from uuid import UUID
from typing import List, Optional
from datetime import datetime
from app.models.saved_search import SavedSearchInDB, SavedSearchCreate, SavedSearchPublic

async def create_saved_search(db, user_id: UUID, saved_search_data: SavedSearchCreate) -> dict:
    """Create a new saved search for a user"""
    saved_search = SavedSearchInDB(
        **saved_search_data.model_dump(),
        user_id=user_id
    )
    
    # Convert to dict for MongoDB storage
    saved_search_dict = saved_search.model_dump(by_alias=True)
    saved_search_dict["id"] = str(saved_search_dict["id"])
    saved_search_dict["user_id"] = str(saved_search_dict["user_id"])
    
    result = await db.saved_searches.insert_one(saved_search_dict)
    saved_search_dict["_id"] = result.inserted_id
    
    return saved_search_dict

async def get_user_saved_searches(db, user_id: UUID) -> List[dict]:
    """Get all saved searches for a user"""
    cursor = db.saved_searches.find({"user_id": str(user_id)}).sort("created_at", -1)
    saved_searches = await cursor.to_list(length=None)
    return saved_searches

async def get_saved_search_by_id(db, user_id: UUID, search_id: UUID) -> Optional[dict]:
    """Get a specific saved search by ID"""
    saved_search = await db.saved_searches.find_one({
        "id": str(search_id),
        "user_id": str(user_id)
    })
    return saved_search

async def update_saved_search(db, user_id: UUID, search_id: UUID, update_data: dict) -> Optional[dict]:
    """Update a saved search"""
    update_data["updated_at"] = datetime.utcnow()
    
    result = await db.saved_searches.update_one(
        {"id": str(search_id), "user_id": str(user_id)},
        {"$set": update_data}
    )
    
    if result.modified_count == 0:
        return None
    
    return await get_saved_search_by_id(db, user_id, search_id)

async def delete_saved_search(db, user_id: UUID, search_id: UUID) -> bool:
    """Delete a saved search"""
    result = await db.saved_searches.delete_one({
        "id": str(search_id),
        "user_id": str(user_id)
    })
    
    return result.deleted_count > 0