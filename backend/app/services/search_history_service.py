from uuid import UUID
from typing import List, Union
from app.models.search_history import SearchHistoryInDB, SearchHistoryCreate

async def create_search_history_entry(db, user_id: Union[str, UUID], search_data: SearchHistoryCreate) -> dict:
    """Create a new search history entry"""
    search_entry = SearchHistoryInDB(
        **search_data.model_dump(),
        user_id=str(user_id)
    )
    
    # Convert to dict for MongoDB storage
    search_dict = search_entry.model_dump(by_alias=True)
    search_dict["_id"] = str(search_dict.pop("id")) # Use _id for MongoDB
    search_dict["user_id"] = str(search_dict["user_id"])
    
    result = await db.search_history.insert_one(search_dict)
    search_dict["_id"] = result.inserted_id
    
    return search_dict

async def get_user_search_history(db, user_id: Union[str, UUID], limit: int = 50) -> List[dict]:
    """Get user's search history, ordered by most recent"""
    cursor = db.search_history.find({"user_id": str(user_id)}).sort("searched_at", -1).limit(limit)
    search_history = await cursor.to_list(length=limit)
    
    # Convert ObjectId to string for serialization
    for entry in search_history:
        if "_id" in entry:
            entry["_id"] = str(entry["_id"])
    
    return search_history

async def delete_search_history_entry(db, user_id: Union[str, UUID], search_id: Union[str, UUID]) -> bool:
    """Delete a specific search history entry"""
    result = await db.search_history.delete_one({
        "id": str(search_id),
        "user_id": str(user_id)
    })
    
    return result.deleted_count > 0

async def clear_user_search_history(db, user_id: Union[str, UUID]) -> int:
    """Clear all search history for a user"""
    result = await db.search_history.delete_many({"user_id": str(user_id)})
    return result.deleted_count