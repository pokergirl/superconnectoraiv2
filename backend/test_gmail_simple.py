#!/usr/bin/env python3
"""
Simple Gmail API test without user input
"""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

async def test_gmail():
    from app.services.gmail_service import gmail_service
    from app.services.email_service import get_email_service
    from app.core.config import settings
    
    print("=" * 60)
    print("  Gmail API Simple Test")
    print("=" * 60)
    print()
    
    # Test 1: Check if Gmail service is available
    print("Test 1: Checking Gmail service availability...")
    if gmail_service.is_available():
        print("✅ Gmail service is available")
    else:
        print("❌ Gmail service is not available")
        return False
    print()
    
    # Test 2: Check email service selection
    print("Test 2: Checking email service selection...")
    email_service = get_email_service()
    service_name = type(email_service).__name__
    print(f"✅ Selected email service: {service_name}")
    
    if service_name == "GmailService":
        print("✅ Using Gmail API (correct!)")
    else:
        print("⚠️  Using SMTP (not Gmail API)")
    print()
    
    # Test 3: Configuration
    print("Test 3: Checking configuration...")
    print(f"   EMAIL_SERVICE: {settings.EMAIL_SERVICE}")
    print(f"   FROM_EMAIL: {settings.FROM_EMAIL}")
    print(f"   FROM_NAME: {settings.FROM_NAME}")
    print()
    
    # Summary
    print("=" * 60)
    print("  Test Summary")
    print("=" * 60)
    
    if service_name == "GmailService":
        print("✅ All tests passed!")
        print()
        print("Gmail API is configured correctly and ready to use.")
        print("You can now send emails via Gmail API.")
        print()
        print("Next steps:")
        print("  1. For production (Render):")
        print("     - Run: python encode_gmail_credentials.py")
        print("     - Add environment variables to Render")
        print("  2. Test sending an email by approving an access request")
        return True
    else:
        print("⚠️  Gmail API is not being used")
        print("   Check EMAIL_SERVICE environment variable")
        return False

if __name__ == '__main__':
    try:
        success = asyncio.run(test_gmail())
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

