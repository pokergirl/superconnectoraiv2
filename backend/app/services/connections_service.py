import csv
import io
from uuid import UUID
from fastapi import HTTPException, status, UploadFile
from app.models.connection import ConnectionInDB
import random

async def process_and_store_connections(db, file: UploadFile, user_id: UUID):
    # First, delete all existing connections for this user
    await db.connections.delete_many({"user_id": str(user_id)})

    # Read the CSV file content
    content = await file.read()
    stream = io.StringIO(content.decode("utf-8"))
    reader = csv.DictReader(stream)

    records_to_insert = []
    for row in reader:
        # Map CSV columns to your Connection model fields
        # This assumes CSV headers match your model field names (e.g., "first_name", "last_name")
        # You might need to adjust this mapping based on the actual CSV format.
        record = {
            # Personal Information
            "first_name": row.get("firstName", ""),
            "last_name": row.get("lastName", ""),
            "linkedin_url": f"https://www.linkedin.com/in/{row.get('publicIdentifier')}" if row.get('publicIdentifier') else None,
            "email_address": None,  # Not available in new CSV
            "city": row.get("city") or None,
            "state": None,  # Not available in new CSV
            "country": row.get("country") or None,
            "followers": row.get("followerCount") or None,
            "description": row.get("about") or None,
            "headline": row.get("headline") or None,
            
            # Connection Information
            "connected_on": None,  # Not available in new CSV
            
            # Current Company Information
            "company": row.get("companyName") or None,
            "title": None,  # Not available in new CSV
            
            # Company Details
            "company_size": None,  # Not available in new CSV
            "company_name": row.get("companyName") or None,
            "company_website": None,  # Not available in new CSV
            "company_phone": None,  # Not available in new CSV
            "company_industry": None,  # Not available in new CSV
            "company_industry_topics": None,  # Not available in new CSV
            "company_description": None,  # Not available in new CSV
            "company_address": None,  # Not available in new CSV
            "company_city": None,  # Not available in new CSV
            "company_state": None,  # Not available in new CSV
            "company_country": None,  # Not available in new CSV
            "company_revenue": None,  # Not available in new CSV
            "company_latest_funding": None,  # Not available in new CSV
            "company_linkedin": None,  # Not available in new CSV
        }
        record['user_id'] = user_id
        record['rating'] = random.randint(1, 10)
        
        # Create a ConnectionInDB instance to get default values and validate
        new_connection = ConnectionInDB(**record)
        # Convert UUIDs to strings for MongoDB storage
        connection_dict = new_connection.model_dump(by_alias=True)
        connection_dict["id"] = str(connection_dict["id"])
        connection_dict["user_id"] = str(connection_dict["user_id"])
        records_to_insert.append(connection_dict)

    if records_to_insert:
        try:
            await db.connections.insert_many(records_to_insert, ordered=False)
        except Exception as e:
            # This will catch errors like duplicate keys if any slip through,
            # but with `ordered=False`, it will attempt to insert all non-dups.
            print(f"An error occurred during bulk insert, but some records may have been inserted: {e}")
    
    return len(records_to_insert)

async def get_user_connections(db, user_id: UUID, page: int = 1, limit: int = 100, min_rating: int = None):
    skip = (page - 1) * limit
    query = {"user_id": str(user_id)}
    if min_rating is not None:
        query["rating"] = {"$gte": min_rating}
    
    cursor = db.connections.find(query).skip(skip).limit(limit)
    connections = await cursor.to_list(length=limit)
    
    # Ensure premium badge fields are properly mapped for frontend
    for conn in connections:
        # Map premium fields from both possible field name formats
        if 'is_premium' not in conn and 'isPremium' in conn:
            conn['is_premium'] = conn['isPremium']
        if 'is_top_voice' not in conn and 'isTopVoice' in conn:
            conn['is_top_voice'] = conn['isTopVoice']
        if 'is_influencer' not in conn and 'isInfluencer' in conn:
            conn['is_influencer'] = conn['isInfluencer']
        if 'is_hiring' not in conn and 'isHiring' in conn:
            conn['is_hiring'] = conn['isHiring']
        if 'is_open_to_work' not in conn and 'isOpenToWork' in conn:
            conn['is_open_to_work'] = conn['isOpenToWork']
        if 'is_creator' not in conn and 'isCreator' in conn:
            conn['is_creator'] = conn['isCreator']
    
    return connections

async def delete_user_connections(db, user_id: UUID):
    result = await db.connections.delete_many({"user_id": str(user_id)})
    return result.deleted_count

async def get_user_connections_count(db, user_id: UUID):
    # First try to count connections with user_id
    count_with_user_id = await db.connections.count_documents({"user_id": str(user_id)})
    
    # If no connections found with user_id, check if there are connections without user_id
    # This handles the case where connections were imported without user_id assignment
    if count_with_user_id == 0:
        count_without_user_id = await db.connections.count_documents({"user_id": {"$exists": False}})
        if count_without_user_id > 0:
            # Return total connections without user_id for testing/demo purposes
            return count_without_user_id
    
    return count_with_user_id