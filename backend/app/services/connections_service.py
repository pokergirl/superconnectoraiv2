import csv
import io
from uuid import UUID
from fastapi import HTTPException, status, UploadFile
from app.models.connection import ConnectionInDB

async def process_csv_upload(db, file: UploadFile, user_id: UUID):
    # First, delete all existing connections for this user
    await db.connections.delete_many({"user_id": str(user_id)})

    # Read the CSV file content
    content = await file.read()
    stream = io.StringIO(content.decode("utf-8"))
    reader = csv.DictReader(stream)

    connections_to_insert = []
    for row in reader:
        # Map CSV columns to your Connection model fields
        # This assumes CSV headers match your model field names (e.g., "first_name", "last_name")
        # You might need to adjust this mapping based on the actual CSV format.
        connection_data = {
            # Personal Information
            "first_name": row.get("First Name", ""),
            "last_name": row.get("Last Name", ""),
            "linkedin_url": row.get("LinkedinUrl") or None,
            "email_address": row.get("Email Address") or None,
            "city": row.get("City") or None,
            "state": row.get("State") or None,
            "country": row.get("Country") or None,
            "followers": row.get("Followers") or None,
            "description": row.get("Description/0") or None,
            
            # Connection Information
            "connected_on": row.get("Connected On") or None,
            
            # Current Company Information
            "company": row.get("Company") or None,
            "title": row.get("Title") or None,
            
            # Company Details
            "company_size": row.get("Company size") or None,
            "company_name": row.get("CompanyName") or None,
            "company_website": row.get("CompanyWebsite") or None,
            "company_phone": row.get("CompanyPhone/0") or None,
            "company_industry": row.get("CompanyIndustry") or None,
            "company_industry_topics": row.get("CompanyIndustryTopics") or None,
            "company_description": row.get("CompanyDescription") or None,
            "company_address": row.get("CompanyAddress/0") or None,
            "company_city": row.get("CompanyCity/0") or None,
            "company_state": row.get("CompanyState/0") or None,
            "company_country": row.get("CompanyCountry/0") or None,
            "company_revenue": row.get("CompanyRevenue") or None,
            "company_latest_funding": row.get("CompanyLatestFunding/0") or None,
            "company_linkedin": row.get("CompanyLinkedIn") or None,
            
            "user_id": user_id,
        }
        
        # Create a ConnectionInDB instance to get default values and validate
        new_connection = ConnectionInDB(**connection_data)
        # Convert UUIDs to strings for MongoDB storage
        connection_dict = new_connection.model_dump(by_alias=True)
        connection_dict["id"] = str(connection_dict["id"])
        connection_dict["user_id"] = str(connection_dict["user_id"])
        connections_to_insert.append(connection_dict)

    if connections_to_insert:
        await db.connections.insert_many(connections_to_insert)
    
    return len(connections_to_insert)

async def get_user_connections(db, user_id: UUID, page: int = 1, limit: int = 100):
    skip = (page - 1) * limit
    cursor = db.connections.find({"user_id": str(user_id)}).skip(skip).limit(limit)
    connections = await cursor.to_list(length=limit)
    return connections

async def delete_user_connections(db, user_id: UUID):
    result = await db.connections.delete_many({"user_id": str(user_id)})
    return result.deleted_count

async def get_user_connections_count(db, user_id: UUID):
    count = await db.connections.count_documents({"user_id": str(user_id)})
    return count