from uuid import UUID
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
import logging
import asyncio
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError, NetworkTimeout
from app.models.last_search_results import LastSearchResultsInDB, LastSearchResultsCreate

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

async def retry_db_operation(operation, max_retries: int = 3, delay: float = 1.0):
    """
    Retry database operations with exponential backoff for connection issues.
    
    Args:
        operation: Async function to retry
        max_retries: Maximum number of retry attempts
        delay: Initial delay between retries (seconds)
        
    Returns:
        Result of the operation
        
    Raises:
        Exception: The last exception if all retries fail
    """
    last_exception = None
    
    for attempt in range(max_retries + 1):
        try:
            return await operation()
        except (ConnectionFailure, ServerSelectionTimeoutError, NetworkTimeout, OSError) as e:
            last_exception = e
            if attempt < max_retries:
                wait_time = delay * (2 ** attempt)  # Exponential backoff
                logger.warning(f"Database connection failed (attempt {attempt + 1}/{max_retries + 1}): {e}. Retrying in {wait_time}s...")
                await asyncio.sleep(wait_time)
            else:
                logger.error(f"Database operation failed after {max_retries + 1} attempts: {e}")
                raise
        except Exception as e:
            # For non-connection errors, don't retry
            logger.error(f"Database operation failed with non-retryable error: {e}")
            raise
    
    # This should never be reached, but just in case
    if last_exception:
        raise last_exception

async def save_last_search_results(
    db,
    user_id: Union[UUID, str],
    search_data: LastSearchResultsCreate
) -> dict:
    """Save or update the user's last search results with retry logic"""
    
    async def _save_operation():
        user_id_str = safe_uuid_to_string(user_id)
        logger.info(f"Saving last search results for user: {user_id_str}")
        
        # First, check if user already has last search results
        existing_result = await db.last_search_results.find_one({"user_id": user_id_str})
        
        if existing_result:
            # Update existing record
            update_data = search_data.model_dump()
            update_data["updated_at"] = datetime.utcnow()
            
            result = await db.last_search_results.update_one(
                {"user_id": user_id_str},
                {"$set": update_data}
            )
            
            if result.modified_count > 0:
                # Return updated document
                updated_doc = await db.last_search_results.find_one({"user_id": user_id_str})
                if updated_doc and "_id" in updated_doc:
                    updated_doc["_id"] = str(updated_doc["_id"])
                logger.info(f"Successfully updated last search results for user: {user_id_str}")
                return updated_doc
            else:
                logger.warning(f"No changes made to last search results for user: {user_id_str}")
                return existing_result
        else:
            # Create new record
            search_entry = LastSearchResultsInDB(
                **search_data.model_dump(),
                user_id=user_id_str
            )
            
            # Convert to dict for MongoDB storage
            search_dict = search_entry.model_dump(by_alias=True)
            # Handle the _id field properly - it may already be set by the alias
            if "id" in search_dict:
                search_dict["_id"] = str(search_dict.pop("id"))
            elif "_id" in search_dict:
                search_dict["_id"] = str(search_dict["_id"])
            search_dict["user_id"] = user_id_str
            
            result = await db.last_search_results.insert_one(search_dict)
            search_dict["_id"] = result.inserted_id
            
            logger.info(f"Successfully created new last search results for user: {user_id_str}")
            return search_dict
    
    try:
        return await retry_db_operation(_save_operation)
    except Exception as e:
        logger.error(f"Failed to save last search results for user {user_id}: {e}")
        raise

async def get_last_search_results(db, user_id: Union[UUID, str]) -> Optional[dict]:
    """Get user's last search results with retry logic"""
    
    async def _get_operation():
        user_id_str = safe_uuid_to_string(user_id)
        logger.debug(f"Getting last search results for user: {user_id_str}")
        
        result = await db.last_search_results.find_one({"user_id": user_id_str})
        
        if result:
            # Convert ObjectId to string for serialization
            if "_id" in result:
                result["_id"] = str(result["_id"])
            logger.debug(f"Found last search results for user: {user_id_str}")
        else:
            logger.debug(f"No last search results found for user: {user_id_str}")
        
        return result
    
    try:
        return await retry_db_operation(_get_operation)
    except Exception as e:
        logger.error(f"Failed to get last search results for user {user_id}: {e}")
        raise

async def clear_last_search_results(db, user_id: Union[UUID, str]) -> bool:
    """Clear user's last search results with retry logic"""
    
    async def _clear_operation():
        user_id_str = safe_uuid_to_string(user_id)
        logger.info(f"Clearing last search results for user: {user_id_str}")
        
        result = await db.last_search_results.delete_one({"user_id": user_id_str})
        success = result.deleted_count > 0
        
        if success:
            logger.info(f"Successfully cleared last search results for user: {user_id_str}")
        else:
            logger.warning(f"No last search results found to clear for user: {user_id_str}")
            
        return success
    
    try:
        return await retry_db_operation(_clear_operation)
    except Exception as e:
        logger.error(f"Failed to clear last search results for user {user_id}: {e}")
        raise

async def has_last_search_results(db, user_id: Union[UUID, str]) -> bool:
    """Check if user has last search results with retry logic"""
    
    async def _check_operation():
        user_id_str = safe_uuid_to_string(user_id)
        logger.debug(f"Checking if user has last search results: {user_id_str}")
        
        count = await db.last_search_results.count_documents({"user_id": user_id_str})
        has_results = count > 0
        
        logger.debug(f"User {user_id_str} has last search results: {has_results}")
        return has_results
    
    try:
        return await retry_db_operation(_check_operation)
    except Exception as e:
        logger.error(f"Failed to check last search results for user {user_id}: {e}")
        raise