from fastapi import HTTPException, status
from datetime import datetime, timedelta
from typing import List, Optional
import logging
from uuid import UUID
from app.models.access_request_follow_up import (
    AccessRequestFollowUpCreate,
    AccessRequestFollowUpInDB,
    AccessRequestFollowUpStatus,
    AccessRequestFollowUpUpdate
)
from app.core.db import get_database
from app.core.config import settings

logger = logging.getLogger(__name__)

async def schedule_access_request_follow_up_email(
    db, 
    access_request_id: str,
    user_email: str,
    user_name: str,
    follow_up_days: int = 14,
    scheduled_date: Optional[datetime] = None
) -> dict:
    """Schedule a follow-up email for an approved access request"""
    
    # Calculate scheduled date if not provided
    if scheduled_date is None:
        scheduled_date = datetime.utcnow() + timedelta(days=follow_up_days)
    
    # Create follow-up email record
    follow_up_email = AccessRequestFollowUpInDB(
        access_request_id=UUID(access_request_id),
        user_email=user_email,
        user_name=user_name,
        scheduled_date=scheduled_date,
        follow_up_days=follow_up_days
    )
    
    # Convert to dict for MongoDB
    follow_up_dict = follow_up_email.model_dump()
    follow_up_dict["id"] = str(follow_up_dict["id"])
    follow_up_dict["access_request_id"] = str(follow_up_dict["access_request_id"])
    
    await db.access_request_follow_ups.insert_one(follow_up_dict)
    
    logger.info(f"Scheduled follow-up email for access request {access_request_id} on {scheduled_date}")
    return follow_up_dict

async def get_pending_access_request_follow_ups(db) -> List[dict]:
    """Get all access request follow-up emails that are due to be sent"""
    current_time = datetime.utcnow()
    
    cursor = db.access_request_follow_ups.find({
        "status": AccessRequestFollowUpStatus.scheduled.value,
        "scheduled_date": {"$lte": current_time}
    })
    
    return await cursor.to_list(length=None)

async def send_access_request_follow_up_email(db, follow_up_id: str) -> bool:
    """Send a follow-up email and update its status"""
    try:
        # Get the follow-up email record
        follow_up = await db.access_request_follow_ups.find_one({"id": follow_up_id})
        if not follow_up:
            logger.error(f"Access request follow-up email {follow_up_id} not found")
            return False
        
        # Generate email content
        email_content = generate_access_request_follow_up_content(
            follow_up["user_name"]
        )
        
        # Define CC emails for follow-up emails
        cc_emails = ["ha@nextstepfwd.com", "hassan.rasool@snapdev.ai"]
        
        # Send the email using the configured email service
        success = await send_email_via_service(
            to_email=follow_up["user_email"],
            subject="How's your SuperConnect AI experience going?",
            content=email_content,
            cc_emails=cc_emails
        )
        
        if success:
            # Update status to sent
            update = AccessRequestFollowUpUpdate(
                status=AccessRequestFollowUpStatus.sent,
                sent_at=datetime.utcnow()
            )
            
            await db.access_request_follow_ups.update_one(
                {"id": follow_up_id},
                {"$set": update.model_dump(exclude_unset=True)}
            )
            
            logger.info(f"Access request follow-up email {follow_up_id} sent successfully")
            return True
        else:
            # Update status to failed
            update = AccessRequestFollowUpUpdate(
                status=AccessRequestFollowUpStatus.failed,
                error_message="Failed to send email"
            )
            
            await db.access_request_follow_ups.update_one(
                {"id": follow_up_id},
                {"$set": update.model_dump(exclude_unset=True)}
            )
            
            logger.error(f"Failed to send access request follow-up email {follow_up_id}")
            return False
            
    except Exception as e:
        logger.error(f"Error sending access request follow-up email {follow_up_id}: {str(e)}")
        
        # Update status to failed with error message
        update = AccessRequestFollowUpUpdate(
            status=AccessRequestFollowUpStatus.failed,
            error_message=str(e)
        )
        
        await db.access_request_follow_ups.update_one(
            {"id": follow_up_id},
            {"$set": update.model_dump(exclude_unset=True)}
        )
        
        return False

def generate_access_request_follow_up_content(user_name: str) -> str:
    """Generate the follow-up email content for access request approvals"""
    donate_link = f"{settings.FRONTEND_URL}/donate"
    
    return f"""
    <html>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
        <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
            <p>Hi {user_name},</p>
            
            <p>It's been about 2 weeks since you joined SuperConnect AI, and I wanted to check in on how your experience has been going!</p>
            
            <p>Have you had a chance to explore the platform and connect with some interesting people? I'd love to hear about your experience - whether it's been helpful, challenging, or anything in between. Your feedback really helps me understand how to make SuperConnect AI even better.</p>
            
            <p>If you've made any meaningful connections or found value in the platform, I'd be so grateful if you'd consider leaving a contribution to help keep SuperConnect AI alive and growing:</p>
            
            <div style="text-align: center; margin: 20px 0;">
                <a href="{donate_link}" style="background-color: #3498db; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; display: inline-block;">Make a Contribution</a>
            </div>
            
            <p>Thanks for being part of this journey, and for helping me build a tool that sparks meaningful connections.</p>
            
            <p>Warmly,<br>
            Ha</p>
        </div>
    </body>
    </html>
    """

async def send_email_via_service(to_email: str, subject: str, content: str, cc_emails: Optional[List[str]] = None) -> bool:
    """Send an email using the configured email service (Gmail API or SMTP)"""
    try:
        from app.services.email_service import get_email_service
        
        email_service = get_email_service()
        
        # Send the email
        success = await email_service.send_email(
            to_email=to_email,
            subject=subject,
            body=content,
            html=True,
            cc_emails=cc_emails
        )
        
        if success:
            logger.info(f"Email sent successfully to {to_email}")
            if cc_emails:
                logger.info(f"CC'd to: {', '.join(cc_emails)}")
        else:
            logger.error(f"Failed to send email to {to_email}")
        
        return success
        
    except Exception as e:
        logger.error(f"Error sending email to {to_email}: {str(e)}")
        return False

async def process_pending_access_request_follow_ups():
    """Background task to process pending access request follow-up emails"""
    try:
        from app.core.db import get_database
        db = get_database()
        pending_follow_ups = await get_pending_access_request_follow_ups(db)
        
        logger.info(f"Processing {len(pending_follow_ups)} pending access request follow-up emails")
        
        for follow_up in pending_follow_ups:
            success = await send_access_request_follow_up_email(db, follow_up["id"])
            if success:
                logger.info(f"Successfully sent access request follow-up email {follow_up['id']}")
            else:
                logger.error(f"Failed to send access request follow-up email {follow_up['id']}")
                
        return len(pending_follow_ups)
        
    except Exception as e:
        logger.error(f"Error processing pending access request follow-ups: {str(e)}")
        return 0

async def cancel_access_request_follow_up_email(db, follow_up_id: str) -> bool:
    """Cancel a scheduled access request follow-up email"""
    try:
        update = AccessRequestFollowUpUpdate(status=AccessRequestFollowUpStatus.cancelled)
        
        result = await db.access_request_follow_ups.update_one(
            {"id": follow_up_id, "status": AccessRequestFollowUpStatus.scheduled.value},
            {"$set": update.model_dump(exclude_unset=True)}
        )
        
        if result.matched_count > 0:
            logger.info(f"Cancelled access request follow-up email {follow_up_id}")
            return True
        else:
            logger.warning(f"Access request follow-up email {follow_up_id} not found or already processed")
            return False
            
    except Exception as e:
        logger.error(f"Error cancelling access request follow-up email {follow_up_id}: {str(e)}")
        return False

async def get_access_request_follow_ups_by_request(db, access_request_id: str) -> List[dict]:
    """Get all follow-up emails for a specific access request"""
    cursor = db.access_request_follow_ups.find({"access_request_id": access_request_id})
    return await cursor.to_list(length=None)

async def get_access_request_follow_up_stats(db) -> dict:
    """Get statistics about access request follow-up emails"""
    pipeline = [
        {
            "$group": {
                "_id": "$status",
                "count": {"$sum": 1}
            }
        }
    ]
    
    cursor = db.access_request_follow_ups.aggregate(pipeline)
    stats = await cursor.to_list(length=None)
    
    # Convert to a more readable format
    stats_dict = {stat["_id"]: stat["count"] for stat in stats}
    
    return {
        "scheduled": stats_dict.get(AccessRequestFollowUpStatus.scheduled.value, 0),
        "sent": stats_dict.get(AccessRequestFollowUpStatus.sent.value, 0),
        "failed": stats_dict.get(AccessRequestFollowUpStatus.failed.value, 0),
        "cancelled": stats_dict.get(AccessRequestFollowUpStatus.cancelled.value, 0),
        "total": sum(stats_dict.values())
    }
