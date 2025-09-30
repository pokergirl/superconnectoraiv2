#!/usr/bin/env python3
"""
Fix Connection User IDs - Associate existing connections with admin user
This script will assign all existing connections to the admin user so search works
"""

import asyncio
import sys
import os

# Add the backend directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.db import connect_to_mongo, close_mongo_connection, get_database

async def fix_connection_user_ids():
    """Associate all existing connections with the admin user"""
    print("🔧 Fixing connection user_id associations...")
    print("=" * 50)
    
    # Connect to database
    await connect_to_mongo()
    db = get_database()
    
    # Find the admin user
    admin_user = await db.users.find_one({"email": "admin@superconnect.ai"})
    if not admin_user:
        print("❌ Admin user not found! Please run create_admin_user.py first")
        await close_mongo_connection()
        return
    
    admin_user_id = admin_user.get("id") or str(admin_user.get("_id"))
    print(f"✅ Found admin user: {admin_user['email']}")
    print(f"   User ID: {admin_user_id}")
    
    # Check current state
    total_connections = await db.connections.count_documents({})
    connections_with_user_id = await db.connections.count_documents({"user_id": {"$exists": True}})
    connections_without_user_id = total_connections - connections_with_user_id
    
    print(f"\n📊 Current state:")
    print(f"   Total connections: {total_connections}")
    print(f"   With user_id: {connections_with_user_id}")
    print(f"   Without user_id: {connections_without_user_id}")
    
    if connections_without_user_id == 0:
        print("\n✅ All connections already have user_id assigned!")
        await close_mongo_connection()
        return
    
    # Update all connections without user_id
    print(f"\n🔄 Assigning user_id to {connections_without_user_id} connections...")
    
    result = await db.connections.update_many(
        {"user_id": {"$exists": False}},  # Filter: connections without user_id
        {"$set": {"user_id": admin_user_id}}  # Update: set user_id
    )
    
    print(f"✅ Updated {result.modified_count} connections")
    
    # Verify the fix
    final_connections_with_user_id = await db.connections.count_documents({"user_id": {"$exists": True}})
    print(f"\n📈 Final state:")
    print(f"   Total connections: {total_connections}")
    print(f"   With user_id: {final_connections_with_user_id}")
    print(f"   Coverage: {final_connections_with_user_id/total_connections*100:.1f}%")
    
    if final_connections_with_user_id == total_connections:
        print("\n🎉 SUCCESS! All connections now have user_id assigned")
        print("\n📋 Next steps:")
        print("1. Login with admin@superconnect.ai / admin123")
        print("2. Try searching for connections")
        print("3. Search should now return results!")
    else:
        print(f"\n⚠️  Warning: {total_connections - final_connections_with_user_id} connections still missing user_id")
    
    # Close database connection
    await close_mongo_connection()

if __name__ == "__main__":
    asyncio.run(fix_connection_user_ids())