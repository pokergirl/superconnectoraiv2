import logging
import os
import base64
import json
import tempfile
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from app.core.config import settings

logger = logging.getLogger(__name__)

class GmailService:
    """Service for sending emails using Gmail API with OAuth2 authentication"""
    
    def __init__(self):
        """Initialize Gmail service with OAuth2 credentials"""
        self.service = None
        self.credentials = None
        self._initialize_service()
    
    def _initialize_service(self):
        """Initialize Gmail service with OAuth2 credentials"""
        try:
            # Check if credentials are available (from file or environment)
            if not self._has_credentials():
                logger.warning("Gmail credentials not found")
                logger.warning("Gmail API will not be available. Please set up credentials.")
                return
            
            # Load or create credentials
            creds = self._load_or_create_credentials()
            
            if not creds or not creds.valid:
                logger.warning("Gmail credentials are not valid")
                return
            
            # Build the Gmail service
            self.service = build('gmail', 'v1', credentials=creds)
            self.credentials = creds
            logger.info("Gmail API service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Gmail service: {str(e)}")
    
    def _has_credentials(self) -> bool:
        """Check if Gmail credentials are available (from file or environment)"""
        # Check if credentials are in environment variables (Render/Cloud)
        if os.getenv("GMAIL_CREDENTIALS_BASE64"):
            return True
        
        # Check if credentials file exists
        if os.path.exists(settings.GMAIL_CREDENTIALS_FILE):
            return True
        
        return False
    
    def _get_credentials_path(self) -> str:
        """Get path to credentials file, creating from environment if needed"""
        # Check if credentials are in environment variables (Render/Cloud)
        if os.getenv("GMAIL_CREDENTIALS_BASE64"):
            try:
                # Decode base64 credentials
                creds_data = base64.b64decode(os.getenv("GMAIL_CREDENTIALS_BASE64")).decode('utf-8')
                creds_json = json.loads(creds_data)
                
                # Create temporary file
                temp_fd, temp_path = tempfile.mkstemp(suffix='.json', prefix='gmail_creds_')
                with os.fdopen(temp_fd, 'w') as f:
                    json.dump(creds_json, f)
                
                logger.info("Loaded Gmail credentials from environment variables")
                return temp_path
            except Exception as e:
                logger.error(f"Error loading credentials from environment: {e}")
                raise
        
        # Return regular file path
        return settings.GMAIL_CREDENTIALS_FILE
    
    def _get_token_path(self) -> Optional[str]:
        """Get path to token file, creating from environment if needed"""
        # Check if token is in environment variables (Render/Cloud)
        if os.getenv("GMAIL_TOKEN_BASE64"):
            try:
                # Decode base64 token
                token_data = base64.b64decode(os.getenv("GMAIL_TOKEN_BASE64")).decode('utf-8')
                token_json = json.loads(token_data)
                
                # Create temporary file
                temp_fd, temp_path = tempfile.mkstemp(suffix='.json', prefix='gmail_token_')
                with os.fdopen(temp_fd, 'w') as f:
                    json.dump(token_json, f)
                
                logger.info("Loaded Gmail token from environment variables")
                return temp_path
            except Exception as e:
                logger.error(f"Error loading token from environment: {e}")
                return None
        
        # Return regular file path
        if os.path.exists(settings.GMAIL_TOKEN_FILE):
            return settings.GMAIL_TOKEN_FILE
        
        return None
    
    def _load_or_create_credentials(self):
        """Load existing credentials or create new ones if needed"""
        creds = None
        
        # Get token path (from file or environment)
        token_path = self._get_token_path()
        
        # Check if token exists
        if token_path:
            try:
                creds = Credentials.from_authorized_user_file(
                    token_path, 
                    settings.GMAIL_SCOPES
                )
                logger.info("Loaded existing Gmail credentials from token")
            except Exception as e:
                logger.error(f"Error loading credentials: {str(e)}")
        
        # If there are no (valid) credentials available, let the user log in
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                    logger.info("Refreshed expired Gmail credentials")
                except Exception as e:
                    logger.error(f"Error refreshing credentials: {str(e)}")
                    creds = None
            
            if not creds:
                logger.info("No valid credentials found. Please run setup_gmail_oauth.py to authenticate")
                return None
        
        return creds
    
    def _create_message(self, to_email: str, subject: str, body: str, html: bool = True) -> dict:
        """
        Create a message for Gmail API
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            body: Email body
            html: Whether the body is HTML
        
        Returns:
            dict: Message object for Gmail API
        """
        try:
            message = MIMEMultipart('alternative')
            message['To'] = to_email
            message['From'] = f"{settings.FROM_NAME} <{settings.FROM_EMAIL}>"
            message['Subject'] = subject
            
            # Attach body
            if html:
                message.attach(MIMEText(body, 'html'))
            else:
                message.attach(MIMEText(body, 'plain'))
            
            # Encode message
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
            
            return {'raw': raw_message}
            
        except Exception as e:
            logger.error(f"Error creating message: {str(e)}")
            raise
    
    async def send_email(
        self,
        to_email: str,
        subject: str,
        body: str,
        html: bool = True
    ) -> bool:
        """
        Send an email using Gmail API
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            body: Email body (HTML or plain text)
            html: Whether the body is HTML (default: True)
        
        Returns:
            bool: True if email sent successfully, False otherwise
        """
        try:
            if not self.service:
                logger.error("Gmail service not initialized. Cannot send email.")
                return False
            
            # Create message
            message = self._create_message(to_email, subject, body, html)
            
            # Send email
            sent_message = self.service.users().messages().send(
                userId='me',
                body=message
            ).execute()
            
            logger.info(f"Email sent successfully to {to_email}. Message ID: {sent_message.get('id')}")
            return True
            
        except HttpError as e:
            logger.error(f"Gmail API error sending email to {to_email}: {str(e)}")
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
    
    def is_available(self) -> bool:
        """Check if Gmail service is available"""
        return self.service is not None

# Create a singleton instance
gmail_service = GmailService()

