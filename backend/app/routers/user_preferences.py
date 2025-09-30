from fastapi import APIRouter, Depends, HTTPException
from app.services.auth_service import get_current_user
from app.core.db import get_database
from pydantic import BaseModel

router = APIRouter()

class UserPreferences(BaseModel):
    persist_search_results: bool

@router.put("/preferences", response_model=UserPreferences)
async def update_user_preferences(
    preferences: UserPreferences,
    db=Depends(get_database),
    current_user: dict = Depends(get_current_user),
):
    """
    Update user preferences.
    """
    user_id = current_user["id"]
    
    await db.users.update_one(
        {"_id": user_id},
        {"$set": {"persist_search_results": preferences.persist_search_results}},
    )
    
    return preferences