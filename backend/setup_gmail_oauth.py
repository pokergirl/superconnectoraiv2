#!/usr/bin/env python3
"""
Gmail API OAuth2 Setup Script

This script helps you set up Gmail API credentials for sending emails.

Prerequisites:
1. Create a Google Cloud Project at https://console.cloud.google.com
2. Enable the Gmail API in your project
3. Create OAuth 2.0 credentials (Desktop application type)
4. Download the credentials JSON file

Usage:
1. Place your credentials.json file in the backend directory
2. Run this script: python setup_gmail_oauth.py
3. Follow the authentication flow in your browser
4. The token will be saved to token.json for future use
"""

import os
import sys
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

# Scopes required for sending emails
SCOPES = ['https://www.googleapis.com/auth/gmail.send']

def setup_gmail_oauth():
    """Set up Gmail OAuth2 credentials"""
    
    # Check if credentials file exists
    if not os.path.exists('credentials.json'):
        print("❌ Error: credentials.json not found!")
        print("\n📝 Please follow these steps:")
        print("1. Go to https://console.cloud.google.com")
        print("2. Create a new project or select an existing one")
        print("3. Enable the Gmail API:")
        print("   - Go to 'APIs & Services' > 'Library'")
        print("   - Search for 'Gmail API' and click 'Enable'")
        print("4. Create OAuth 2.0 credentials:")
        print("   - Go to 'APIs & Services' > 'Credentials'")
        print("   - Click 'Create Credentials' > 'OAuth client ID'")
        print("   - Choose 'Desktop app' as application type")
        print("   - Name it 'SuperConnector Gmail'")
        print("   - Click 'Create'")
        print("5. Download the credentials:")
        print("   - Click the download icon next to your OAuth client")
        print("   - Save it as 'credentials.json' in the backend directory")
        print("\nAfter completing these steps, run this script again.")
        sys.exit(1)
    
    creds = None
    
    # Check if token file exists
    if os.path.exists('token.json'):
        try:
            creds = Credentials.from_authorized_user_file('token.json', SCOPES)
            print("✅ Found existing token.json")
        except Exception as e:
            print(f"⚠️  Error loading existing token: {e}")
            creds = None
    
    # If there are no (valid) credentials available, let the user log in
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("🔄 Refreshing expired token...")
            try:
                creds.refresh(Request())
            except Exception as e:
                print(f"❌ Error refreshing token: {e}")
                print("Please re-authenticate...")
                creds = None
        
        if not creds:
            print("🔐 Starting OAuth2 authentication flow...")
            print("\nA browser window will open for authentication.")
            print("Please sign in with your Gmail account and grant permissions.\n")
            
            try:
                flow = InstalledAppFlow.from_client_secrets_file(
                    'credentials.json', 
                    SCOPES
                )
                creds = flow.run_local_server(port=0)
                print("✅ Authentication successful!")
            except Exception as e:
                print(f"❌ Authentication failed: {e}")
                sys.exit(1)
        
        # Save the credentials for the next run
        print("💾 Saving credentials to token.json...")
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
        print("✅ Credentials saved successfully!")
    
    # Verify the credentials work
    print("\n🔍 Verifying Gmail API access...")
    try:
        from googleapiclient.discovery import build
        service = build('gmail', 'v1', credentials=creds)
        
        # Try to get user profile
        profile = service.users().getProfile(userId='me').execute()
        email_address = profile.get('emailAddress')
        
        print(f"✅ Successfully authenticated as: {email_address}")
        print("\n🎉 Gmail API setup complete!")
        print("\n📧 You can now send emails using the Gmail API.")
        print("\n💡 Tips:")
        print("   - The token.json file contains your authentication credentials")
        print("   - Keep it secure and never commit it to version control")
        print("   - The token will automatically refresh when it expires")
        print("   - If you need to re-authenticate, delete token.json and run this script again")
        
        return True
        
    except Exception as e:
        print(f"❌ Error verifying Gmail API access: {e}")
        return False

if __name__ == '__main__':
    print("=" * 60)
    print("  Gmail API OAuth2 Setup for SuperConnector")
    print("=" * 60)
    print()
    
    success = setup_gmail_oauth()
    
    if success:
        print("\n✅ Setup completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Setup failed. Please check the errors above.")
        sys.exit(1)

