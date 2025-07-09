import re
import csv
import asyncio
import os
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime
import pandas as pd
from bs4 import BeautifulSoup
import emoji
import openai
import httpx
from pinecone import Pinecone
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.core.config import settings
from app.core.db import get_database

class EmbeddingsService:
    def __init__(self):
        # Initialize OpenAI client
        if not settings.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY not found in environment variables")
        
        try:
            # Create a custom HTTP client without proxy configuration
            http_client = httpx.Client(
                timeout=60.0,
                limits=httpx.Limits(max_connections=100, max_keepalive_connections=20)
            )
            
            # Initialize OpenAI client with custom HTTP client
            self.openai_client = openai.OpenAI(
                api_key=settings.OPENAI_API_KEY,
                http_client=http_client
            )
            print("OpenAI client initialized successfully in embeddings service")
        except Exception as e:
            print(f"Error initializing OpenAI client in embeddings service: {e}")
            raise ValueError(f"Failed to initialize OpenAI client: {e}")
            
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
            
        self.embedding_model = "text-embedding-3-small"
        self.batch_size = 500
        
    def canonicalize_profile_text(self, name: str, headline: str, experience: str, skills: str, location: str) -> str:
        """
        Canonicalize profile text by merging fields into a clean string.
        
        Args:
            name: User's name
            headline: User's headline/title
            experience: User's experience description
            skills: User's skills
            location: User's location
            
        Returns:
            Canonicalized text string
        """
        # Combine all fields
        combined_text = f"{name} {headline} {experience} {skills} {location}"
        
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
        Generate embedding for the given text using OpenAI's text-embedding-3-small model.
        
        Args:
            text: Text to generate embedding for
            
        Returns:
            List of floats representing the embedding vector
        """
        if not self.openai_client:
            raise ValueError("OpenAI client not initialized. Please check OPENAI_API_KEY configuration.")
            
        try:
            response = self.openai_client.embeddings.create(
                model=self.embedding_model,
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"Error generating embedding: {e}")
            raise
    
    async def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for a batch of texts using OpenAI's text-embedding-3-small model.
        This makes a single API call for all texts, which is much more efficient than individual calls.
        
        Args:
            texts: List of texts to generate embeddings for
            
        Returns:
            List of embedding vectors corresponding to each input text
        """
        if not self.openai_client:
            raise ValueError("OpenAI client not initialized. Please check OPENAI_API_KEY configuration.")
            
        if not texts:
            return []
            
        try:
            response = self.openai_client.embeddings.create(
                model=self.embedding_model,
                input=texts
            )
            return [data.embedding for data in response.data]
        except Exception as e:
            print(f"Error generating batch embeddings: {e}")
            raise
    
    async def get_cached_embedding(self, profile_id: str) -> Optional[List[float]]:
        """
        Retrieve cached embedding for a profile.
        
        Args:
            profile_id: Profile ID to look up
            
        Returns:
            Cached embedding vector or None if not found
        """
        try:
            db = get_database()
            cache_collection = db.embedding_cache
            
            cached_result = await cache_collection.find_one({"profile_id": profile_id})
            if cached_result:
                return cached_result.get("embedding")
            return None
        except Exception as e:
            print(f"Error retrieving cached embedding: {e}")
            return None
    
    async def cache_embedding(self, profile_id: str, embedding: List[float]) -> None:
        """
        Cache embedding for a profile.
        
        Args:
            profile_id: Profile ID
            embedding: Embedding vector to cache
        """
        try:
            db = get_database()
            cache_collection = db.embedding_cache
            
            await cache_collection.update_one(
                {"profile_id": profile_id},
                {
                    "$set": {
                        "profile_id": profile_id,
                        "embedding": embedding,
                        "created_at": datetime.utcnow(),
                        "model": self.embedding_model
                    }
                },
                upsert=True
            )
        except Exception as e:
            print(f"Error caching embedding: {e}")
            raise
    
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
    
    def load_connections_data(self, csv_path: str = "Connections.csv") -> pd.DataFrame:
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
        Extract metadata from a CSV row according to the specified schema.
        
        Args:
            row: Pandas Series representing a row from the CSV
            
        Returns:
            Metadata dictionary
        """
        return {
            "industry": str(row.get("CompanyIndustry", "")).strip() or None,
            "size": str(row.get("Company size", "")).strip() or None,
            "city": str(row.get("City", "")).strip() or None,
            "followers": str(row.get("Followers", "")).strip() or None,
            "connected_on": str(row.get("Connected On", "")).strip() or None
        }
    
    async def process_profiles_and_upsert(self, csv_path: str = "Connections.csv", user_id: str = "default_user", chunk_size: int = 100) -> Dict[str, Any]:
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
                            # Extract profile information
                            name = f"{row.get('FirstName', '')} {row.get('LastName', '')}".strip()
                            headline = str(row.get('Title', '')).strip()
                            experience = str(row.get('Description/0', '')).strip()
                            skills = ""  # Not available in current CSV structure
                            location = f"{row.get('City', '')} {row.get('State', '')} {row.get('Country', '')}".strip()
                            
                            # Skip if essential data is missing
                            if not name or name == " ":
                                continue
                            
                            # Generate profile ID (using LinkedIn URL or row index)
                            linkedin_url = str(row.get('LinkedinUrl', '')).strip()
                            profile_id = linkedin_url if linkedin_url else f"profile_{index}"
                            
                            # Canonicalize profile text
                            canonical_text = self.canonicalize_profile_text(
                                name=name,
                                headline=headline,
                                experience=experience,
                                skills=skills,
                                location=location
                            )
                            
                            # Skip if canonical text is too short
                            if len(canonical_text.strip()) < 10:
                                continue
                            
                            # Check for cached embedding first
                            cached_embedding = await self.get_cached_embedding(profile_id)
                            if cached_embedding:
                                # Use cached embedding
                                metadata = self.extract_metadata(row)
                                metadata["name"] = name
                                metadata["canonical_text"] = canonical_text
                                chunk_vectors.append((profile_id, cached_embedding, metadata))
                                chunk_processed_count += 1
                            else:
                                # Add to batch for embedding generation
                                batch_data.append({
                                    'profile_id': profile_id,
                                    'canonical_text': canonical_text,
                                    'name': name,
                                    'row': row,
                                    'index': index
                                })
                                valid_rows.append(row)
                            
                        except Exception as e:
                            chunk_error_count += 1
                            print(f"Error preparing row {index} in chunk {chunk_number}: {e}")
                            continue
                    
                    # Generate embeddings for the batch (if any)
                    if batch_data:
                        try:
                            # Extract texts for batch embedding generation
                            texts_to_embed = [item['canonical_text'] for item in batch_data]
                            
                            # Generate embeddings in a single API call
                            embeddings = await self.generate_embeddings_batch(texts_to_embed)
                            
                            # Process the results and cache embeddings
                            for i, embedding in enumerate(embeddings):
                                item = batch_data[i]
                                profile_id = item['profile_id']
                                
                                # Cache the embedding
                                await self.cache_embedding(profile_id, embedding)
                                
                                # Extract metadata
                                metadata = self.extract_metadata(item['row'])
                                metadata["name"] = item['name']
                                metadata["canonical_text"] = item['canonical_text']
                                
                                # Add to chunk vectors list
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
embeddings_service = EmbeddingsService()