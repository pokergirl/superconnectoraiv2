import asyncio
import os
import sys
from uuid import uuid4

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.db import connect_to_mongo, close_mongo_connection, get_database
from app.services.retrieval_service import retrieval_service
from app.models.user import UserPublic

async def main():
    print("--- Starting Search Functionality Test ---")
    await connect_to_mongo()
    db = get_database()

    try:
        # 1. Test User ID validation
        print("\n[1/3] Testing User ID validation...")
        try:
            user_id = uuid4()
            user_public = UserPublic(
                id=user_id,
                email='test@example.com',
                role='user',
                status='active',
                is_premium=False,
                must_change_password=False,
                created_at='2023-01-01T00:00:00',
                last_login=None
            )
            print(f"  - Successfully created UserPublic with UUID: {user_public.id}")
        except Exception as e:
            print(f"  - FAILED: User ID validation failed: {e}")
            return

        # 2. Test Gemini and OpenAI API initialization
        print("\n[2/3] Testing API initializations...")
        if retrieval_service.gemini_client:
            print("  - Gemini client initialized successfully.")
        else:
            print("  - WARNING: Gemini client failed to initialize.")

        # Assuming there's an openai_client to check
        if hasattr(retrieval_service, 'openai_client') and retrieval_service.openai_client:
            print("  - OpenAI client initialized successfully.")
        else:
            print("  - NOTE: OpenAI client not found or not initialized (may be expected).")

        # 3. Test end-to-end search
        print("\n[3/3] Testing end-to-end search...")
        try:
            search_results = await retrieval_service.retrieve_and_rerank(
                user_query="software engineer",
                user_id=str(user_id),
                enable_query_rewrite=False,
                filter_dict=None
            )
            print(f"  - Search completed. Found {len(search_results)} results.")
            if search_results:
                print("  - Sample result:", search_results)
            print("  - SUCCESS: End-to-end search test passed.")
        except Exception as e:
            print(f"  - FAILED: End-to-end search failed: {e}")

    finally:
        await close_mongo_connection()
        print("\n--- Test Finished ---")

if __name__ == "__main__":
    asyncio.run(main())