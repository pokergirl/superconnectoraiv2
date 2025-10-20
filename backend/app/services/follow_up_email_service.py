from fastapi import HTTPException, status
from datetime import datetime, timedelta
from typing import List, Optional
import asyncio
import logging
from uuid import UUID
from app.models.follow_up_email import (
    FollowUpEmailCreate,
    FollowUpEmailInDB,
    FollowUpStatus,
    FollowUpEmailUpdate
)
from app.models.warm_intro_request import WarmIntroStatus, WarmIntroRequest
from app.models.user import UserInDB
from app.core.db import get_database
from app.core.config import settings
import time
import random

logger = logging.getLogger(__name__)

async def schedule_follow_up_email(
    db, 
    warm_intro_request_id: str,
    requester_email: str,
    requester_name: str,
    connection_name: str,
    facilitator_email: str,
    follow_up_days: int = 14
) -> dict:
    """Schedule a follow-up email for a warm intro request"""
    
    # Calculate scheduled date
    scheduled_date = datetime.utcnow() + timedelta(days=follow_up_days)
    
    # Create follow-up email record
    follow_up_email = FollowUpEmailInDB(
        warm_intro_request_id=warm_intro_request_id,
        requester_email=requester_email,
        requester_name=requester_name,
        connection_name=connection_name,
        facilitator_email=facilitator_email,
        scheduled_date=scheduled_date,
        follow_up_days=follow_up_days
    )
    
    # Convert to dict for MongoDB
    follow_up_dict = follow_up_email.model_dump()
    follow_up_dict["id"] = str(follow_up_dict["id"])
    follow_up_dict["warm_intro_request_id"] = str(follow_up_dict["warm_intro_request_id"])
    
    await db.follow_up_emails.insert_one(follow_up_dict)
    
    logger.info(f"Scheduled follow-up email for warm intro {warm_intro_request_id} on {scheduled_date}")
    return follow_up_dict

async def get_pending_follow_ups(db) -> List[dict]:
    """Get all follow-up emails that are due to be sent"""
    current_time = datetime.utcnow()
    
    cursor = db.follow_up_emails.find({
        "status": FollowUpStatus.scheduled.value,
        "scheduled_date": {"$lte": current_time}
    })
    
    return await cursor.to_list(length=None)

async def send_follow_up_email(db, follow_up_id: str) -> bool:
    """Send a follow-up email and update its status"""
    try:
        # Get the follow-up email record
        follow_up = await db.follow_up_emails.find_one({"id": follow_up_id})
        if not follow_up:
            logger.error(f"Follow-up email {follow_up_id} not found")
            return False
        
        # Generate email content
        email_content = generate_follow_up_email_content(
            follow_up["requester_name"],
            follow_up["connection_name"],
            follow_up["facilitator_email"]
        )
        
        # Send the email using the configured email service
        success = await send_email_via_service(
            to_email=follow_up["requester_email"],
            subject=f"Follow-up: Connection with {follow_up['connection_name']}",
            content=email_content
        )
        
        if success:
            # Update status to sent
            update = FollowUpEmailUpdate(
                status=FollowUpStatus.sent,
                sent_at=datetime.utcnow()
            )
            
            await db.follow_up_emails.update_one(
                {"id": follow_up_id},
                {"$set": update.model_dump(exclude_unset=True)}
            )
            
            logger.info(f"Follow-up email {follow_up_id} sent successfully")
            return True
        else:
            # Update status to failed
            update = FollowUpEmailUpdate(
                status=FollowUpStatus.failed,
                error_message="Failed to send email"
            )
            
            await db.follow_up_emails.update_one(
                {"id": follow_up_id},
                {"$set": update.model_dump(exclude_unset=True)}
            )
            
            logger.error(f"Failed to send follow-up email {follow_up_id}")
            return False
            
    except Exception as e:
        logger.error(f"Error sending follow-up email {follow_up_id}: {str(e)}")
        
        # Update status to failed with error message
        update = FollowUpEmailUpdate(
            status=FollowUpStatus.failed,
            error_message=str(e)
        )
        
        await db.follow_up_emails.update_one(
            {"id": follow_up_id},
            {"$set": update.model_dump(exclude_unset=True)}
        )
        
        return False

def generate_follow_up_email_content(requester_name: str, connection_name: str, facilitator_name: str) -> str:
    """Generate the follow-up email content as specified in the PRD"""
    return f"""Hi {requester_name},

I wanted to check in on the warm intro I made for you with {connection_name} a couple of weeks ago. Were the two of you able to connect?

I'd love to hear how it went. Was it helpful, or not as useful as you hoped? Just hit reply to share your feedback. It really helps me understand the impact of these introductions and how to make SuperConnect AI even better.

SuperConnect is a labor of love, and it's sustained by the support of individuals like you. If you found this connection valuable, I'd be so grateful if you'd consider leaving a contribution to help keep it alive and keep the warm intros coming:
{settings.FRONTEND_URL}/donate

Thanks for being part of this journey, and for helping me build a tool that sparks meaningful connections.

Warmly,
Ha
"""

async def send_email_via_service(to_email: str, subject: str, content: str) -> bool:
    """Send an email using the configured email service (Gmail API or SMTP)"""
    try:
        from app.services.email_service import get_email_service
        
        email_service = get_email_service()
        
        # Send the email
        success = await email_service.send_email(
            to_email=to_email,
            subject=subject,
            body=content,
            html=True
        )
        
        if success:
            logger.info(f"Email sent successfully to {to_email}")
        else:
            logger.error(f"Failed to send email to {to_email}")
        
        return success
        
    except Exception as e:
        logger.error(f"Error sending email to {to_email}: {str(e)}")
        return False

async def process_pending_follow_ups():
    """Background task to process pending follow-up emails"""
    try:
        from app.core.db import get_database
        db = get_database()
        pending_follow_ups = await get_pending_follow_ups(db)
        
        logger.info(f"Processing {len(pending_follow_ups)} pending follow-up emails")
        
        for follow_up in pending_follow_ups:
            success = await send_follow_up_email(db, follow_up["id"])
            if success:
                logger.info(f"Successfully sent follow-up email {follow_up['id']}")
            else:
                logger.error(f"Failed to send follow-up email {follow_up['id']}")
                
        return len(pending_follow_ups)
        
    except Exception as e:
        logger.error(f"Error processing pending follow-ups: {str(e)}")
        return 0

async def cancel_follow_up_email(db, follow_up_id: str) -> bool:
    """Cancel a scheduled follow-up email"""
    try:
        update = FollowUpEmailUpdate(status=FollowUpStatus.cancelled)
        
        result = await db.follow_up_emails.update_one(
            {"id": follow_up_id, "status": FollowUpStatus.scheduled.value},
            {"$set": update.model_dump(exclude_unset=True)}
        )
        
        if result.matched_count > 0:
            logger.info(f"Cancelled follow-up email {follow_up_id}")
            return True
        else:
            logger.warning(f"Follow-up email {follow_up_id} not found or already processed")
            return False
            
    except Exception as e:
        logger.error(f"Error cancelling follow-up email {follow_up_id}: {str(e)}")
        return False

async def get_follow_ups_by_warm_intro(db, warm_intro_request_id: str) -> List[dict]:
    """Get all follow-up emails for a specific warm intro request"""
    cursor = db.follow_up_emails.find({"warm_intro_request_id": warm_intro_request_id})
    return await cursor.to_list(length=None)

async def get_follow_up_stats(db) -> dict:
    """Get statistics about follow-up emails"""
    pipeline = [
        {
            "$group": {
                "_id": "$status",
                "count": {"$sum": 1}
            }
        }
    ]
    
    cursor = db.follow_up_emails.aggregate(pipeline)
    stats = await cursor.to_list(length=None)
    
    # Convert to a more readable format
    stats_dict = {stat["_id"]: stat["count"] for stat in stats}
    
    return {
        "scheduled": stats_dict.get(FollowUpStatus.scheduled.value, 0),
        "sent": stats_dict.get(FollowUpStatus.sent.value, 0),
        "failed": stats_dict.get(FollowUpStatus.failed.value, 0),
        "cancelled": stats_dict.get(FollowUpStatus.cancelled.value, 0),
        "total": sum(stats_dict.values())
    }

# New functions for automated follow-up emails based on warm intro requests

async def get_eligible_warm_intro_requests(db) -> List[dict]:
    """Get warm intro requests that are eligible for follow-up emails (older than 14 days, no follow-up sent yet, not skipped)"""
    cutoff_date = datetime.utcnow() - timedelta(days=14)
    
    cursor = db.warm_intro_requests.find({
        "created_at": {"$lte": cutoff_date},
        "follow_up_sent_date": None,
        "follow_up_skipped": {"$ne": True},
        "status": WarmIntroStatus.pending.value
    })
    
    return await cursor.to_list(length=None)

async def prepare_manual_follow_up_email(db, warm_intro_request: dict) -> dict:
    """Prepare manual follow-up email data for a warm intro request"""
    try:
        # Handle both field naming conventions
        request_id = warm_intro_request.get("id") or warm_intro_request.get("_id")
        user_id = warm_intro_request.get("user_id") or warm_intro_request.get("requester_id")
        
        if not request_id:
            logger.error(f"No valid request ID found in warm intro request: {warm_intro_request}")
            return {"success": False, "error": "Invalid request ID"}
            
        if not user_id:
            logger.error(f"No valid user ID found in warm intro request {request_id}")
            return {"success": False, "error": "Invalid user ID"}
        
        # Get user email - handle both _id and id field naming
        user = await db.users.find_one({"$or": [{"_id": user_id}, {"id": user_id}]})
        if not user:
            logger.error(f"User not found for warm intro request {request_id}")
            return {"success": False, "error": "User not found"}
        
        user_email = user["email"]
        
        # Generate email content
        email_content = generate_automated_follow_up_content(
            warm_intro_request["requester_name"],
            warm_intro_request.get("connection_name") or warm_intro_request.get("target_name"),
            request_id
        )
        
        # Mark as follow-up prepared (but not sent automatically)
        update_query = {"$or": [{"_id": request_id}, {"id": request_id}]}
        await db.warm_intro_requests.update_one(
            update_query,
            {
                "$set": {
                    "follow_up_prepared_date": datetime.utcnow(),
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        logger.info(f"Manual follow-up email prepared for warm intro request {request_id}")
        
        return {
            "success": True,
            "request_id": request_id,
            "to_email": user_email,
            "subject": "Following up on your introduction request",
            "html_content": email_content,
            "requester_name": warm_intro_request["requester_name"],
            "connection_name": warm_intro_request.get("connection_name") or warm_intro_request.get("target_name")
        }
            
    except Exception as e:
        request_id = warm_intro_request.get("id") or warm_intro_request.get("_id", "unknown")
        logger.error(f"Error preparing manual follow-up email for warm intro request {request_id}: {str(e)}")
        return {"success": False, "error": str(e)}

def generate_automated_follow_up_content(requester_name: str, connection_name: str, request_id: str) -> str:
    """Generate the automated follow-up email content"""
    donate_link = f"{settings.FRONTEND_URL}/donate"
    
    return f"""
    <html>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
        <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
            <p>Hi {requester_name},</p>
            
            <p>I wanted to check in on the warm intro I made for you with <strong>{connection_name}</strong> a couple of weeks ago. Were the two of you able to connect?</p>
            
            <p>I'd love to hear how it went. Was it helpful, or not as useful as you hoped? Just hit reply to share your feedback. It really helps me understand the impact of these introductions and how to make SuperConnect AI even better.</p>
            
            <p>SuperConnect is a labor of love, and it's sustained by the support of individuals like you. If you found this connection valuable, I'd be so grateful if you'd consider leaving a contribution to help keep it alive and keep the warm intros coming:</p>
            
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

# SendGrid integration removed - now using manual email templates
# Email templates are generated and displayed to users for manual sending

async def process_manual_follow_ups() -> int:
    """Process all eligible warm intro requests for manual follow-up email preparation"""
    try:
        db = get_database()
        eligible_requests = await get_eligible_warm_intro_requests(db)
        
        logger.info(f"Processing {len(eligible_requests)} eligible warm intro requests for manual follow-up preparation")
        
        prepared_count = 0
        failed_count = 0
        
        # Process requests to prepare manual email templates
        for request in eligible_requests:
            try:
                result = await prepare_manual_follow_up_email(db, request)
                if result["success"]:
                    prepared_count += 1
                    logger.info(f"Successfully prepared follow-up email for request {request['id']}")
                else:
                    failed_count += 1
                    logger.warning(f"Failed to prepare follow-up email for request {request['id']}: {result.get('error', 'Unknown error')}")
                    
            except Exception as e:
                failed_count += 1
                logger.error(f"Error processing follow-up for request {request['id']}: {str(e)}")
        
        logger.info(f"Manual follow-up processing complete: {prepared_count} prepared, {failed_count} failed")
        return prepared_count
        
    except Exception as e:
        logger.error(f"Error processing manual follow-ups: {str(e)}")
        return 0
