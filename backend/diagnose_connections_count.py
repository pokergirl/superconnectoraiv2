import os
import asyncio
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
import certifi

# Load environment variables from .env file
load_dotenv()

# Get MongoDB configuration from environment variables
DATABASE_URL = os.getenv("DATABASE_URL")
DATABASE_NAME = os.getenv("DATABASE_NAME", "superconnector")

async def diagnose_connections():
    """
    Diagnoses connection counts in MongoDB to understand why only 3,602 are being searched.
    """
    if not DATABASE_URL:
        print("Error: DATABASE_URL must be set in your environment variables.")
        return

    try:
        client = AsyncIOMotorClient(DATABASE_URL, tlsCAFile=certifi.where())
        db = client[DATABASE_NAME]

        print("\n" + "="*80)
        print("CONNECTION COUNT DIAGNOSIS")
        print("="*80)

        # 1. Total connections in database
        total_connections = await db.connections.count_documents({})
        print(f"\n1. TOTAL CONNECTIONS IN DATABASE: {total_connections}")

        # 2. Connections with user_id field
        connections_with_user_id = await db.connections.count_documents({"user_id": {"$exists": True}})
        print(f"\n2. CONNECTIONS WITH user_id FIELD: {connections_with_user_id}")

        # 3. Connections without user_id field
        connections_without_user_id = await db.connections.count_documents({"user_id": {"$exists": False}})
        print(f"   CONNECTIONS WITHOUT user_id FIELD: {connections_without_user_id}")

        # 4. Find admin user
        admin_user = await db.users.find_one({"email": "admin@superconnect.ai"})
        if admin_user:
            admin_user_id = str(admin_user.get("id") or admin_user.get("_id"))
            print(f"\n3. ADMIN USER ID: {admin_user_id}")
            
            # Count admin's connections
            admin_connections = await db.connections.count_documents({"user_id": admin_user_id})
            print(f"   ADMIN'S CONNECTIONS: {admin_connections}")
        else:
            print("\n3. ADMIN USER NOT FOUND")
            admin_user_id = None
            admin_connections = 0

        # 5. Get all unique user_ids in connections
        print("\n4. CONNECTIONS BY USER:")
        pipeline = [
            {"$match": {"user_id": {"$exists": True}}},
            {"$group": {"_id": "$user_id", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}}
        ]
        
        async for result in db.connections.aggregate(pipeline):
            user_id = result["_id"]
            count = result["count"]
            
            # Try to find user details
            user = await db.users.find_one({"$or": [{"id": user_id}, {"_id": user_id}]})
            if user:
                email = user.get("email", "Unknown")
                print(f"   - {email} (ID: {user_id}): {count} connections")
            else:
                print(f"   - Unknown user (ID: {user_id}): {count} connections")

        # 6. Check what the API would return for a specific user
        print("\n5. SIMULATING API COUNT:")
        
        # Find a non-admin user
        non_admin_users = await db.users.find({"email": {"$ne": "admin@superconnect.ai"}}).limit(1).to_list(length=1)
        
        if non_admin_users:
            test_user = non_admin_users[0]
            test_user_id = str(test_user.get("id") or test_user.get("_id"))
            test_user_email = test_user.get("email", "Unknown")
            
            print(f"   Testing with user: {test_user_email} (ID: {test_user_id})")
            
            # Simulate what get_user_connections_count does
            user_ids_to_count = [test_user_id]
            if admin_user_id and admin_user_id != test_user_id:
                user_ids_to_count.append(admin_user_id)
            
            api_count = await db.connections.count_documents({"user_id": {"$in": user_ids_to_count}})
            print(f"   API would return: {api_count} connections")
            print(f"   (User's own: {await db.connections.count_documents({'user_id': test_user_id})})")
            print(f"   (Admin's: {admin_connections})")
        else:
            print("   No non-admin users found")

        # 7. Check Pinecone namespace info if available
        print("\n6. ADDITIONAL INFO:")
        print(f"   - The API is currently returning 3,602 connections")
        print(f"   - This represents connections with user_id assigned to:")
        print(f"     * The current user")
        print(f"     * The admin user (admin@superconnect.ai)")
        
        if total_connections > connections_with_user_id:
            print(f"\n⚠️  WARNING: There are {connections_without_user_id} connections without user_id!")
            print(f"   These connections are NOT being included in searches.")
            print(f"   You may need to assign user_id to these connections.")

        print("\n" + "="*80)
        print("DIAGNOSIS COMPLETE")
        print("="*80 + "\n")

    except Exception as e:
        print(f"An error occurred: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if 'client' in locals():
            client.close()

if __name__ == "__main__":
    asyncio.run(diagnose_connections())

