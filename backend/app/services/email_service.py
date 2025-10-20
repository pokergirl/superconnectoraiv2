import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
from app.core.config import settings

logger = logging.getLogger(__name__)

class EmailService:
    """Service for sending emails using smtplib with proper SSL/TLS handling (fallback when Gmail API is not available)"""
    
    def __init__(self):
        """Initialize email service"""
        if settings.SMTP_USER and settings.SMTP_PASSWORD:
            logger.info(f"SMTP email service initialized with {settings.SMTP_HOST}:{settings.SMTP_PORT}")
        else:
            logger.warning("SMTP credentials not configured. Email sending will be simulated.")
    
    async def send_email(
        self,
        to_email: str,
        subject: str,
        body: str,
        html: bool = True
    ) -> bool:
        """
        Send an email using smtplib with proper SSL/TLS handling
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            body: Email body (HTML or plain text)
            html: Whether the body is HTML (default: True)
        
        Returns:
            bool: True if email sent successfully, False otherwise
        """
        try:
            if not settings.SMTP_USER or not settings.SMTP_PASSWORD:
                # Simulate email sending if SMTP not configured
                logger.info(f"SIMULATED EMAIL SENT:")
                logger.info(f"To: {to_email}")
                logger.info(f"Subject: {subject}")
                logger.info(f"Body: {body[:100]}...")
                return True
            
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f"{settings.FROM_NAME} <{settings.FROM_EMAIL}>"
            msg['To'] = to_email
            
            # Attach body
            if html:
                msg.attach(MIMEText(body, 'html'))
            else:
                msg.attach(MIMEText(body, 'plain'))
            
            # Send email using smtplib with proper SSL/TLS
            try:
                if settings.SMTP_PORT == 465:
                    # Port 465 uses SSL
                    server = smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT)
                else:
                    # Port 587 uses STARTTLS
                    server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT)
                    server.starttls()
                
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                server.send_message(msg)
                server.quit()
                
                logger.info(f"Email sent successfully to {to_email}")
                return True
                
            except smtplib.SMTPException as e:
                logger.error(f"SMTP error sending email to {to_email}: {str(e)}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {str(e)}")
            return False
    
    async def send_approval_email(
        self,
        to_email: str,
        recipient_name: str,
        temp_password: str
    ) -> bool:
        """
        Send access approval email with temporary password
        
        Args:
            to_email: Recipient email address
            recipient_name: Recipient's full name
            temp_password: Temporary password for login
        
        Returns:
            bool: True if email sent successfully, False otherwise
        """
        subject = "Your access request has been approved!"
        
        app_url = settings.FRONTEND_URL or "https://superconnector.ai"
        login_url = f"{app_url}/login"
        
        body = f"""Hi {recipient_name},

Your access to SuperConnect.ai has been approved, and I'm so glad to have you here!

Here's your temporary passcode to log in: {temp_password}
(You'll be prompted to create a new password once you're in.)

Log in here: {login_url}
Or visit: {app_url}

SuperConnect.ai is a passion project we built to help leaders like you spark meaningful connections. To keep it alive, it depends on your support. If you find the connections valuable, there's an option to leave a tip. Every contribution helps sustain and grow this community-driven effort.

I'd also love your feedback as you dive in. Your thoughts will help shape SuperConnect and make it even better.

Excited for you to explore, and grateful to have you on this journey.

Warmly,
Ha & the SuperConnect.ai team"""
        
        return await self.send_email(to_email, subject, body, html=False)
    
    async def send_rejection_email(
        self,
        to_email: str,
        recipient_name: str,
        admin_notes: Optional[str] = None
    ) -> bool:
        """
        Send access rejection email
        
        Args:
            to_email: Recipient email address
            recipient_name: Recipient's full name
            admin_notes: Optional admin notes for rejection reason
        
        Returns:
            bool: True if email sent successfully, False otherwise
        """
        subject = "Update on your access request"
        
        app_url = settings.FRONTEND_URL or "https://superconnector.ai"
        notes_section = f"\n\nNote: {admin_notes}" if admin_notes else ""
        
        body = f"""Hi {recipient_name},

Thank you for your interest in SuperConnect.ai.

Unfortunately, we're unable to approve your access request at this time.{notes_section}

We appreciate your understanding and encourage you to reach out if you have any questions.

Visit us at: {app_url}

Best regards,
The SuperConnect.ai Team"""
        
        return await self.send_email(to_email, subject, body, html=False)
    
    async def send_password_reset_email(
        self,
        to_email: str,
        reset_token: str
    ) -> bool:
        """
        Send password reset email with reset token
        
        Args:
            to_email: Recipient email address
            reset_token: Password reset token
        
        Returns:
            bool: True if email sent successfully, False otherwise
        """
        subject = "Password Reset Request"
        
        reset_url = f"{settings.FRONTEND_URL}/reset-password?token={reset_token}"
        
        body = f"""Hi,

You requested to reset your password for SuperConnect.ai.

Please click the link below to reset your password:
{reset_url}

This link will expire in 1 hour.

If you didn't request this, please ignore this email.

Best regards,
The SuperConnect.ai Team"""
        
        return await self.send_email(to_email, subject, body, html=False)

# Create a singleton instance
email_service = EmailService()

# Import Gmail service
from app.services.gmail_service import gmail_service

def get_email_service():
    """
    Get the appropriate email service based on configuration
    
    Returns:
        GmailService if EMAIL_SERVICE is 'gmail_api' and available, otherwise SMTP EmailService
    """
    if settings.EMAIL_SERVICE == "gmail_api" and gmail_service.is_available():
        logger.info("Using Gmail API for email sending")
        return gmail_service
    else:
        if settings.EMAIL_SERVICE == "gmail_api":
            logger.warning("Gmail API requested but not available. Falling back to SMTP.")
        logger.info("Using SMTP for email sending")
        return email_service


