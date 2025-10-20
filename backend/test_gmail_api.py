#!/usr/bin/env python3
"""
Test script for Gmail API integration

This script tests the Gmail API service to ensure it's working correctly.
"""

import asyncio
import logging
from app.services.gmail_service import gmail_service
from app.services.email_service import get_email_service
from app.core.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_gmail_service():
    """Test the Gmail service"""
    
    print("=" * 60)
    print("  Gmail API Integration Test")
    print("=" * 60)
    print()
    
    # Test 1: Check if Gmail service is available
    print("Test 1: Checking Gmail service availability...")
    if gmail_service.is_available():
        print("✅ Gmail service is available")
    else:
        print("❌ Gmail service is not available")
        print("   Please run setup_gmail_oauth.py to configure Gmail API")
        return False
    print()
    
    # Test 2: Check email service selection
    print("Test 2: Checking email service selection...")
    email_service = get_email_service()
    print(f"✅ Selected email service: {type(email_service).__name__}")
    print()
    
    # Test 3: Send a test email
    print("Test 3: Sending test email...")
    print(f"   Configuration:")
    print(f"   - FROM_EMAIL: {settings.FROM_EMAIL}")
    print(f"   - FROM_NAME: {settings.FROM_NAME}")
    print(f"   - EMAIL_SERVICE: {settings.EMAIL_SERVICE}")
    print()
    
    # Get recipient email from user
    recipient_email = input("Enter recipient email address (or press Enter to skip): ").strip()
    
    if not recipient_email:
        print("⚠️  Skipping email send test")
        return True
    
    test_subject = "Test Email from SuperConnector Gmail API"
    test_body = """
    <html>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
        <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
            <h2 style="color: #3498db;">Gmail API Test Email</h2>
            <p>This is a test email sent using the Gmail API integration.</p>
            <p>If you received this email, the Gmail API is working correctly! 🎉</p>
            <hr style="border: 1px solid #eee; margin: 20px 0;">
            <p style="color: #666; font-size: 12px;">
                This email was sent from SuperConnector using Gmail API.
            </p>
        </div>
    </body>
    </html>
    """
    
    print(f"   Sending test email to: {recipient_email}")
    success = await email_service.send_email(
        to_email=recipient_email,
        subject=test_subject,
        body=test_body,
        html=True
    )
    
    if success:
        print("✅ Test email sent successfully!")
        print(f"   Please check {recipient_email} for the test email")
    else:
        print("❌ Failed to send test email")
        return False
    print()
    
    # Summary
    print("=" * 60)
    print("  Test Summary")
    print("=" * 60)
    print("✅ All tests passed!")
    print()
    print("Gmail API integration is working correctly.")
    print("You can now use it in your application.")
    print()
    
    return True

if __name__ == '__main__':
    try:
        success = asyncio.run(test_gmail_service())
        exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        exit(1)
    except Exception as e:
        print(f"\n\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)

