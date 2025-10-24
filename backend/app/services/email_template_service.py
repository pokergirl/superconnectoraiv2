from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

class EmailTemplateService:
    """Service for replacing placeholders in email templates with actual data"""
    
    @staticmethod
    async def get_user_info_from_access_request(db, user_email: str) -> Dict[str, Any]:
        """
        Get user information from access_requests collection
        
        Args:
            db: Database connection
            user_email: User's email address
        
        Returns:
            dict: User information including full_name and organization (LinkedIn URL)
        """
        try:
            logger.info(f"🔍 Looking up access request for email: {user_email}")
            
            # Find the access request for this user
            access_request = await db.access_requests.find_one({"email": user_email})
            
            if access_request:
                logger.info(f"✅ Found access request: {access_request}")
                return {
                    "full_name": access_request.get("full_name", ""),
                    "organization": access_request.get("organization", ""),
                    "reason": access_request.get("reason", "")
                }
            else:
                logger.warning(f"❌ No access request found for email: {user_email}")
                return {
                    "full_name": "",
                    "organization": "",
                    "reason": ""
                }
        except Exception as e:
            logger.error(f"❌ Error retrieving user info from access request: {str(e)}")
            return {
                "full_name": "",
                "organization": "",
                "reason": ""
            }
    
    @staticmethod
    async def replace_placeholders_with_user_info(
        template: str,
        connection_name: str,
        requester_name: str,
        reason: Optional[str] = None,
        about: Optional[str] = None,
        requester_linkedin_url: Optional[str] = None,
        db=None,
        user_email: Optional[str] = None
    ) -> str:
        """
        Replace placeholders in email template with actual data, including user info from access_requests
        
        Args:
            template: Email template with placeholders like {requesterName}, {reason}, etc.
            connection_name: Name of the connection being introduced to
            requester_name: Name of the person requesting the introduction
            reason: Why the requester wants to connect (optional)
            about: About the requester (optional)
            requester_linkedin_url: Requester's LinkedIn profile URL (optional)
            db: Database connection
            user_email: User's email address to look up in access_requests
        
        Returns:
            str: Email template with placeholders replaced
        """
        try:
            logger.info(f"🚀 Starting template replacement with user info")
            logger.info(f"📧 User email: {user_email}")
            logger.info(f"👤 Original requester name: {requester_name}")
            logger.info(f"🔗 Original LinkedIn URL: {requester_linkedin_url}")
            
            # Get user info from access_requests if available
            user_info = {}
            if db is not None and user_email:
                logger.info(f"🔍 Looking up user info in access_requests...")
                user_info = await EmailTemplateService.get_user_info_from_access_request(db, user_email)
                logger.info(f"📋 User info from access_requests: {user_info}")
            else:
                logger.warning(f"⚠️ No database or user_email provided, skipping access_requests lookup")
            
            # Use access request data if available, otherwise fall back to provided data
            actual_requester_name = user_info.get("full_name") or requester_name
            actual_linkedin_url = user_info.get("organization") or requester_linkedin_url
            
            logger.info(f"✅ Final requester name: {actual_requester_name}")
            logger.info(f"✅ Final LinkedIn URL: {actual_linkedin_url}")
            
            # Create replacement dictionary
            replacements = {
                '{connectionName}': connection_name,
                '{requesterName}': actual_requester_name,
                '{reason}': reason or "They're interested in connecting with you.",
                '{about}': about or f"{actual_requester_name} is looking to connect and would love to learn more about your work.",
            }
            
            # Add LinkedIn URL if provided
            if actual_linkedin_url:
                linkedin_section = f"\n\nYou can view {actual_requester_name}'s LinkedIn profile here: {actual_linkedin_url}"
                replacements['{requesterLinkedIn}'] = linkedin_section
            else:
                replacements['{requesterLinkedIn}'] = ""
            
            logger.info(f"🔄 Replacement dictionary: {replacements}")
            
            # Replace all placeholders
            result = template
            for placeholder, value in replacements.items():
                result = result.replace(placeholder, value)
            
            logger.info(f"✅ Email template placeholders replaced successfully with user info from access_requests")
            return result
            
        except Exception as e:
            logger.error(f"❌ Error replacing email template placeholders: {str(e)}")
            # Return template with basic replacements if error occurs
            return template.replace('{connectionName}', connection_name).replace('{requesterName}', requester_name)
    
    @staticmethod
    def replace_placeholders(
        template: str,
        connection_name: str,
        requester_name: str,
        reason: Optional[str] = None,
        about: Optional[str] = None,
        requester_linkedin_url: Optional[str] = None
    ) -> str:
        """
        Replace placeholders in email template with actual data (synchronous version for backward compatibility)
        
        Args:
            template: Email template with placeholders like {requesterName}, {reason}, etc.
            connection_name: Name of the connection being introduced to
            requester_name: Name of the person requesting the introduction
            reason: Why the requester wants to connect (optional)
            about: About the requester (optional)
            requester_linkedin_url: Requester's LinkedIn profile URL (optional)
        
        Returns:
            str: Email template with placeholders replaced
        """
        try:
            # Create replacement dictionary
            replacements = {
                '{connectionName}': connection_name,
                '{requesterName}': requester_name,
                '{reason}': reason or "They're interested in connecting with you.",
                '{about}': about or f"{requester_name} is looking to connect and would love to learn more about your work.",
            }
            
            # Add LinkedIn URL if provided
            if requester_linkedin_url:
                linkedin_section = f"\n\nYou can view {requester_name}'s LinkedIn profile here: {requester_linkedin_url}"
                replacements['{requesterLinkedIn}'] = linkedin_section
            else:
                replacements['{requesterLinkedIn}'] = ""
            
            # Replace all placeholders
            result = template
            for placeholder, value in replacements.items():
                result = result.replace(placeholder, value)
            
            logger.info(f"Email template placeholders replaced successfully")
            return result
            
        except Exception as e:
            logger.error(f"Error replacing email template placeholders: {str(e)}")
            # Return template with basic replacements if error occurs
            return template.replace('{connectionName}', connection_name).replace('{requesterName}', requester_name)
    
    @staticmethod
    def get_default_template() -> str:
        """
        Get the default email template for warm introductions
        
        Returns:
            str: Default email template with proper HTML formatting
        """
        return """Hi {connectionName},<br><br>

I hope this email finds you well. I wanted to reach out regarding a warm introduction request that was made through SuperConnect AI.<br><br>

{requesterName} has requested an introduction to you, and I wanted to facilitate this connection. They mentioned they're interested in connecting because:<br><br>

{reason}<br><br>

Here's a bit about {requesterName}:<br>
{about}{requesterLinkedIn}<br><br>

Would you be open to a brief conversation or connection? I'd be happy to facilitate an introduction if you're interested.<br><br>

Best regards,<br>
Ha<br>
SuperConnect AI"""
