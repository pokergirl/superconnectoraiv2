from fastapi import APIRouter, Depends, HTTPException, status
from app.services.auth_service import get_current_admin_user
from app.core.db import get_database
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

@router.get("/pending-counts")
async def get_pending_counts(
    current_admin: "UserPublic" = Depends(get_current_admin_user),
    db = Depends(get_database)
):
    """Get pending counts for current user's dashboard items"""
    try:
        from datetime import datetime
        from app.models.user import UserPublic
        
        # Get current user ID
        user_id = current_admin.id
        
        # Get pending warm intro requests count for all users (admin sees all requests)
        warm_intro_count = await db.warm_intro_requests.count_documents({
            "status": "pending"
        })
        
        # Get pending follow-up emails count (scheduled status AND due now)
        # Note: Follow-up emails don't have user_id, so we keep the global count
        current_time = datetime.utcnow()
        follow_up_count = await db.follow_up_emails.count_documents({
            "status": "scheduled",
            "scheduled_date": {"$lte": current_time}
        })
        
        # Get pending access requests count (global for admin)
        access_requests_count = await db.access_requests.count_documents({"status": "pending"})
        
        return {
            "warm_intro_requests": warm_intro_count,
            "follow_up_emails": follow_up_count,
            "access_requests": access_requests_count
        }
        
    except Exception as e:
        logger.error(f"Error getting pending counts: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get pending counts: {str(e)}"
        )