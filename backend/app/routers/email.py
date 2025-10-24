from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from typing import Optional
import logging

from app.services.auth_service import get_current_admin_user
from app.services.email_service import get_email_service
from app.services.email_template_service import EmailTemplateService
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

class PopulatedEmailTemplateRequest(BaseModel):
    warm_intro_request_id: str

class PopulatedEmailTemplateResponse(BaseModel):
    success: bool
    template: str
    subject: str
    message: Optional[str] = None

@router.post("/populate-template", response_model=PopulatedEmailTemplateResponse)
async def populate_email_template(
    request: PopulatedEmailTemplateRequest,
    current_user = Depends(get_current_admin_user),
    db = Depends(get_database)
):
    """
    Get a populated email template for a warm intro request.
    
    This endpoint is only available to admin users.
    """
    try:
        logger.info(f"🚀 Starting email template population for request ID: {request.warm_intro_request_id}")
        
        # Get the warm intro request
        warm_intro_request = await db.warm_intro_requests.find_one({"id": request.warm_intro_request_id})
        if not warm_intro_request:
            logger.error(f"❌ Warm intro request not found: {request.warm_intro_request_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Warm intro request not found"
            )
        
        logger.info(f"✅ Found warm intro request: {warm_intro_request}")
        
        # Get user email from the warm intro request
        user_id = warm_intro_request.get("user_id")
        if not user_id:
            logger.error(f"❌ User ID not found in warm intro request")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User ID not found in warm intro request"
            )
        
        logger.info(f"👤 User ID from warm intro request: {user_id}")
        
        # Get user email from users collection
        user = await db.users.find_one({"$or": [{"_id": user_id}, {"id": user_id}]})
        if not user:
            logger.error(f"❌ User not found for ID: {user_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        user_email = user.get("email")
        if not user_email:
            logger.error(f"❌ User email not found for user: {user}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User email not found"
            )
        
        logger.info(f"📧 User email found: {user_email}")
        
        # Get the default template
        template = EmailTemplateService.get_default_template()
        logger.info(f"📄 Using default template")
        
        # Populate the template with actual data, including user info from access_requests
        logger.info(f"🔄 Calling replace_placeholders_with_user_info...")
        populated_template = await EmailTemplateService.replace_placeholders_with_user_info(
            template=template,
            connection_name=warm_intro_request.get("connection_name", ""),
            requester_name=warm_intro_request.get("requester_name", ""),
            reason=warm_intro_request.get("reason"),
            about=warm_intro_request.get("about"),
            requester_linkedin_url=warm_intro_request.get("requester_linkedin_url"),
            db=db,
            user_email=user_email
        )
        
        logger.info(f"✅ Template populated successfully")
        
        # Generate subject
        subject = f"Warm Introduction Request - {warm_intro_request.get('connection_name', '')}"
        
        return PopulatedEmailTemplateResponse(
            success=True,
            template=populated_template,
            subject=subject,
            message="Template populated successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error populating email template: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to populate template: {str(e)}"
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
