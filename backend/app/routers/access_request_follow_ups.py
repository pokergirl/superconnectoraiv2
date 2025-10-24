from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from typing import List, Optional
from datetime import datetime
import logging
from app.models.access_request_follow_up import (
    AccessRequestFollowUpCreate,
    AccessRequestFollowUpPublic,
    AccessRequestFollowUpUpdate,
    AccessRequestFollowUpStatus
)
from app.services.access_request_follow_up_service import (
    schedule_access_request_follow_up_email,
    get_pending_access_request_follow_ups,
    send_access_request_follow_up_email,
    cancel_access_request_follow_up_email,
    get_access_request_follow_ups_by_request,
    get_access_request_follow_up_stats,
    process_pending_access_request_follow_ups
)
from app.core.db import get_database
from app.services.auth_service import get_current_admin_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/admin/access-request-follow-ups", tags=["admin", "access-request-follow-ups"])

@router.post("/schedule", response_model=AccessRequestFollowUpPublic)
async def schedule_follow_up(
    follow_up_data: AccessRequestFollowUpCreate,
    current_user: dict = Depends(get_current_admin_user),
    db = Depends(get_database)
):
    """Schedule a follow-up email for an access request (admin only)"""
    try:
        follow_up_dict = await schedule_access_request_follow_up_email(
            db=db,
            access_request_id=str(follow_up_data.access_request_id),
            user_email=follow_up_data.user_email,
            user_name=follow_up_data.user_name,
            follow_up_days=follow_up_data.follow_up_days,
            scheduled_date=follow_up_data.scheduled_date
        )
        
        logger.info(f"Admin {current_user['email']} scheduled follow-up email for access request {follow_up_data.access_request_id}")
        
        return AccessRequestFollowUpPublic(**follow_up_dict)
        
    except Exception as e:
        logger.error(f"Error scheduling follow-up email: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to schedule follow-up email: {str(e)}"
        )

@router.get("/pending", response_model=List[AccessRequestFollowUpPublic])
async def get_pending_follow_ups(
    current_user: dict = Depends(get_current_admin_user),
    db = Depends(get_database)
):
    """Get all pending access request follow-up emails (admin only)"""
    try:
        pending_follow_ups = await get_pending_access_request_follow_ups(db)
        
        return [AccessRequestFollowUpPublic(**follow_up) for follow_up in pending_follow_ups]
        
    except Exception as e:
        logger.error(f"Error getting pending follow-ups: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get pending follow-ups: {str(e)}"
        )

@router.post("/{follow_up_id}/send")
async def send_follow_up_email(
    follow_up_id: str,
    current_user: dict = Depends(get_current_admin_user),
    db = Depends(get_database)
):
    """Manually send a follow-up email (admin only)"""
    try:
        success = await send_access_request_follow_up_email(db, follow_up_id)
        
        if success:
            logger.info(f"Admin {current_user['email']} manually sent follow-up email {follow_up_id}")
            return {"success": True, "message": "Follow-up email sent successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send follow-up email"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sending follow-up email {follow_up_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send follow-up email: {str(e)}"
        )

@router.post("/{follow_up_id}/cancel")
async def cancel_follow_up_email(
    follow_up_id: str,
    current_user: dict = Depends(get_current_admin_user),
    db = Depends(get_database)
):
    """Cancel a scheduled follow-up email (admin only)"""
    try:
        success = await cancel_access_request_follow_up_email(db, follow_up_id)
        
        if success:
            logger.info(f"Admin {current_user['email']} cancelled follow-up email {follow_up_id}")
            return {"success": True, "message": "Follow-up email cancelled successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Follow-up email not found or already processed"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling follow-up email {follow_up_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cancel follow-up email: {str(e)}"
        )

@router.get("/access-request/{access_request_id}", response_model=List[AccessRequestFollowUpPublic])
async def get_follow_ups_by_access_request(
    access_request_id: str,
    current_user: dict = Depends(get_current_admin_user),
    db = Depends(get_database)
):
    """Get all follow-up emails for a specific access request (admin only)"""
    try:
        follow_ups = await get_access_request_follow_ups_by_request(db, access_request_id)
        
        return [AccessRequestFollowUpPublic(**follow_up) for follow_up in follow_ups]
        
    except Exception as e:
        logger.error(f"Error getting follow-ups for access request {access_request_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get follow-ups: {str(e)}"
        )

@router.get("/stats")
async def get_follow_up_stats(
    current_user: dict = Depends(get_current_admin_user),
    db = Depends(get_database)
):
    """Get statistics about access request follow-up emails (admin only)"""
    try:
        stats = await get_access_request_follow_up_stats(db)
        
        return {
            "success": True,
            "stats": stats,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting follow-up stats: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get stats: {str(e)}"
        )

@router.post("/process-pending")
async def process_pending_follow_up_emails(
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_admin_user)
):
    """Manually trigger processing of pending access request follow-up emails (admin only)"""
    try:
        logger.info(f"Admin {current_user['email']} triggered manual processing of pending access request follow-up emails")
        
        # Process in background
        background_tasks.add_task(process_pending_access_request_follow_ups)
        
        return {
            "success": True,
            "message": "Processing of pending access request follow-up emails started",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error triggering manual processing: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to trigger processing: {str(e)}"
        )
