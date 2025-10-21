import os
import asyncio
from dotenv import load_dotenv
from pinecone import Pinecone
from motor.motor_asyncio import AsyncIOMotorClient
import certifi

# Load environment variables
load_dotenv()

PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "superconnector-profiles")
DATABASE_URL = os.getenv("DATABASE_URL")
DATABASE_NAME = os.getenv("DATABASE_NAME", "superconnector")

async def check_pinecone_vs_mongodb():
    """
    Compare Pinecone index counts vs MongoDB counts to find discrepancies.
    """
    print("\n" + "="*80)
    print("PINECONE vs MONGODB COMPARISON")
    print("="*80)
    
    # Connect to MongoDB
    client = AsyncIOMotorClient(DATABASE_URL, tlsCAFile=certifi.where())
    db = client[DATABASE_NAME]
    
    try:
        # Get admin user
        admin_user = await db.users.find_one({"email": "admin@superconnect.ai"})
        if not admin_user:
            print("ERROR: Admin user not found!")
            return
        
        admin_user_id = str(admin_user.get("id") or admin_user.get("_id"))
        print(f"\nAdmin User ID: {admin_user_id}")
        
        # Count admin's connections in MongoDB
        mongodb_count = await db.connections.count_documents({"user_id": admin_user_id})
        print(f"\n1. MongoDB Admin Connections: {mongodb_count}")
        
        # Initialize Pinecone
        if not PINECONE_API_KEY:
            print("ERROR: PINECONE_API_KEY not set!")
            return
        
        pc = Pinecone(api_key=PINECONE_API_KEY)
        index = pc.Index(PINECONE_INDEX_NAME)
        
        # Get Pinecone index stats
        stats = index.describe_index_stats()
        print(f"\n2. Pinecone Index Stats:")
        print(f"   Total vectors: {stats.total_vector_count}")
        print(f"   Dimension: {stats.dimension}")
        
        # Check namespace stats
        if hasattr(stats, 'namespaces') and stats.namespaces:
            print(f"\n3. Pinecone Namespaces:")
            for namespace, ns_stats in stats.namespaces.items():
                vector_count = ns_stats.vector_count if hasattr(ns_stats, 'vector_count') else 0
                print(f"   - Namespace '{namespace}': {vector_count} vectors")
                
                if namespace == admin_user_id:
                    print(f"     ✓ This is the ADMIN namespace")
                    pinecone_admin_count = vector_count
        else:
            print("\n3. No namespace information available")
            print("   Note: Pinecone serverless indexes may not expose namespace counts")
        
        # Get all user IDs from MongoDB
        print(f"\n4. All Users with Connections:")
        pipeline = [
            {"$match": {"user_id": {"$exists": True}}},
            {"$group": {"_id": "$user_id", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}}
        ]
        
        async for result in db.connections.aggregate(pipeline):
            user_id = result["_id"]
            count = result["count"]
            
            user = await db.users.find_one({"$or": [{"id": user_id}, {"_id": user_id}]})
            email = user.get("email", "Unknown") if user else "Unknown"
            
            print(f"   - {email} (ID: {user_id})")
            print(f"     MongoDB: {count} connections")
        
        # Summary
        print(f"\n" + "="*80)
        print("SUMMARY")
        print("="*80)
        print(f"MongoDB has {mongodb_count} admin connections")
        print(f"Pinecone has {stats.total_vector_count} total vectors")
        
        if mongodb_count > stats.total_vector_count:
            missing = mongodb_count - stats.total_vector_count
            print(f"\n⚠️  DISCREPANCY FOUND!")
            print(f"   {missing} connections in MongoDB are NOT in Pinecone")
            print(f"\n💡 SOLUTION:")
            print(f"   Run the embedding service to index the missing connections:")
            print(f"   - Use the /connections/upload endpoint to re-upload")
            print(f"   - Or run: python3 setup_pinecone_index.py")
        else:
            print(f"\n✓ MongoDB and Pinecone counts match!")
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        client.close()

if __name__ == "__main__":
    asyncio.run(check_pinecone_vs_mongodb())

