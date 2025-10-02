import re
import csv
import asyncio
import os
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime
import pandas as pd
from bs4 import BeautifulSoup
import emoji
import google.generativeai as genai
import httpx
from pinecone import Pinecone
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.core.config import settings
from app.core.db import get_database

class GeminiEmbeddingsService:
    def __init__(self):
        # Initialize Gemini client
        if not settings.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY not found in environment variables")
        
        try:
            genai.configure(api_key=settings.GEMINI_API_KEY)
            print("Gemini client initialized successfully in embeddings service")
        except Exception as e:
            print(f"Error initializing Gemini client in embeddings service: {e}")
            raise ValueError(f"Failed to initialize Gemini client: {e}")
            
        # Initialize Pinecone client only if API key is provided
        if settings.PINECONE_API_KEY:
            try:
                self.pinecone_client = Pinecone(api_key=settings.PINECONE_API_KEY)
                self.index = self.pinecone_client.Index(settings.PINECONE_INDEX_NAME)
            except Exception as e:
                print(f"Warning: Could not initialize Pinecone client: {e}")
                self.pinecone_client = None
                self.index = None
        else:
            self.pinecone_client = None
            self.index = None
            
        # Use Gemini's text embedding model - use the larger dimension model for compatibility
        self.embedding_model = settings.GEMINI_EMBEDDING_MODEL
        # Note: text-embedding-004 produces 768-dimensional vectors
        # For compatibility with existing 1536-dimensional Pinecone index, we'll need to pad or recreate the index
        self.batch_size = 500
        
    def canonicalize_profile_text(self, row: pd.Series) -> str:
        """
        Canonicalize profile text by merging all relevant fields from a row into a clean string.
        
        Args:
            row: A pandas Series representing a row from the connections DataFrame.
            
        Returns:
            A single canonicalized text string for vectorization.
        """
        # Extract all relevant textual information from the row
        full_name = str(row.get("fullName", "")).strip()
        headline = str(row.get("headline", "")).strip()
        about = str(row.get("about", "")).strip()
        experiences = str(row.get("experiences", "")).strip()
        education = str(row.get("education", "")).strip()
        skills = str(row.get("skills", "")).strip()
        company_name = str(row.get("companyName", "")).strip()
        location = f"{str(row.get('city', '')).strip()} {str(row.get('country', '')).strip()}".strip()

        # Combine all fields into a comprehensive string
        combined_text = " ".join(filter(None, [
            full_name,
            headline,
            about,
            "Past Experience: " + experiences if experiences else "",
            "Education: " + education if education else "",
            "Skills: " + skills if skills else "",
            "Current Company: " + company_name if company_name else "",
            "Location: " + location if location else ""
        ]))
        
        # Remove HTML tags
        soup = BeautifulSoup(combined_text, 'html.parser')
        text = soup.get_text()
        
        # Remove emojis
        text = emoji.replace_emoji(text, replace='')
        
        # Expand "Sr." to "Senior"
        text = re.sub(r'\bSr\.?\s*', 'Senior ', text, flags=re.IGNORECASE)
        
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Convert to lowercase and strip
        text = text.lower().strip()
        
        return text
    
    async def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for the given text using Gemini's text-embedding-004 model.
        Pads the 768-dimensional vector to 1536 dimensions for Pinecone compatibility.
        
        Args:
            text: Text to generate embedding for
            
        Returns:
            List of floats representing the embedding vector (1536 dimensions)
        """
        try:
            result = genai.embed_content(
                model=self.embedding_model,
                content=text,
                task_type="retrieval_document",
                output_dimensionality=1536
            )
            embedding = result['embedding']
            return embedding
        except Exception as e:
            print(f"Error generating embedding with Gemini: {e}")
            raise
    
    async def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for a batch of texts using Gemini's text-embedding-004 model.
        Pads each 768-dimensional vector to 1536 dimensions for Pinecone compatibility.
        Note: Gemini doesn't support batch embedding in the same way as OpenAI,
        so we'll process them individually but efficiently.
        
        Args:
            texts: List of texts to generate embeddings for
            
        Returns:
            List of embedding vectors corresponding to each input text (1536 dimensions each)
        """
        if not texts:
            return []
            
        try:
            embeddings = []
            for text in texts:
                result = genai.embed_content(
                    model=self.embedding_model,
                    content=text,
                    task_type="retrieval_document",
                    output_dimensionality=1536
                )
                embedding = result['embedding']
                embeddings.append(embedding)
                
                # Small delay to avoid rate limiting
                await asyncio.sleep(0.1)
                
            return embeddings
        except Exception as e:
            print(f"Error generating batch embeddings with Gemini: {e}")
            raise
    
    async def get_cached_embedding(self, profile_id: str) -> Optional[List[float]]:
        """
        Retrieve cached embedding for a profile.
        
        Args:
            profile_id: Profile ID to look up
            
        Returns:
            Cached embedding vector or None if not found
        """
        # Caching disabled to prevent disk space issues on deployment environment.
        return None
    
    async def cache_embedding(self, profile_id: str, embedding: List[float]) -> None:
        """
        Cache embedding for a profile.
        
        Args:
            profile_id: Profile ID
            embedding: Embedding vector to cache
        """
        # Caching disabled to prevent disk space issues on deployment environment.
        return
    
    async def get_or_generate_embedding(self, profile_id: str, text: str) -> List[float]:
        """
        Get cached embedding or generate new one if not cached.
        This method is kept for backward compatibility and single-item processing.
        For batch processing, use generate_embeddings_batch directly.
        
        Args:
            profile_id: Profile ID
            text: Text to generate embedding for
            
        Returns:
            Embedding vector
        """
        # Try to get cached embedding first
        cached_embedding = await self.get_cached_embedding(profile_id)
        if cached_embedding:
            return cached_embedding
        
        # Generate new embedding
        embedding = await self.generate_embedding(text)
        
        # Cache the embedding
        await self.cache_embedding(profile_id, embedding)
        
        return embedding
    
    def batch_upsert_to_pinecone(self, vectors: List[Tuple[str, List[float], Dict[str, Any]]], namespace: str) -> None:
        """
        Perform batch upsert to Pinecone index.
        
        Args:
            vectors: List of tuples (id, vector, metadata)
            namespace: Namespace for tenant isolation (user_id)
        """
        if not self.index:
            raise ValueError("Pinecone client not initialized. Please check PINECONE_API_KEY and PINECONE_INDEX_NAME configuration.")
            
        try:
            # Process vectors in batches
            for i in range(0, len(vectors), self.batch_size):
                batch = vectors[i:i + self.batch_size]
                
                # Format vectors for Pinecone
                formatted_vectors = []
                for vector_id, vector, metadata in batch:
                    formatted_vectors.append({
                        "id": vector_id,
                        "values": vector,
                        "metadata": metadata
                    })
                
                # Upsert batch to Pinecone
                self.index.upsert(
                    vectors=formatted_vectors,
                    namespace=namespace
                )
                
                print(f"Upserted batch {i//self.batch_size + 1} with {len(batch)} vectors to namespace {namespace}")
                
        except Exception as e:
            print(f"Error upserting to Pinecone: {e}")
            raise
    
    def load_connections_data(self, csv_path: str = "updated_connections.csv") -> pd.DataFrame:
        """
        Load connections data from CSV file.
        
        Note: For large files, consider using the chunked processing in process_profiles_and_upsert
        instead of loading the entire file into memory.
        
        Args:
            csv_path: Path to the CSV file
            
        Returns:
            DataFrame with connections data
        """
        try:
            df = pd.read_csv(csv_path)
            return df
        except Exception as e:
            print(f"Error loading connections data: {e}")
            raise
    
    def extract_metadata(self, row: pd.Series) -> Dict[str, Any]:
        """
        Extract metadata from a CSV row, ensuring all profile fields are included
        and data types are compatible with Pinecone (string, number, boolean).
        
        Args:
            row: Pandas Series representing a row from the CSV
            
        Returns:
            Metadata dictionary with flattened profile data.
        """
        metadata = {}

        # Helper to safely get a value from the row
        def safe_get(key, default=None):
            val = row.get(key)
            # Check for pandas missing values (NaT, nan, None)
            if pd.isna(val):
                return default
            return val

        # Helper to convert to string, returning None for empty strings
        def to_str(value):
            if value is None:
                return None
            s = str(value).strip()
            return s if s else None

        # Helper to convert to integer
        def to_int(value):
            if value is None:
                return None
            try:
                # Handle cases like '500+' by removing non-digits
                if isinstance(value, str):
                    cleaned_value = re.sub(r'[^\d]', '', value)
                    return int(cleaned_value) if cleaned_value else None
                return int(float(value))
            except (ValueError, TypeError):
                return None

        # Helper to convert to boolean
        def to_bool(value):
            if value is None:
                return False # Default to False for boolean flags
            if isinstance(value, bool):
                return value
            return str(value).lower() in ['true', '1', 't', 'y', 'yes']

        # Define all possible profile fields and their conversion functions
        # This combines fields from the Connection model and observed CSV columns
        field_map = {
            # Personal Info
            'fullName': to_str,
            'firstName': to_str,
            'lastName': to_str,
            'headline': to_str,
            'about': to_str,
            'description': to_str,
            'city': to_str,
            'state': to_str,
            'country': to_str,
            'location': to_str,
            'profilePicture': to_str,
            'publicIdentifier': to_str,
            'linkedin_url': to_str,
            'email_address': to_str,
            
            # Connection & Stats
            'connected_on': to_str,
            'followerCount': to_int,
            'followers': to_int,
            'connectionsCount': to_int,
            
            # Flags
            'isCreator': to_bool,
            'isPremium': to_bool,
            'isTopVoice': to_bool,
            'isOpenToWork': to_bool,
            'isHiring': to_bool,
            'isInfluencer': to_bool,
            
            # Professional Details
            'title': to_str,
            'experiences': to_str,
            'education': to_str,
            'skills': to_str,
            'schoolName': to_str,
            'pronoun': to_str,
            'associated_hashtags': to_str,
            
            # Company Details
            'companyName': to_str,
            'company': to_str,
            'company_size': to_str,
            'company_website': to_str,
            'company_phone': to_str,
            'company_industry': to_str,
            'company_industry_topics': to_str,
            'company_description': to_str,
            'company_address': to_str,
            'company_city': to_str,
            'company_state': to_str,
            'company_country': to_str,
            'company_revenue': to_str,
            'company_latest_funding': to_str,
            'company_linkedin': to_str,
            'urn': to_str,
        }

        for field, converter in field_map.items():
            value = safe_get(field)
            if value is not None:
                converted_value = converter(value)
                # Add to metadata only if it's not None and not an empty string
                if converted_value is not None and converted_value != '':
                    # Use a consistent key, e.g., 'companyName' over 'company'
                    key = 'companyName' if field == 'company' else field
                    key = 'followerCount' if field == 'followers' else key
                    if key not in metadata: # Prioritize first-seen key
                        metadata[key] = converted_value

        # Post-processing to ensure consistency
        if 'fullName' not in metadata and ('firstName' in metadata or 'lastName' in metadata):
            first = metadata.get('firstName', '') or ''
            last = metadata.get('lastName', '') or ''
            full_name = f"{first} {last}".strip()
            if full_name:
                metadata['fullName'] = full_name

        return metadata
    
    async def process_profiles_and_upsert(self, csv_path: str = "updated_connections.csv", user_id: str = "default_user", chunk_size: int = 100) -> Dict[str, Any]:
        """
        Process all profiles from CSV in chunks, generate embeddings in batches, and upsert to Pinecone.
        
        Args:
            csv_path: Path to the CSV file
            user_id: User ID for namespace isolation
            chunk_size: Number of rows to process in each chunk
            
        Returns:
            Processing results summary
        """
        try:
            # Initialize counters
            total_processed_count = 0
            total_error_count = 0
            total_vectors_upserted = 0
            chunk_number = 0
            total_rows = 0
            
            print(f"Starting chunked processing of {csv_path} with chunk size {chunk_size}")
            
            # Process CSV in chunks
            for chunk_df in pd.read_csv(csv_path, chunksize=chunk_size):
                chunk_number += 1
                chunk_vectors = []
                chunk_processed_count = 0
                chunk_error_count = 0
                
                print(f"Processing batch of {len(chunk_df)} profiles for chunk {chunk_number}...")
                
                try:
                    # Prepare batch data
                    batch_data = []
                    valid_rows = []
                    
                    # First pass: extract and validate profile data
                    for index, row in chunk_df.iterrows():
                        try:
                            # Use 'urn' as the primary unique identifier, fallback to publicIdentifier, then linkedin_url
                            profile_id = str(row.get('urn', '')).strip()
                            if not profile_id:
                                profile_id = str(row.get('publicIdentifier', '')).strip()
                            if not profile_id:
                                profile_id = str(row.get('linkedin_url', '')).strip()
                            
                            # Fallback to a row-based ID if still no identifier
                            if not profile_id:
                                profile_id = f"profile_{total_rows + index}"

                            # Skip if essential data is missing
                            if not str(row.get('fullName', '')).strip():
                                continue
                            
                            # Canonicalize the entire row's text for vectorization
                            canonical_text = self.canonicalize_profile_text(row)
                            
                            # Skip if canonical text is too short
                            if len(canonical_text.strip()) < 20: # Increased threshold for meaningful content
                                continue
                            
                            # Check for cached embedding first
                            cached_embedding = await self.get_cached_embedding(profile_id)
                            if cached_embedding:
                                # Use cached embedding
                                metadata = self.extract_metadata(row)
                                metadata["canonical_text"] = canonical_text # Add canonical text to metadata
                                chunk_vectors.append((profile_id, cached_embedding, metadata))
                                chunk_processed_count += 1
                            else:
                                # Add to batch for embedding generation
                                batch_data.append({
                                    'profile_id': profile_id,
                                    'canonical_text': canonical_text,
                                    'row': row,
                                })
                                valid_rows.append(row)
                            
                        except Exception as e:
                            chunk_error_count += 1
                            print(f"Error preparing row {total_rows + index} in chunk {chunk_number}: {e}")
                            continue
                    
                    # Generate embeddings for the batch (if any)
                    if batch_data:
                        try:
                            # Extract texts for batch embedding generation
                            texts_to_embed = [item['canonical_text'] for item in batch_data]
                            
                            # Generate embeddings using Gemini
                            embeddings = await self.generate_embeddings_batch(texts_to_embed)
                            
                            # Process the results and cache embeddings
                            for i, embedding in enumerate(embeddings):
                                item = batch_data[i]
                                profile_id = item['profile_id']
                                
                                # Cache the new embedding
                                await self.cache_embedding(profile_id, embedding)
                                
                                # Extract metadata from the new columns
                                metadata = self.extract_metadata(item['row'])
                                metadata["canonical_text"] = item['canonical_text'] # Add canonical text to metadata
                                
                                # Add to chunk vectors list for upserting
                                chunk_vectors.append((profile_id, embedding, metadata))
                                chunk_processed_count += 1
                                
                        except Exception as e:
                            chunk_error_count += len(batch_data)
                            print(f"Error generating batch embeddings for chunk {chunk_number}: {e}")
                    
                    # Batch upsert chunk to Pinecone
                    if chunk_vectors:
                        print(f"Upserting {len(chunk_vectors)} vectors from chunk {chunk_number} to Pinecone...")
                        self.batch_upsert_to_pinecone(chunk_vectors, namespace=user_id)
                        total_vectors_upserted += len(chunk_vectors)
                        print(f"Successfully upserted chunk {chunk_number} with {len(chunk_vectors)} vectors")
                    
                    # Update totals
                    total_processed_count += chunk_processed_count
                    total_error_count += chunk_error_count
                    total_rows += len(chunk_df)
                    
                    print(f"Completed chunk {chunk_number}: {chunk_processed_count} processed, {chunk_error_count} errors")
                    
                except Exception as e:
                    print(f"Error processing batch for chunk {chunk_number}: {e}")
                    # Continue with next chunk instead of failing entirely
                    total_error_count += len(chunk_df)
                    total_rows += len(chunk_df)
                    continue
            
            print(f"Completed processing all chunks. Total: {total_processed_count} processed, {total_error_count} errors, {total_vectors_upserted} vectors upserted")
            
            return {
                "total_rows": total_rows,
                "processed_count": total_processed_count,
                "error_count": total_error_count,
                "vectors_upserted": total_vectors_upserted,
                "chunks_processed": chunk_number,
                "namespace": user_id
            }
            
        except Exception as e:
            print(f"Error in process_profiles_and_upsert: {e}")
            raise

# Global instance
gemini_embeddings_service = GeminiEmbeddingsService()