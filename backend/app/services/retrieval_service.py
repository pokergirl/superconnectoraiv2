import json
import math
import asyncio
import os
import logging
from typing import List, Dict, Any, Optional, Tuple
import google.api_core.exceptions
import google.generativeai as genai
import httpx
from pinecone import Pinecone
from app.core.config import settings
from app.services.gemini_embeddings_service import gemini_embeddings_service
from app.services.threading_service import threading_service

logger = logging.getLogger(__name__)

class RetrievalService:
    def _to_snake_case(self, name: str) -> str:
        """Converts a camelCase string to snake_case."""
        import re
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()

    def _convert_keys_to_snake_case(self, data: Any) -> Any:
        """Recursively converts dictionary keys from camelCase to snake_case."""
        if isinstance(data, dict):
            return {self._to_snake_case(k): self._convert_keys_to_snake_case(v) for k, v in data.items()}
        if isinstance(data, list):
            return [self._convert_keys_to_snake_case(i) for i in data]
        return data

    def __init__(self):
        # Initialize Gemini client
        if not settings.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY not found in environment variables")
        
        try:
            genai.configure(api_key=settings.GEMINI_API_KEY)
            self.gemini_client = genai.GenerativeModel(model_name=settings.GEMINI_MODEL)
            print("Gemini client initialized successfully")
        except Exception as e:
            print(f"Error initializing Gemini client: {e}")
            raise ValueError(f"Failed to initialize Gemini client: {e}")
            
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
        Optional LLM query rewrite using Gemini to transform verbose query into concise search intent.
        
        Args:
            verbose_query: The original user query
            enable_rewrite: Whether to enable query rewriting (toggle)
            
        Returns:
            Rewritten query or original query if rewrite is disabled
        """
        if not enable_rewrite or not self.gemini_client:
            return verbose_query
            
        try:
            prompt = f"""You are a query optimization assistant. Transform verbose user queries into concise, focused search intent sentences that capture the core requirements for finding relevant professional profiles.

Focus on:
- Key skills, roles, or expertise areas
- Industry or company preferences
- Location requirements
- Experience level or seniority
- Specific qualifications or backgrounds

Keep the output to 1-2 sentences maximum.

Rewrite this query into a concise search intent: {verbose_query}"""

            response = self.gemini_client.generate_content(prompt)
            
            rewritten_query = response.text.strip()
            
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
    ) -> List[Dict[str, Any]]:
        """
        Perform hybrid search query on Pinecone index.
        
        Args:
            vector: Dense embedding of the search query
            top_k: Number of results to retrieve (default: 600)
            alpha: Balance between dense and sparse results (default: 0.6)
            filter_dict: Metadata filtering dictionary
            namespace: Namespace for tenant isolation
            
        Returns:
            List of profiles from the query response, including metadata
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
            
            # Extract profiles with metadata from matches
            profiles = []
            for match in query_response.matches:
                profile_data = self._convert_keys_to_snake_case(match.metadata)
                profile_data["id"] = match.id
                profile_data["profile_id"] = match.id
                # Construct linkedin_url if public_identifier is available and linkedin_url is missing
                if 'public_identifier' in profile_data and not profile_data.get('linkedin_url'):
                    profile_data['linkedin_url'] = f"https://www.linkedin.com/in/{profile_data['public_identifier']}"
                
                profiles.append(profile_data)

            logger.info(f"Retrieved {len(profiles)} profiles from Pinecone.")

            # Log the first profile's metadata for inspection
            if profiles:
                logger.debug(f"Sample profile metadata from Pinecone: {profiles}")

            return profiles
            
        except Exception as e:
            logger.error(f"Error performing hybrid Pinecone query: {e}", exc_info=True)
            # Return empty list to trigger fallback instead of raising
            return []
    
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
    
    def _extract_and_parse_json(self, text: str) -> Optional[List[Dict[str, Any]]]:
        """
        Find and parse the main JSON array from the model's response.
        This is more robust against malformed JSON or extra text.
        """
        try:
            # Find the start of the JSON array
            start_index = text.find('[')
            if start_index == -1:
                logger.error("No JSON array found in the response.")
                return None

            # Find the end of the JSON array
            end_index = text.rfind(']')
            if end_index == -1:
                logger.error("JSON array end not found.")
                return None

            # Extract the JSON string
            json_str = text[start_index:end_index + 1]
            
            # Attempt to parse the extracted string
            return json.loads(json_str)

        except json.JSONDecodeError as e:
            logger.error(f"JSON decoding failed: {e}")
            # Fallback for common errors, like missing commas
            try:
                # Add commas between JSON objects
                json_str = json_str.replace("}\n{", "},\n{")
                return json.loads(json_str)
            except json.JSONDecodeError:
                logger.error("Fallback JSON parsing also failed.")
                return None
        except Exception as e:
            logger.error(f"An unexpected error occurred during JSON extraction: {e}")
            return None

    def calculate_chunk_size(self) -> int:
        """
        Calculates the number of profiles to include in each chunk for re-ranking.
        Reduced chunk size to prevent token limit issues.
        """
        return 5

    def _truncate_profile_for_ai(self, profile: Dict[str, Any], max_chars: int = 800) -> Dict[str, Any]:
        """
        Truncate profile data to prevent token limit issues while preserving key information.
        
        Args:
            profile: Profile dictionary
            max_chars: Maximum characters for text fields
            
        Returns:
            Truncated profile dictionary
        """
        truncated_profile = {}
        
        # Essential fields to always include (short fields)
        essential_fields = ['id', 'profile_id', 'full_name', 'first_name', 'last_name', 'city', 'country', 'company_name', 'title']
        
        # Text fields that need truncation
        text_fields = ['headline', 'about', 'experiences', 'education', 'skills', 'canonical_text']
        
        # Copy essential fields
        for field in essential_fields:
            if field in profile:
                truncated_profile[field] = profile[field]
        
        # Truncate text fields
        for field in text_fields:
            if field in profile and profile[field]:
                text = str(profile[field])
                if len(text) > max_chars:
                    truncated_profile[field] = text[:max_chars] + "..."
                else:
                    truncated_profile[field] = text
        
        # Include boolean flags and numeric fields
        for key, value in profile.items():
            if key not in essential_fields and key not in text_fields:
                if isinstance(value, (bool, int, float)) or (isinstance(value, str) and len(str(value)) < 50):
                    truncated_profile[key] = value
        
        return truncated_profile

    def _rerank_chunk(
        self,
        chunk: List[Dict[str, Any]],
        user_query: str
    ) -> List[Dict[str, Any]]:
        """
        Re-ranks a single chunk of candidates using Gemini Pro with token management.
        """
        try:
            # Truncate profiles to prevent token limit issues
            truncated_chunk = [self._truncate_profile_for_ai(profile) for profile in chunk]
            
            # Prepare the system prompt
            prompt = """You are a sophisticated recruiting assistant responsible for accurately scoring professional profiles against a user's search query. Your task is to provide a relevance score from 0 to 10, where 10 indicates a perfect match and 0 indicates no relevance.

**Scoring Guidelines:**
- **10:** Perfect match. The profile explicitly meets all key criteria in the user's query.
- **9:** Excellent match.
- **8:** Very good match.
- **7:** Good match.
- **5-6:** Average match. Meets some criteria but has notable gaps.
- **1-3:** Poor match. Tangentially related but not a good fit.
- **0:** No match. The profile is completely irrelevant to the query.

For each profile, provide up to 3 reasons "Why this may be a good match" and up to 3 reasons "Why this may not be a good match". Each reason should be a concise sentence directly relevant to the user's search query.

User Query: "{}"

Profiles to evaluate:
{}

Please respond with a JSON array where each object has:
- "profile_id": The profile identifier (use the "id" field from each profile).
- "score": An integer from 0 to 10, representing relevance.
- "pros": An array of up to 3 detailed strengths/advantages (each as a concise sentence).
- "cons": An array of up to 3 detailed weaknesses/concerns (each as a concise sentence).

IMPORTANT: For "profile_id", use the exact value from the "id" field of each profile in the JSON above.

Example format:
[
  {{
    "profile_id": "profile_123",
    "score": 8,
    "pros": [
      "Strong background in required technology with 5+ years experience.",
      "Currently works at a leading company in the target industry."
    ],
    "cons": [
      "Limited experience with specific tools mentioned in requirements."
    ]
  }}
]""".format(user_query, json.dumps(truncated_chunk, indent=2))

            # Call Gemini Pro
            response = self.gemini_client.generate_content(prompt)
            
            # Parse the response
            ai_response = response.text.strip()
            logger.info(f"Raw Gemini response for re-ranking chunk: {ai_response}")
            
            # Use the robust JSON parsing function
            reranked_results = self._extract_and_parse_json(ai_response)
            
            if not reranked_results:
                logger.error("Failed to parse JSON response from Gemini for a chunk")
                return []

            # Validate and process results
            chunk_results = []
            for result in reranked_results:
                if isinstance(result, dict) and all(key in result for key in ["profile_id", "score", "pros", "cons"]):
                    result_profile_id = str(result["profile_id"])
                    profile_data = next((p for p in chunk if str(p.get("id", "")) == result_profile_id or str(p.get("profile_id", "")) == result_profile_id), None)
                    
                    if profile_data:
                        pros = result.get("pros", [])
                        cons = result.get("cons", [])
                        
                        summary = " ".join(pros) + " " + " ".join(cons)
                        chunk_results.append({
                            "profile": profile_data,
                            "score": max(0, min(10, int(float(result["score"])))),
                            "pros": pros,
                            "cons": cons,
                            "summary": summary,
                            "pro": " ".join(pros) if pros else "Strong candidate match.",
                            "con": " ".join(cons) if cons else "Some limitations may apply."
                        })
                        logger.debug(f"Successfully matched profile_id: {result_profile_id}")
                    else:
                        logger.warning(f"Could not find profile data for profile_id: {result_profile_id}")
            return chunk_results
            
        except google.api_core.exceptions.PermissionDenied as e:
            if "billing" in str(e).lower() or "credits" in str(e).lower():
                logger.error("Billing issue detected: You may have run out of credits.", exc_info=True)
                # Optionally, re-raise a custom exception to be handled upstream
                raise ValueError("Billing issue: Please check your account credits.") from e
            else:
                logger.error(f"Permission denied while processing chunk: {e}", exc_info=True)
                return []
        except Exception as e:
            logger.error(f"Error processing chunk: {e}", exc_info=True)
            return []

    async def rerank_with_gemini(
        self,
        candidates: List[Dict[str, Any]],
        user_query: str
    ) -> List[Dict[str, Any]]:
        """
        Re-rank candidates using Gemini Pro with context budgeting and parallel processing.
        """
        if not candidates:
            return []
            
        chunk_size = self.calculate_chunk_size()
        chunks = [candidates[i:i + chunk_size] for i in range(0, len(candidates), chunk_size)]
        
        args_list = [(chunk, user_query) for chunk in chunks]
        
        results_from_threads = threading_service.run_in_parallel(self._rerank_chunk, args_list)
        
        all_results = [item for sublist in results_from_threads if sublist for item in sublist]
        
        all_results.sort(key=lambda x: x["score"], reverse=True)
        
        print(f"Re-ranked {len(all_results)} profiles using Gemini")
        return all_results
    
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
            # Ensure user_id is a string to prevent serialization issues
            namespace = str(user_id)
            logger.info(f"Starting retrieval and re-ranking for query: '{user_query}' in namespace: {namespace}")
            
            # Step 1: Optional query rewrite
            processed_query = await self.rewrite_query_with_llm(user_query, enable_query_rewrite)
            
            # Step 2: Generate embedding for the query
            query_embedding = await gemini_embeddings_service.generate_embedding(processed_query)
            
            # Step 3: Execute hybrid query against Pinecone
            candidate_profiles = await self.hybrid_pinecone_query(
                vector=query_embedding,
                top_k=30,
                alpha=0.6,
                filter_dict=filter_dict,
                namespace=namespace
            )
            
            if not candidate_profiles:
                logger.warning("No profiles found in Pinecone query, falling back to MongoDB search")
                # Fallback to MongoDB text search when Pinecone returns no results
                candidate_profiles = await self.fallback_mongodb_search(user_query, namespace, filter_dict)
                if not candidate_profiles:
                    logger.warning("No profiles found in MongoDB fallback either")
                    return []
            
            logger.info(f"Re-ranking {len(candidate_profiles)} candidates.")
            # Step 4: Chunk and re-rank candidates using OpenAI
            reranked_results = await self.rerank_with_gemini(candidate_profiles, user_query)
            
            # Step 5: Filter results based on relevance score
            filtered_results = [result for result in reranked_results if result['score'] >= 6]
            
            # Step 6: Limit results to top 20
            final_results = filtered_results[:20]
            
            logger.info(f"Total final results: {len(final_results)}")
            # Log details of the first 3 profiles for inspection
            for i, result in enumerate(final_results[:3]):
                profile_info = result.get('profile', {})
                logger.info(f"Profile {i+1} ID: {profile_info.get('id')}")
                logger.info(f"Profile {i+1} Score: {result.get('score')}")
                logger.info(f"Profile {i+1} Company: {profile_info.get('company_name', 'N/A')}")
                logger.info(f"Profile {i+1} Keys: {list(profile_info.keys())}")

            logger.info(f"Retrieval and re-ranking completed. Returning {len(final_results)} results (limited from {len(reranked_results)})")
            return final_results
            
        except Exception as e:
            logger.error(f"Error in retrieve_and_rerank: {e}", exc_info=True)
            raise
    
    async def fallback_mongodb_search(
        self,
        user_query: str,
        user_id: str,
        filter_dict: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Fallback MongoDB text search when Pinecone fails or returns no results.
        Uses MongoDB's text search capabilities on connection data.
        """
        try:
            from app.core.db import get_database
            db = get_database()
            
            # Build MongoDB query - start with empty query for testing
            mongo_query = {}
            
            # Only filter by user_id if connections actually have user_id field
            # For testing purposes, we'll search all connections if no user_id field exists
            try:
                user_id_count = await db.connections.count_documents({"user_id": {"$exists": True}})
                if user_id_count > 0:
                    mongo_query["user_id"] = user_id
                else:
                    logger.info("No connections have user_id field, searching all connections for testing")
            except Exception as e:
                logger.warning(f"Could not check for user_id field: {e}, proceeding without user_id filter")
            
            # Add text search
            search_terms = user_query.lower().split()
            text_conditions = []
            
            for term in search_terms:
                # Search across multiple fields - support both field name formats
                term_conditions = [
                    # Original format (from Google Sheets direct import)
                    {"fullName": {"$regex": term, "$options": "i"}},
                    {"headline": {"$regex": term, "$options": "i"}},
                    {"about": {"$regex": term, "$options": "i"}},
                    {"companyName": {"$regex": term, "$options": "i"}},
                    {"title": {"$regex": term, "$options": "i"}},
                    {"experiences": {"$regex": term, "$options": "i"}},
                    {"skills": {"$regex": term, "$options": "i"}},
                    {"city": {"$regex": term, "$options": "i"}},
                    {"country": {"$regex": term, "$options": "i"}},
                    # Alternative format (from auto_import_google_sheets.py)
                    {"name": {"$regex": term, "$options": "i"}},
                    {"company": {"$regex": term, "$options": "i"}},
                    {"description": {"$regex": term, "$options": "i"}},
                    {"location": {"$regex": term, "$options": "i"}}
                ]
                text_conditions.append({"$or": term_conditions})
            
            if text_conditions:
                mongo_query["$and"] = text_conditions
            
            # Apply filters if provided
            if filter_dict:
                logger.info(f"Applying filters: {filter_dict}")
                
                # Handle different filter types
                for key, value in filter_dict.items():
                    if key == "$or":
                        # Handle location filters (multiple OR conditions)
                        if "$and" not in mongo_query:
                            mongo_query["$and"] = []
                        mongo_query["$and"].append({"$or": value})
                    elif key == "company_industry":
                        # Handle industry filters
                        if "$and" not in mongo_query:
                            mongo_query["$and"] = []
                        if "$in" in value:
                            # Convert to case-insensitive regex for each industry
                            industry_conditions = []
                            for industry in value["$in"]:
                                industry_conditions.extend([
                                    {"company_industry": {"$regex": industry, "$options": "i"}},
                                    {"companyName": {"$regex": industry, "$options": "i"}},
                                    {"experiences": {"$regex": industry, "$options": "i"}}
                                ])
                            mongo_query["$and"].append({"$or": industry_conditions})
                    elif key == "company_size":
                        # Handle company size filters
                        if "$and" not in mongo_query:
                            mongo_query["$and"] = []
                        if "$in" in value:
                            # Direct match for company size
                            mongo_query["$and"].append({"company_size": value})
                    elif key in ["is_hiring", "is_open_to_work", "is_company_owner", "has_pe_vc_role"]:
                        # Handle boolean filters
                        if "$and" not in mongo_query:
                            mongo_query["$and"] = []
                        
                        # Handle multiple field name variations for each boolean filter
                        if key == "is_open_to_work":
                            # Check both snake_case and camelCase variants
                            mongo_query["$and"].append({
                                "$or": [
                                    {"is_open_to_work": value},
                                    {"isOpenToWork": value}
                                ]
                            })
                        elif key == "is_hiring":
                            # Check both snake_case and camelCase variants
                            mongo_query["$and"].append({
                                "$or": [
                                    {"is_hiring": value},
                                    {"isHiring": value}
                                ]
                            })
                        elif key == "is_company_owner":
                            # Check both snake_case and camelCase variants
                            mongo_query["$and"].append({
                                "$or": [
                                    {"is_company_owner": value},
                                    {"isCompanyOwner": value}
                                ]
                            })
                        elif key == "has_pe_vc_role":
                            # Check both snake_case and camelCase variants
                            mongo_query["$and"].append({
                                "$or": [
                                    {"has_pe_vc_role": value},
                                    {"hasPeVcRole": value}
                                ]
                            })
                    else:
                        # Handle other filters directly
                        mongo_query[key] = value
            
            logger.info(f"MongoDB query: {mongo_query}")
            
            # Execute MongoDB query
            cursor = db.connections.find(mongo_query).limit(30)
            connections = await cursor.to_list(length=30)
            
            logger.info(f"MongoDB fallback found {len(connections)} connections")
            
            # Convert to the format expected by the re-ranking system
            profiles = []
            for conn in connections:
                # Extract name information - handle both fullName and name fields
                full_name = conn.get("fullName", conn.get("name", ""))
                
                # Split full name into first and last name
                name_parts = full_name.strip().split() if full_name else []
                first_name = name_parts[0] if name_parts else ""
                last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""
                
                # Convert MongoDB document to profile format with camelCase first
                profile = {
                    "id": str(conn.get("_id", conn.get("id", ""))),
                    "fullName": full_name,
                    "firstName": first_name,
                    "lastName": last_name,
                    "headline": conn.get("headline", ""),
                    "about": conn.get("about", ""),
                    "city": conn.get("city", ""),
                    "country": conn.get("country", ""),
                    "companyName": conn.get("companyName", conn.get("company", "")),
                    "title": conn.get("title", ""),
                    "experiences": conn.get("experiences", ""),
                    "education": conn.get("education", ""),
                    "skills": conn.get("skills", ""),
                    "linkedin_url": conn.get("linkedin_url", ""),
                    "profilePicture": conn.get("profilePicture", conn.get("profile_picture", "")),
                    "followerCount": conn.get("followerCount", conn.get("follower_count", 0)),
                    "connectionsCount": conn.get("connectionsCount", conn.get("connections_count", 0)),
                    "isOpenToWork": conn.get("isOpenToWork", conn.get("is_open_to_work", False)),
                    "isHiring": conn.get("isHiring", conn.get("is_hiring", False)),
                    "isPremium": conn.get("isPremium", conn.get("is_premium", False)),
                    "isTopVoice": conn.get("isTopVoice", conn.get("is_top_voice", False)),
                    "isInfluencer": conn.get("isInfluencer", conn.get("is_influencer", False)),
                    "isCreator": conn.get("isCreator", conn.get("is_creator", False)),
                    "is_company_owner": conn.get("is_company_owner", False),
                    "company_industry": conn.get("company_industry", ""),
                    "company_size": conn.get("company_size", "")
                }
                # Convert to snake_case to match Pinecone results format
                profile_snake_case = self._convert_keys_to_snake_case(profile)
                profiles.append(profile_snake_case)
            
            return profiles
            
        except Exception as e:
            logger.error(f"Error in MongoDB fallback search: {e}", exc_info=True)
            return []

# Global instance
retrieval_service = RetrievalService()
