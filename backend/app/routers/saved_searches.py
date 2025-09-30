from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List
from uuid import UUID
from pydantic import BaseModel

from app.services.auth_service import get_current_user
from app.services import saved_searches_service
from app.services.retrieval_service import retrieval_service
from app.models.saved_search import SavedSearchCreate, SavedSearchPublic
from app.core.db import get_database

router = APIRouter()

class SavedSearchUpdate(BaseModel):
    name: str = None
    query: str = None
    filters: dict = None

@router.post("/saved-searches", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_saved_search(
    saved_search_data: SavedSearchCreate,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database)
):
    """Create a new saved search"""
    try:
        user_id = current_user.id
        saved_search = await saved_searches_service.create_saved_search(db, user_id, saved_search_data)
        return saved_search
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create saved search: {str(e)}"
        )

@router.get("/saved-searches", response_model=List[dict])
async def get_saved_searches(
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database)
):
    """Get all saved searches for the current user"""
    try:
        user_id = current_user.id
        saved_searches = await saved_searches_service.get_user_saved_searches(db, user_id)
        return saved_searches
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get saved searches: {str(e)}"
        )

@router.get("/saved-searches/{search_id}", response_model=dict)
async def get_saved_search(
    search_id: UUID,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database)
):
    """Get a specific saved search by ID"""
    try:
        user_id = current_user.id
        saved_search = await saved_searches_service.get_saved_search_by_id(db, user_id, search_id)
        
        if not saved_search:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Saved search not found"
            )
        
        return saved_search
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get saved search: {str(e)}"
        )

@router.put("/saved-searches/{search_id}", response_model=dict)
async def update_saved_search(
    search_id: UUID,
    update_data: SavedSearchUpdate,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database)
):
    """Update a saved search"""
    try:
        user_id = current_user.id
        
        # Only include non-None fields in the update
        update_dict = {k: v for k, v in update_data.model_dump().items() if v is not None}
        
        if not update_dict:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No fields to update"
            )
        
        saved_search = await saved_searches_service.update_saved_search(db, user_id, search_id, update_dict)
        
        if not saved_search:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Saved search not found"
            )
        
        return saved_search
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update saved search: {str(e)}"
        )

@router.delete("/saved-searches/{search_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_saved_search(
    search_id: UUID,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database)
):
    """Delete a saved search"""
    try:
        user_id = current_user.id
        deleted = await saved_searches_service.delete_saved_search(db, user_id, search_id)
        
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Saved search not found"
            )
        
        return
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete saved search: {str(e)}"
        )

@router.post("/saved-searches/{search_id}/run")
async def run_saved_search(
    search_id: UUID,
    page: int = Query(1, ge=1, description="Page number for pagination"),
    page_size: int = Query(20, ge=1, le=100, description="Number of results per page"),
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database)
):
    """
    Execute a saved search using the new retrieval service
    """
    try:
        user_id = current_user.id
        
        # Get the saved search
        saved_search = await saved_searches_service.get_saved_search_by_id(db, user_id, search_id)
        
        if not saved_search:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Saved search not found"
            )
        
        # Extract query and filters from saved search
        query = saved_search.get("query", "")
        filters = saved_search.get("filters", {})
        
        if not query.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Saved search has empty query"
            )
        
        # Convert filters to the format expected by the retrieval service
        filter_dict = None
        if filters:
            # Convert saved filters to SearchFilters format first
            from app.routers.search import SearchFilters, convert_search_filters_to_pinecone_filter
            
            try:
                search_filters = SearchFilters(**filters)
                filter_dict = convert_search_filters_to_pinecone_filter(search_filters)
            except Exception as filter_error:
                print(f"Error converting saved search filters: {filter_error}")
                # Continue without filters if conversion fails
                filter_dict = None
        
        # Use the new retrieval service for search and re-ranking
        reranked_results = await retrieval_service.retrieve_and_rerank(
            user_query=query,
            user_id=str(user_id),
            enable_query_rewrite=True,
            filter_dict=filter_dict
        )
        
        # Apply pagination
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_results = reranked_results[start_idx:end_idx]
        
        # Convert to the expected SearchResult format
        search_results = []
        for result in paginated_results:
            search_results.append({
                "connection": result["profile"],
                "score": result["score"],
                "summary": result["pro"],  # Use pro as summary
                "pros": [result["pro"]],
                "cons": [result["con"]]
            })
        
        return {
            "saved_search": saved_search,
            "results": search_results,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total_results": len(reranked_results),
                "total_pages": (len(reranked_results) + page_size - 1) // page_size
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error running saved search: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to run saved search: {str(e)}"
        )