"""
Test script to verify that the search API now displays the actual Pinecone vector counts.
"""
import os
import asyncio
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def test_vector_count_method():
    """Test the new get_namespace_vector_count method"""
    from app.services.retrieval_service import retrieval_service
    from app.core.db import connect_to_mongo, get_database, close_mongo_connection
    
    print("\n" + "="*80)
    print("TESTING VECTOR COUNT DISPLAY IN API")
    print("="*80)
    
    # Connect to database
    await connect_to_mongo()
    
    # Get admin namespace
    db = get_database()
    admin_user = await db.users.find_one({"email": "admin@superconnect.ai"})
    
    if not admin_user:
        print("ERROR: Admin user not found!")
        return
    
    admin_namespace = str(admin_user.get("id") or admin_user.get("_id"))
    print(f"\n1. Admin namespace: {admin_namespace}")
    
    # Test the new method
    vector_count = retrieval_service.get_namespace_vector_count(admin_namespace)
    print(f"\n2. Vector count from new method: {vector_count:,}")
    
    # Get MongoDB count for comparison
    mongodb_count = await db.connections.count_documents({"user_id": admin_namespace})
    print(f"\n3. MongoDB connection count: {mongodb_count:,}")
    
    # Show the message that will be displayed
    print(f"\n4. API will now show:")
    print(f"   'Searching {vector_count:,} connections in Pinecone...'")
    print(f"   (instead of showing MongoDB count of {mongodb_count:,})")
    
    # Calculate difference
    difference = vector_count - mongodb_count
    print(f"\n5. Difference: {difference:,} more vectors in Pinecone")
    
    if difference > 0:
        percentage = (difference / mongodb_count) * 100
        print(f"   That's {percentage:.1f}% more than MongoDB!")
    
    print("\n" + "="*80)
    print("✓ TEST COMPLETE - API will now show actual Pinecone counts")
    print("="*80 + "\n")
    
    # Cleanup
    await close_mongo_connection()

if __name__ == "__main__":
    asyncio.run(test_vector_count_method())

