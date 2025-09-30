import asyncio
import os
import json
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def analyze_current_database():
    """Analyze the current database to understand the data structure"""
    
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ DATABASE_URL not found in environment variables")
        return None
        
    print(f"🔗 Connecting to: {database_url[:50]}...")
    
    try:
        client = AsyncIOMotorClient(database_url)
        db = client.superconnect_ai
        
        # Test connection
        await client.admin.command('ping')
        print("✅ Database connection successful!")
        
        # Get collections
        collections = await db.list_collection_names()
        print(f"📁 Collections found: {collections}")
        
        # Analyze connections collection
        if 'connections' in collections:
            total_connections = await db.connections.count_documents({})
            print(f"📊 Total connections: {total_connections}")
            
            if total_connections > 0:
                # Sample connections
                sample = await db.connections.find({}).limit(3).to_list(length=3)
                print(f"\n📋 Sample connections:")
                for i, conn in enumerate(sample, 1):
                    print(f"   {i}. {conn.get('fullName', 'Unknown')} - {conn.get('companyName', 'Unknown')}")
                
                # Check user_id distribution
                with_user_id = await db.connections.count_documents({"user_id": {"$exists": True}})
                without_user_id = total_connections - with_user_id
                
                print(f"\n🔍 User ID Analysis:")
                print(f"   With user_id: {with_user_id}")
                print(f"   Without user_id: {without_user_id}")
                
                if with_user_id > 0:
                    user_ids = await db.connections.distinct("user_id")
                    print(f"   Unique user_ids: {len(user_ids)}")
                    
                    # Show connections per user
                    for user_id in user_ids[:5]:  # Show first 5 users
                        count = await db.connections.count_documents({"user_id": user_id})
                        print(f"     - {user_id}: {count} connections")
                
                # Check for OpenAI connections
                openai_connections = await db.connections.count_documents({
                    "$or": [
                        {"companyName": {"$regex": "OpenAI", "$options": "i"}},
                        {"companyName": {"$regex": "Open AI", "$options": "i"}},
                        {"experiences": {"$regex": "OpenAI", "$options": "i"}},
                        {"about": {"$regex": "OpenAI", "$options": "i"}}
                    ]
                })
                print(f"\n🔍 OpenAI-related connections: {openai_connections}")
                
                if openai_connections > 0:
                    openai_sample = await db.connections.find({
                        "$or": [
                            {"companyName": {"$regex": "OpenAI", "$options": "i"}},
                            {"companyName": {"$regex": "Open AI", "$options": "i"}},
                            {"experiences": {"$regex": "OpenAI", "$options": "i"}},
                            {"about": {"$regex": "OpenAI", "$options": "i"}}
                        ]
                    }).limit(3).to_list(length=3)
                    
                    print(f"   Sample OpenAI connections:")
                    for conn in openai_sample:
                        print(f"     - {conn.get('fullName', 'Unknown')} at {conn.get('companyName', 'Unknown')}")
        
        client.close()
        return total_connections
        
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return None

async def export_connections_to_json(filename="production_connections_export.json"):
    """Export all connections to a JSON file"""
    
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ DATABASE_URL not found")
        return False
    
    try:
        client = AsyncIOMotorClient(database_url)
        db = client.superconnect_ai
        
        print("📤 Exporting connections to JSON...")
        
        # Get all connections
        connections = await db.connections.find({}).to_list(length=None)
        
        # Convert ObjectId and datetime to strings
        for conn in connections:
            for key, value in conn.items():
                if hasattr(value, 'isoformat'):  # datetime
                    conn[key] = value.isoformat()
                elif hasattr(value, '__str__') and key == '_id':  # ObjectId
                    conn[key] = str(value)
        
        # Save to file
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(connections, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Exported {len(connections)} connections to {filename}")
        print(f"📁 File size: {os.path.getsize(filename) / 1024 / 1024:.2f} MB")
        
        client.close()
        return True
        
    except Exception as e:
        print(f"❌ Export failed: {e}")
        return False

async def import_connections_from_json(filename="production_connections_export.json", clear_existing=True):
    """Import connections from JSON file"""
    
    if not os.path.exists(filename):
        print(f"❌ File {filename} not found")
        return False
    
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ DATABASE_URL not found")
        return False
    
    try:
        client = AsyncIOMotorClient(database_url)
        db = client.superconnect_ai
        
        # Load data
        with open(filename, 'r', encoding='utf-8') as f:
            connections = json.load(f)
        
        print(f"📥 Importing {len(connections)} connections...")
        
        if clear_existing:
            # Clear existing connections
            result = await db.connections.delete_many({})
            print(f"🗑️  Cleared {result.deleted_count} existing connections")
        
        # Import in batches
        batch_size = 1000
        imported = 0
        
        for i in range(0, len(connections), batch_size):
            batch = connections[i:i + batch_size]
            
            # Convert string dates back to datetime if needed
            for conn in batch:
                for key, value in conn.items():
                    if key in ['created_at', 'updated_at'] and isinstance(value, str):
                        try:
                            conn[key] = datetime.fromisoformat(value)
                        except:
                            conn[key] = datetime.utcnow()
            
            await db.connections.insert_many(batch)
            imported += len(batch)
            print(f"   Imported {imported}/{len(connections)} connections...")
        
        print(f"✅ Import completed: {imported} connections")
        
        # Verify import
        total = await db.connections.count_documents({})
        print(f"📊 Total connections in database: {total}")
        
        client.close()
        return True
        
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False

async def search_for_openai_connections():
    """Search for OpenAI-related connections to test the dataset"""
    
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ DATABASE_URL not found")
        return
    
    try:
        client = AsyncIOMotorClient(database_url)
        db = client.superconnect_ai
        
        # Search for OpenAI connections
        openai_query = {
            "$or": [
                {"companyName": {"$regex": "OpenAI", "$options": "i"}},
                {"companyName": {"$regex": "Open AI", "$options": "i"}},
                {"title": {"$regex": "OpenAI", "$options": "i"}},
                {"experiences": {"$regex": "OpenAI", "$options": "i"}},
                {"about": {"$regex": "OpenAI", "$options": "i"}},
                {"headline": {"$regex": "OpenAI", "$options": "i"}}
            ]
        }
        
        openai_connections = await db.connections.find(openai_query).to_list(length=10)
        
        print(f"🔍 Found {len(openai_connections)} OpenAI-related connections:")
        for conn in openai_connections:
            print(f"   - {conn.get('fullName', 'Unknown')}")
            print(f"     Company: {conn.get('companyName', 'Unknown')}")
            print(f"     Title: {conn.get('title', 'Unknown')}")
            print(f"     Headline: {conn.get('headline', 'Unknown')[:100]}...")
            print()
        
        # Also search for product leaders
        product_query = {
            "$or": [
                {"title": {"$regex": "product.*lead", "$options": "i"}},
                {"title": {"$regex": "lead.*product", "$options": "i"}},
                {"headline": {"$regex": "product.*lead", "$options": "i"}},
                {"headline": {"$regex": "lead.*product", "$options": "i"}}
            ]
        }
        
        product_leaders = await db.connections.find(product_query).limit(5).to_list(length=5)
        print(f"🎯 Found {len(product_leaders)} product leaders:")
        for conn in product_leaders:
            print(f"   - {conn.get('fullName', 'Unknown')} at {conn.get('companyName', 'Unknown')}")
        
        client.close()
        
    except Exception as e:
        print(f"❌ Search failed: {e}")

async def main():
    """Main migration workflow"""
    
    print("🚀 SuperconnectAI Connection Migration Tool")
    print("=" * 50)
    
    # Step 1: Analyze current database
    print("\n1️⃣ Analyzing current database...")
    connection_count = await analyze_current_database()
    
    if connection_count is None:
        print("❌ Cannot proceed without database connection")
        return
    
    if connection_count < 1000:
        print(f"\n⚠️  Current database has only {connection_count} connections")
        print("   This appears to be a development database, not production")
        print("   Production should have 15,000+ connections")
        print("\n💡 Next steps:")
        print("   1. Check Vercel dashboard for production DATABASE_URL")
        print("   2. Update .env with production database URL")
        print("   3. Re-run this script")
        return
    
    print(f"\n🎉 Found {connection_count} connections - this looks like production data!")
    
    # Step 2: Search for specific connections
    print("\n2️⃣ Searching for OpenAI and product leader connections...")
    await search_for_openai_connections()
    
    # Step 3: Offer export option
    print("\n3️⃣ Migration options:")
    print("   - Current database appears to have the full dataset")
    print("   - You can export this data for backup/analysis")
    print("   - Or use this database directly for testing")
    
    export_choice = input("\nWould you like to export connections to JSON? (y/n): ").lower().strip()
    if export_choice == 'y':
        await export_connections_to_json()
    
    print("\n✅ Migration analysis complete!")
    print("   Your environment appears to already have access to the full dataset")

if __name__ == "__main__":
    asyncio.run(main())