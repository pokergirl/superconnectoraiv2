from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from typing import Optional
import logging

from app.services.auth_service import get_current_admin_user
from app.services.email_service import get_email_service
from app.core.db import get_database

logger = logging.getLogger(__name__)

router = APIRouter()

class SendEmailRequest(BaseModel):
    to_email: EmailStr
    subject: str
    body: str
    warm_intro_request_id: Optional[str] = None

class SendEmailResponse(BaseModel):
    success: bool
    message: str
    email_id: Optional[str] = None

@router.post("/send-email", response_model=SendEmailResponse)
async def send_email(
    request: SendEmailRequest,
    current_user = Depends(get_current_admin_user),
    db = Depends(get_database)
):
    """
    Send an email using the configured email service (Gmail API or SMTP).
    
    This endpoint is only available to admin users.
    """
    try:
        # Get the email service
        email_service = get_email_service()
        
        # Send the email
        success = await email_service.send_email(
            to_email=request.to_email,
            subject=request.subject,
            body=request.body,
            html=True
        )
        
        if success:
            logger.info(f"Email sent successfully to {request.to_email} by admin {current_user.email}")
            
            # If this is related to a warm intro request, we could log it
            if request.warm_intro_request_id:
                logger.info(f"Email sent for warm intro request {request.warm_intro_request_id}")
            
            return SendEmailResponse(
                success=True,
                message=f"Email sent successfully to {request.to_email}",
                email_id=None  # Gmail API doesn't return email ID in our current implementation
            )
        else:
            logger.error(f"Failed to send email to {request.to_email}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send email"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sending email to {request.to_email}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send email: {str(e)}"
        )

@router.get("/email-status")
async def get_email_status(
    current_user = Depends(get_current_admin_user)
):
    """
    Get the status of the email service configuration.
    
    This endpoint is only available to admin users.
    """
    try:
        email_service = get_email_service()
        
        # Check if Gmail service is available
        is_gmail_available = hasattr(email_service, 'is_available') and email_service.is_available()
        
        return {
            "email_service_type": "gmail_api" if is_gmail_available else "smtp",
            "is_available": True,
            "service_name": email_service.__class__.__name__
        }
        
    except Exception as e:
        logger.error(f"Error checking email status: {str(e)}")
        return {
            "email_service_type": "unknown",
            "is_available": False,
            "error": str(e)
        }
