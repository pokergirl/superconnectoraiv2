import json
import math
import asyncio
import os
import logging
from typing import List, Dict, Any, Optional, Tuple
import openai
import httpx
from pinecone import Pinecone
from app.core.config import settings
from app.services.embeddings_service import embeddings_service
from app.core.db import get_database

logger = logging.getLogger(__name__)

class RetrievalService:
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
            print("OpenAI client initialized successfully")
        except Exception as e:
            print(f"Error initializing OpenAI client: {e}")
            raise ValueError(f"Failed to initialize OpenAI client: {e}")
            
        # Initialize Pinecone client
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
            
        # Configuration constants
        self.TOTAL_TOKEN_LIMIT = 128000
        self.ESTIMATED_PROMPT_TOKENS = 500  # Conservative estimate for system prompt + user query
        self.ESTIMATED_AVG_PROFILE_TOKENS = 200  # Conservative estimate per profile
        
    async def rewrite_query_with_llm(self, verbose_query: str, enable_rewrite: bool = True) -> str:
        """
        Optional LLM query rewrite using gpt-4o-mini to transform verbose query into concise search intent.
        
        Args:
            verbose_query: The original user query
            enable_rewrite: Whether to enable query rewriting (toggle)
            
        Returns:
            Rewritten query or original query if rewrite is disabled
        """
        if not enable_rewrite or not self.openai_client:
            return verbose_query
            
        try:
            system_prompt = """You are a query optimization assistant. Transform verbose user queries into concise, focused search intent sentences that capture the core requirements for finding relevant professional profiles.

Focus on:
- Key skills, roles, or expertise areas
- Industry or company preferences
- Location requirements
- Experience level or seniority
- Specific qualifications or backgrounds

Keep the output to 1-2 sentences maximum."""

            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Rewrite this query into a concise search intent: {verbose_query}"}
                ],
                max_tokens=100,
                temperature=0.3
            )
            
            rewritten_query = response.choices[0].message.content.strip()
            print(f"Query rewritten from: '{verbose_query}' to: '{rewritten_query}'")
            return rewritten_query
            
        except Exception as e:
            print(f"Error rewriting query: {e}")
            return verbose_query
    
    async def hybrid_pinecone_query(
        self, 
        vector: List[float], 
        top_k: int = 600, 
        alpha: float = 0.6, 
        filter_dict: Optional[Dict[str, Any]] = None,
        namespace: str = "default_user"
    ) -> List[str]:
        """
        Perform hybrid search query on Pinecone index.
        
        Args:
            vector: Dense embedding of the search query
            top_k: Number of results to retrieve (default: 600)
            alpha: Balance between dense and sparse results (default: 0.6)
            filter_dict: Metadata filtering dictionary
            namespace: Namespace for tenant isolation
            
        Returns:
            List of profile IDs from the query response
        """
        if not self.index:
            raise ValueError("Pinecone client not initialized. Please check PINECONE_API_KEY configuration.")
            
        try:
            # Prepare query parameters
            query_params = {
                "vector": vector,
                "top_k": top_k,
                "namespace": namespace,
                "include_metadata": True
            }
            
            # Add filter if provided
            if filter_dict:
                query_params["filter"] = filter_dict
                
            # Note: Pinecone serverless automatically handles hybrid search
            # The alpha parameter is handled internally by Pinecone for serverless indexes
            print(f"Performing hybrid query with top_k={top_k}, alpha={alpha}, namespace={namespace}")
            
            # Execute the query
            query_response = self.index.query(**query_params)
            
            # Extract profile IDs from matches
            profile_ids = []
            for match in query_response.matches:
                profile_ids.append(match.id)
                
            print(f"Retrieved {len(profile_ids)} profile IDs from Pinecone")
            return profile_ids
            
        except Exception as e:
            print(f"Error performing hybrid Pinecone query: {e}")
            raise
    
    def calculate_chunk_size(self) -> int:
        """
        Calculate the chunk size for profiles to send to the re-ranking model.
        Formula: chunk_size = floor((128_000 - prompt_tokens) / avg_profile_tokens)
        
        Returns:
            Calculated chunk size
        """
        available_tokens = self.TOTAL_TOKEN_LIMIT - self.ESTIMATED_PROMPT_TOKENS
        chunk_size = math.floor(available_tokens / self.ESTIMATED_AVG_PROFILE_TOKENS)
        
        # Ensure minimum chunk size of 1 and reasonable maximum
        chunk_size = max(1, min(chunk_size, 100))
        
        print(f"Calculated chunk size: {chunk_size} profiles per batch")
        return chunk_size
    
    def clean_json_response(self, response_content: str) -> str:
        """
        Clean the response content by removing markdown code block fences if present.
        
        Args:
            response_content: Raw response content from OpenAI
            
        Returns:
            Cleaned response content ready for JSON parsing
        """
        content = response_content.strip()
        
        # Check if content is wrapped in markdown code blocks
        if content.startswith('```json') and content.endswith('```'):
            # Remove the opening ```json and closing ```
            content = content[7:-3].strip()
        elif content.startswith('```') and content.endswith('```'):
            # Handle generic code blocks
            content = content[3:-3].strip()
            
        return content
    
    async def rerank_with_openai(
        self,
        candidates: List[Dict[str, Any]],
        user_query: str
    ) -> List[Dict[str, Any]]:
        """
        Re-rank candidates using gpt-4o with context budgeting.
        
        Args:
            candidates: List of candidate profiles to re-rank
            user_query: Original user query for context
            
        Returns:
            List of re-ranked profiles with scores, pros, and cons
        """
        if not self.openai_client:
            raise ValueError("OpenAI client not initialized. Please check OPENAI_API_KEY configuration.")
            
        if not candidates:
            return []
            
        chunk_size = self.calculate_chunk_size()
        all_results = []
        
        # Process candidates in chunks
        for i in range(0, len(candidates), chunk_size):
            chunk = candidates[i:i + chunk_size]
            print(f"Processing chunk {i//chunk_size + 1} with {len(chunk)} profiles")
            
            try:
                # Prepare the system prompt
                system_prompt = "You are a recruiting assistant. For each profile JSON, score 1-10 how well it matches the user query, then list a one-sentence pro and con."
                
                # Prepare the user message with profiles
                profiles_json = json.dumps(chunk, indent=2)
                user_message = """User Query: "{}"

Profiles to evaluate:
{}

Please respond with a JSON array where each object has:
- "profile_id": the profile identifier (use the "id" field from each profile)
- "score": integer from 1-10
- "pro": one sentence explaining the main strength/match
- "con": one sentence explaining the main limitation/concern

IMPORTANT: For "profile_id", use the exact value from the "id" field of each profile in the JSON above.

Example format:
[
  {{
    "profile_id": "profile_123",
    "score": 8,
    "pro": "Strong background in required technology with relevant industry experience.",
    "con": "Location might not be ideal for the role requirements."
  }}
]""".format(user_query, profiles_json)

                # Call gpt-4o
                response = self.openai_client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_message}
                    ],
                    max_tokens=4000,
                    temperature=0.3
                )
                
                # Parse the response
                ai_response = response.choices[0].message.content.strip()
                logger.debug(f"Raw OpenAI response for re-ranking: {ai_response}")
                
                try:
                    # Clean the response before parsing JSON
                    cleaned_response = self.clean_json_response(ai_response)
                    # Try to parse as JSON
                    chunk_results = json.loads(cleaned_response)
                    
                    # Validate and process results
                    for result in chunk_results:
                        if isinstance(result, dict) and all(key in result for key in ["profile_id", "score", "pro", "con"]):
                            # Find the original profile data with improved matching logic
                            result_profile_id = str(result["profile_id"])
                            profile_data = None
                            
                            # Try multiple matching strategies
                            for p in chunk:
                                # Strategy 1: Match against 'id' field
                                if str(p.get("id", "")) == result_profile_id:
                                    profile_data = p
                                    break
                                # Strategy 2: Match against 'profile_id' field
                                elif str(p.get("profile_id", "")) == result_profile_id:
                                    profile_data = p
                                    break
                                # Strategy 3: Match against '_id' field (if still present)
                                elif str(p.get("_id", "")) == result_profile_id:
                                    profile_data = p
                                    break
                                # Strategy 4: Match against linkedin_url (original Pinecone ID)
                                elif str(p.get("linkedin_url", "")) == result_profile_id:
                                    profile_data = p
                                    break
                            
                            if profile_data:
                                all_results.append({
                                    "profile": profile_data,
                                    "score": max(1, min(10, int(result["score"]))),  # Ensure score is 1-10
                                    "pro": result["pro"],
                                    "con": result["con"]
                                })
                                print(f"Successfully matched profile_id: {result_profile_id}")
                            else:
                                print(f"Warning: Could not find profile data for profile_id: {result_profile_id}")
                                print(f"Available profile IDs in chunk: {[str(p.get('id', p.get('profile_id', p.get('_id', 'unknown')))) for p in chunk]}")
                                
                except json.JSONDecodeError:
                    print(f"Failed to parse JSON response for chunk {i//chunk_size + 1}: {ai_response}")
                    raise
                        
            except Exception as e:
                print(f"Error processing chunk {i//chunk_size + 1}: {e}")
                raise
        
        # Sort by score descending
        all_results.sort(key=lambda x: x["score"], reverse=True)
        
        print(f"Re-ranked {len(all_results)} profiles using OpenAI")
        return all_results
    
    async def fetch_profile_data(self, profile_ids: List[str], user_id: str) -> List[Dict[str, Any]]:
        """
        Fetch full profile data for the given profile IDs from the database.
        
        Args:
            profile_ids: List of profile IDs to fetch
            user_id: User ID for database queries
            
        Returns:
            List of full profile data dictionaries
        """
        try:
            db = get_database()
            connections_collection = db.connections
            
            # Query for profiles by their LinkedIn URLs or profile IDs
            profiles = []
            async for profile in connections_collection.find({
                "$or": [
                    {"linkedin_url": {"$in": profile_ids}},
                    {"_id": {"$in": profile_ids}}
                ],
                "user_id": user_id
            }):
                # Convert MongoDB document to clean dict
                clean_profile = {}
                for key, value in profile.items():
                    if key == "_id":
                        clean_profile["id"] = str(value)
                        clean_profile["profile_id"] = str(value)
                    else:
                        clean_profile[key] = value
                        
                profiles.append(clean_profile)
            
            print(f"Fetched {len(profiles)} full profiles from database")
            return profiles
            
        except Exception as e:
            print(f"Error fetching profile data: {e}")
            return []
    
    async def retrieve_and_rerank(
        self, 
        user_query: str, 
        user_id: str = "default_user",
        enable_query_rewrite: bool = True,
        filter_dict: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Main service orchestration method that ties all steps together.
        
        Args:
            user_query: Original user query
            user_id: User ID for namespace isolation and data fetching
            enable_query_rewrite: Whether to enable optional query rewriting
            filter_dict: Optional metadata filtering
            
        Returns:
            List of re-ranked and annotated results
        """
        try:
            print(f"Starting retrieval and re-ranking for query: '{user_query}'")
            
            # Step 1: Optional query rewrite
            processed_query = await self.rewrite_query_with_llm(user_query, enable_query_rewrite)
            
            # Step 2: Generate embedding for the query
            query_embedding = await embeddings_service.generate_embedding(processed_query)
            
            # Step 3: Execute hybrid query against Pinecone
            profile_ids = await self.hybrid_pinecone_query(
                vector=query_embedding,
                top_k=30,
                alpha=0.6,
                filter_dict=filter_dict,
                namespace=user_id
            )
            
            if not profile_ids:
                print("No profiles found in Pinecone query")
                return []
            
            # Step 4: Fetch full profile data for candidates
            candidate_profiles = await self.fetch_profile_data(profile_ids, user_id)
            
            if not candidate_profiles:
                print("No full profile data found for candidates")
                return []
            
            # Step 5: Chunk and re-rank candidates using OpenAI
            reranked_results = await self.rerank_with_openai(candidate_profiles, user_query)
            
            # Step 6: Limit results to top 20
            final_results = reranked_results[:20]
            
            print(f"Retrieval and re-ranking completed. Returning {len(final_results)} results (limited from {len(reranked_results)})")
            return final_results
            
        except Exception as e:
            print(f"Error in retrieve_and_rerank: {e}")
            raise

# Global instance
retrieval_service = RetrievalService()