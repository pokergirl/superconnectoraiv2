from uuid import UUID
from typing import List, Optional, Union
from datetime import datetime
import logging
from app.models.saved_search import SavedSearchInDB, SavedSearchCreate, SavedSearchPublic

logger = logging.getLogger(__name__)

def safe_uuid_to_string(uuid_value: Union[UUID, str]) -> str:
    """
    Safely convert UUID object to string, handling both UUID objects and strings.
    
    Args:
        uuid_value: Either a UUID object or string
        
    Returns:
        String representation of the UUID
        
    Raises:
        ValueError: If the input cannot be converted to a valid UUID string
    """
    try:
        if isinstance(uuid_value, UUID):
            return str(uuid_value)
        elif isinstance(uuid_value, str):
            # Validate that it's a proper UUID string
            UUID(uuid_value)  # This will raise ValueError if invalid
            return uuid_value
        else:
            raise ValueError(f"Expected UUID or string, got {type(uuid_value)}")
    except Exception as e:
        logger.error(f"Error converting UUID to string: {e}, input: {uuid_value}")
        raise ValueError(f"Invalid UUID format: {uuid_value}")

async def create_saved_search(db, user_id: Union[UUID, str], saved_search_data: SavedSearchCreate) -> dict:
    """Create a new saved search for a user"""
    try:
        user_id_str = safe_uuid_to_string(user_id)
        logger.info(f"Creating saved search for user: {user_id_str}")
        
        saved_search = SavedSearchInDB(
            **saved_search_data.model_dump(),
            user_id=user_id_str
        )
        
        # Convert to dict for MongoDB storage
        saved_search_dict = saved_search.model_dump(by_alias=True)
        # The id field is aliased as "_id" for MongoDB
        if "_id" in saved_search_dict:
            saved_search_dict["_id"] = safe_uuid_to_string(saved_search_dict["_id"])
        saved_search_dict["user_id"] = user_id_str
        
        result = await db.saved_searches.insert_one(saved_search_dict)
        saved_search_dict["_id"] = result.inserted_id
        
        # Ensure the frontend gets the id field it expects
        if "_id" in saved_search_dict:
            saved_search_dict["id"] = str(saved_search_dict["_id"])
        
        logger.info(f"Successfully created saved search with ID: {saved_search_dict.get('id')}")
        return saved_search_dict
        
    except Exception as e:
        logger.error(f"Error creating saved search for user {user_id}: {e}")
        raise

async def get_user_saved_searches(db, user_id: Union[UUID, str]) -> List[dict]:
    """Get all saved searches for a user"""
    try:
        user_id_str = safe_uuid_to_string(user_id)
        logger.debug(f"Getting saved searches for user: {user_id_str}")
        
        cursor = db.saved_searches.find({"user_id": user_id_str}).sort("created_at", -1)
        saved_searches = await cursor.to_list(length=None)
        
        # Ensure each search has the id field the frontend expects
        for search in saved_searches:
            if "_id" in search:
                search["id"] = str(search["_id"])
        
        logger.debug(f"Found {len(saved_searches)} saved searches for user: {user_id_str}")
        return saved_searches
        
    except Exception as e:
        logger.error(f"Error getting saved searches for user {user_id}: {e}")
        raise

async def get_saved_search_by_id(db, user_id: Union[UUID, str], search_id: Union[UUID, str]) -> Optional[dict]:
    """Get a specific saved search by ID"""
    try:
        user_id_str = safe_uuid_to_string(user_id)
        search_id_str = safe_uuid_to_string(search_id)
        logger.debug(f"Getting saved search {search_id_str} for user: {user_id_str}")
        
        saved_search = await db.saved_searches.find_one({
            "_id": search_id_str,
            "user_id": user_id_str
        })
        
        # Ensure the search has the id field the frontend expects
        if saved_search and "_id" in saved_search:
            saved_search["id"] = str(saved_search["_id"])
        
        if saved_search:
            logger.debug(f"Found saved search {search_id_str} for user: {user_id_str}")
        else:
            logger.debug(f"Saved search {search_id_str} not found for user: {user_id_str}")
            
        return saved_search
        
    except Exception as e:
        logger.error(f"Error getting saved search {search_id} for user {user_id}: {e}")
        raise

async def update_saved_search(db, user_id: Union[UUID, str], search_id: Union[UUID, str], update_data: dict) -> Optional[dict]:
    """Update a saved search"""
    try:
        user_id_str = safe_uuid_to_string(user_id)
        search_id_str = safe_uuid_to_string(search_id)
        logger.info(f"Updating saved search {search_id_str} for user: {user_id_str}")
        
        update_data["updated_at"] = datetime.utcnow()
        
        result = await db.saved_searches.update_one(
            {"_id": search_id_str, "user_id": user_id_str},
            {"$set": update_data}
        )
        
        if result.modified_count == 0:
            logger.warning(f"No saved search found to update: {search_id_str} for user: {user_id_str}")
            return None
        
        logger.info(f"Successfully updated saved search {search_id_str} for user: {user_id_str}")
        return await get_saved_search_by_id(db, user_id, search_id)
        
    except Exception as e:
        logger.error(f"Error updating saved search {search_id} for user {user_id}: {e}")
        raise

async def delete_saved_search(db, user_id: Union[UUID, str], search_id: Union[UUID, str]) -> bool:
    """Delete a saved search"""
    try:
        user_id_str = safe_uuid_to_string(user_id)
        search_id_str = safe_uuid_to_string(search_id)
        logger.info(f"Deleting saved search {search_id_str} for user: {user_id_str}")
        
        result = await db.saved_searches.delete_one({
            "_id": search_id_str,
            "user_id": user_id_str
        })
        
        success = result.deleted_count > 0
        if success:
            logger.info(f"Successfully deleted saved search {search_id_str} for user: {user_id_str}")
        else:
            logger.warning(f"No saved search found to delete: {search_id_str} for user: {user_id_str}")
            
        return success
        
    except Exception as e:
        logger.error(f"Error deleting saved search {search_id} for user {user_id}: {e}")
        raise