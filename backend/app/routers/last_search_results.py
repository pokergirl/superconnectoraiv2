from fastapi import APIRouter, Depends, HTTPException, status
from typing import Optional
from uuid import UUID

from app.services.auth_service import get_current_user
from app.services import last_search_results_service
from app.models.last_search_results import LastSearchResultsCreate
from app.core.db import get_database

router = APIRouter()

@router.get("/last-search-results")
async def get_last_search_results(
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database)
):
    """Get user's last search results"""
    try:
        user_id = current_user.id
        last_search = await last_search_results_service.get_last_search_results(db, user_id)
        
        if not last_search:
            return {"has_results": False, "data": None}
        
        return {"has_results": True, "data": last_search}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get last search results: {str(e)}"
        )

@router.post("/last-search-results", status_code=status.HTTP_201_CREATED)
async def save_last_search_results(
    search_data: LastSearchResultsCreate,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database)
):
    """Save user's last search results"""
    try:
        user_id = current_user.id
        saved_search = await last_search_results_service.save_last_search_results(db, user_id, search_data)
        return saved_search
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save last search results: {str(e)}"
        )

@router.delete("/last-search-results", status_code=status.HTTP_204_NO_CONTENT)
async def clear_last_search_results(
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database)
):
    """Clear user's last search results"""
    try:
        user_id = current_user.id
        deleted = await last_search_results_service.clear_last_search_results(db, user_id)
        
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No last search results found to clear"
            )
        
        return
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to clear last search results: {str(e)}"
        )

@router.get("/last-search-results/exists")
async def check_last_search_results_exist(
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database)
):
    """Check if user has last search results"""
    try:
        user_id = current_user.id
        has_results = await last_search_results_service.has_last_search_results(db, user_id)
        return {"has_results": has_results}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check last search results: {str(e)}"
        )