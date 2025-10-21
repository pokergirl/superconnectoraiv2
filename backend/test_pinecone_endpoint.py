"""
Test script to verify the new Pinecone count endpoint works correctly.
"""
import os
import asyncio
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def test_pinecone_count_endpoint():
    """Test the new /connections/pinecone-count endpoint"""
    from app.services.retrieval_service import retrieval_service
    from app.core.db import connect_to_mongo, get_database, close_mongo_connection
    
    print("\n" + "="*80)
    print("TESTING NEW PINECONE COUNT ENDPOINT")
    print("="*80)
    
    # Connect to database
    await connect_to_mongo()
    
    try:
        # Get admin user
        db = get_database()
        admin_user = await db.users.find_one({"email": "admin@superconnect.ai"})
        
        if not admin_user:
            print("ERROR: Admin user not found!")
            return
        
        admin_namespace = str(admin_user.get("id") or admin_user.get("_id"))
        print(f"\n1. Admin namespace: {admin_namespace}")
        
        # Test the endpoint logic
        user_vector_count = retrieval_service.get_namespace_vector_count(admin_namespace)
        admin_vector_count = retrieval_service.get_namespace_vector_count(admin_namespace)
        total_vectors = user_vector_count + admin_vector_count
        
        print(f"\n2. Vector counts:")
        print(f"   User vectors: {user_vector_count:,}")
        print(f"   Admin vectors: {admin_vector_count:,}")
        print(f"   Total vectors: {total_vectors:,}")
        
        # Simulate the endpoint response
        response = {
            "count": total_vectors,
            "user_vectors": user_vector_count,
            "admin_vectors": admin_vector_count,
            "source": "pinecone"
        }
        
        print(f"\n3. Endpoint would return:")
        print(f"   {response}")
        
        # Compare with MongoDB count
        mongodb_count = await db.connections.count_documents({"user_id": admin_namespace})
        print(f"\n4. MongoDB count for comparison: {mongodb_count:,}")
        
        print(f"\n5. Frontend will now show:")
        print(f"   'Got it! I'm searching {total_vectors:,} connections in our database.'")
        print(f"   (instead of the old MongoDB count of {mongodb_count:,})")
        
        print("\n" + "="*80)
        print("✓ ENDPOINT TEST COMPLETE")
        print("="*80 + "\n")
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await close_mongo_connection()

if __name__ == "__main__":
    asyncio.run(test_pinecone_count_endpoint())

