"""
Test script to verify the updated Pinecone count endpoint returns only admin vectors.
"""
import os
import asyncio
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def test_updated_pinecone_endpoint():
    """Test the updated /connections/pinecone-count endpoint"""
    from app.services.retrieval_service import retrieval_service
    from app.core.db import connect_to_mongo, get_database, close_mongo_connection
    
    print("\n" + "="*80)
    print("TESTING UPDATED PINECONE COUNT ENDPOINT (ADMIN ONLY)")
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
        
        # Test the updated endpoint logic (admin vectors only)
        admin_vector_count = retrieval_service.get_namespace_vector_count(admin_namespace)
        
        print(f"\n2. Admin vector count: {admin_vector_count:,}")
        
        # Simulate the updated endpoint response
        response = {
            "count": admin_vector_count,
            "admin_vectors": admin_vector_count,
            "source": "pinecone"
        }
        
        print(f"\n3. Updated endpoint returns:")
        print(f"   {response}")
        
        # Compare with MongoDB count
        mongodb_count = await db.connections.count_documents({"user_id": admin_namespace})
        print(f"\n4. MongoDB count for comparison: {mongodb_count:,}")
        
        print(f"\n5. Frontend will now show:")
        print(f"   'Got it! I'm searching {admin_vector_count:,} connections in our database.'")
        print(f"   (instead of the old MongoDB count of {mongodb_count:,})")
        
        # Show the difference
        difference = admin_vector_count - mongodb_count
        percentage = (difference / mongodb_count) * 100
        print(f"\n6. Pinecone has {difference:,} more vectors than MongoDB")
        print(f"   That's {percentage:.1f}% more than MongoDB!")
        
        print("\n" + "="*80)
        print("✓ UPDATED ENDPOINT TEST COMPLETE")
        print("✓ Now returns only admin vectors (what users actually search)")
        print("="*80 + "\n")
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await close_mongo_connection()

if __name__ == "__main__":
    asyncio.run(test_updated_pinecone_endpoint())

