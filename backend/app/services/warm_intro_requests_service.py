from uuid import UUID
from typing import List, Optional, Dict
from datetime import datetime
import math
from app.models.warm_intro_request import WarmIntroRequest, WarmIntroStatus

async def create_warm_intro_request(
    db, 
    user_id: UUID, 
    requester_name: str, 
    connection_name: str, 
    status: WarmIntroStatus = WarmIntroStatus.pending
) -> WarmIntroRequest:
    """
    Create a new warm intro request.
    
    Args:
        db: Database connection
        user_id: ID of the user creating the request
        requester_name: Name of the person requesting the intro
        connection_name: Name of the person to be introduced to
        status: Initial status of the request
    
    Returns:
        WarmIntroRequest: The created warm intro request
    """
    warm_intro_request = WarmIntroRequest(
        user_id=user_id,
        requester_name=requester_name,
        connection_name=connection_name,
        status=status
    )
    
    # Convert the model to dict for MongoDB insertion
    document = warm_intro_request.model_dump()
    # Convert UUID objects to strings for MongoDB
    document["id"] = str(document["id"])
    document["user_id"] = str(document["user_id"])
    
    await db.warm_intro_requests.insert_one(document)
    return warm_intro_request

async def get_warm_intro_requests(
    db,
    user_id: UUID,
    page: int = 1,
    limit: int = 10,
    status_filter: Optional[WarmIntroStatus] = None
) -> Dict:
    """
    Get paginated warm intro requests for a user.
    
    Args:
        db: Database connection
        user_id: ID of the user
        page: Page number (1-based)
        limit: Number of items per page
        status_filter: Optional status filter
    
    Returns:
        Dict: Paginated results with items, total, page, limit, total_pages, and status_counts
    """
    # Build query
    query = {"user_id": str(user_id)}
    if status_filter:
        query["status"] = status_filter.value
    
    # Calculate skip
    skip = (page - 1) * limit
    
    # Get total count
    total = await db.warm_intro_requests.count_documents(query)
    
    # Get paginated results
    cursor = db.warm_intro_requests.find(query).sort("created_at", -1).skip(skip).limit(limit)
    requests = await cursor.to_list(length=limit)
    
    # Convert to WarmIntroRequest objects
    warm_intro_requests = [WarmIntroRequest(**request) for request in requests]
    
    # Calculate total pages
    total_pages = math.ceil(total / limit) if total > 0 else 1
    
    # Get status counts for all requests (not just filtered ones)
    status_counts = await get_warm_intro_request_counts(db, user_id)
    
    return {
        "items": warm_intro_requests,
        "total": total,
        "page": page,
        "limit": limit,
        "total_pages": total_pages,
        "status_counts": status_counts
    }

async def get_warm_intro_request_by_id(
    db, 
    request_id: UUID, 
    user_id: UUID
) -> Optional[WarmIntroRequest]:
    """
    Get a specific warm intro request by ID.
    
    Args:
        db: Database connection
        request_id: ID of the request
        user_id: ID of the user (for security)
    
    Returns:
        WarmIntroRequest or None: The request if found and belongs to user
    """
    request = await db.warm_intro_requests.find_one({
        "id": str(request_id), 
        "user_id": str(user_id)
    })
    
    if request:
        return WarmIntroRequest(**request)
    return None

async def update_warm_intro_request_status(
    db,
    request_id: UUID,
    status: WarmIntroStatus,
    user_id: UUID,
    connected_date: Optional[datetime] = None,
    declined_date: Optional[datetime] = None,
    outcome: Optional[str] = None,
    outcome_date: Optional[datetime] = None
) -> Optional[WarmIntroRequest]:
    """
    Update the status of a warm intro request.
    
    Args:
        db: Database connection
        request_id: ID of the request
        status: New status
        user_id: ID of the user (for security)
        connected_date: Date when connected (if status is connected)
        declined_date: Date when declined (if status is declined)
        outcome: Connection outcome (Connected, Not Connected, or None to clear)
        outcome_date: Date when outcome was set
    
    Returns:
        WarmIntroRequest or None: The updated request if successful
    """
    # Build update document
    update_doc = {
        "status": status.value,
        "updated_at": datetime.utcnow()
    }
    
    # Add outcome field if provided
    if outcome is not None:
        update_doc["outcome"] = outcome
        
    # Add outcome_date field if provided
    if outcome_date is not None:
        update_doc["outcome_date"] = outcome_date
    
    # Add date fields based on status
    if status == WarmIntroStatus.connected and connected_date:
        update_doc["connected_date"] = connected_date
        update_doc["declined_date"] = None  # Clear declined date
    elif status == WarmIntroStatus.declined and declined_date:
        update_doc["declined_date"] = declined_date
        update_doc["connected_date"] = None  # Clear connected date
    elif status == WarmIntroStatus.pending:
        # Clear both dates when resetting to pending
        update_doc["connected_date"] = None
        update_doc["declined_date"] = None
    
    # Update the request
    result = await db.warm_intro_requests.update_one(
        {"id": str(request_id), "user_id": str(user_id)},
        {"$set": update_doc}
    )
    
    if result.modified_count > 0:
        # Return the updated request
        return await get_warm_intro_request_by_id(db, request_id, user_id)
    
    return None

async def get_warm_intro_request_counts(
    db, 
    user_id: UUID
) -> Dict[str, int]:
    """
    Get count statistics for warm intro requests by status.
    
    Args:
        db: Database connection
        user_id: ID of the user
    
    Returns:
        Dict: Counts by status and total
    """
    # Get total count
    total = await db.warm_intro_requests.count_documents({"user_id": str(user_id)})
    
    # Get counts by status
    pipeline = [
        {"$match": {"user_id": str(user_id)}},
        {"$group": {"_id": "$status", "count": {"$sum": 1}}}
    ]
    
    status_counts = {}
    async for result in db.warm_intro_requests.aggregate(pipeline):
        status_counts[result["_id"]] = result["count"]
    
    return {
        "total": total,
        "pending": status_counts.get(WarmIntroStatus.pending.value, 0),
        "connected": status_counts.get(WarmIntroStatus.connected.value, 0),
        "declined": status_counts.get(WarmIntroStatus.declined.value, 0)
    }

async def delete_warm_intro_request(
    db, 
    request_id: UUID, 
    user_id: UUID
) -> bool:
    """
    Delete a warm intro request.
    
    Args:
        db: Database connection
        request_id: ID of the request
        user_id: ID of the user (for security)
    
    Returns:
        bool: True if deleted successfully
    """
    result = await db.warm_intro_requests.delete_one({
        "id": str(request_id), 
        "user_id": str(user_id)
    })
    
    return result.deleted_count > 0

async def search_warm_intro_requests(
    db, 
    user_id: UUID, 
    search_query: str, 
    page: int = 1, 
    limit: int = 10
) -> Dict:
    """
    Search warm intro requests by requester or connection name.
    
    Args:
        db: Database connection
        user_id: ID of the user
        search_query: Search term
        page: Page number (1-based)
        limit: Number of items per page
    
    Returns:
        Dict: Paginated search results
    """
    # Build search query
    query = {
        "user_id": str(user_id),
        "$or": [
            {"requester_name": {"$regex": search_query, "$options": "i"}},
            {"connection_name": {"$regex": search_query, "$options": "i"}}
        ]
    }
    
    # Calculate skip
    skip = (page - 1) * limit
    
    # Get total count
    total = await db.warm_intro_requests.count_documents(query)
    
    # Get paginated results
    cursor = db.warm_intro_requests.find(query).sort("created_at", -1).skip(skip).limit(limit)
    requests = await cursor.to_list(length=limit)
    
    # Convert to WarmIntroRequest objects
    warm_intro_requests = [WarmIntroRequest(**request) for request in requests]
    
    # Calculate total pages
    total_pages = math.ceil(total / limit) if total > 0 else 1
    
    return {
        "items": warm_intro_requests,
        "total": total,
        "page": page,
        "limit": limit,
        "total_pages": total_pages
    }