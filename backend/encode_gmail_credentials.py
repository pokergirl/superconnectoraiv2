#!/usr/bin/env python3
"""
Helper script to encode Gmail credentials for Render environment variables
"""

import os
import base64
import json

def encode_file_to_base64(filepath):
    """Encode a JSON file to base64"""
    if not os.path.exists(filepath):
        return None
    
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        json_str = json.dumps(data)
        encoded = base64.b64encode(json_str.encode('utf-8')).decode('utf-8')
        return encoded
    except Exception as e:
        print(f"Error encoding {filepath}: {e}")
        return None

def main():
    print("=" * 70)
    print("  Gmail Credentials Encoder for Render")
    print("=" * 70)
    print()
    
    creds_file = "credentials.json"
    token_file = "token.json"
    
    if not os.path.exists(creds_file):
        print(f"❌ Error: {creds_file} not found!")
        return
    
    if not os.path.exists(token_file):
        print(f"❌ Error: {token_file} not found!")
        return
    
    print("✅ Found credentials.json and token.json")
    print()
    
    print("Encoding credentials...")
    creds_encoded = encode_file_to_base64(creds_file)
    token_encoded = encode_file_to_base64(token_file)
    
    if not creds_encoded or not token_encoded:
        print("❌ Failed to encode credentials")
        return
    
    print("✅ Credentials encoded successfully")
    print()
    
    # Save to files
    with open("credentials_base64.txt", "w") as f:
        f.write(creds_encoded)
    
    with open("token_base64.txt", "w") as f:
        f.write(token_encoded)
    
    print("📄 Saved encoded credentials to:")
    print("   - credentials_base64.txt")
    print("   - token_base64.txt")
    print()
    
    print("=" * 70)
    print("  Render Environment Variables Setup")
    print("=" * 70)
    print()
    print("1. Go to: https://dashboard.render.com")
    print("2. Select your service > Environment tab")
    print("3. Add these 3 environment variables:")
    print()
    print("   GMAIL_CREDENTIALS_BASE64")
    print("   (copy from credentials_base64.txt)")
    print()
    print("   GMAIL_TOKEN_BASE64")
    print("   (copy from token_base64.txt)")
    print()
    print("   EMAIL_SERVICE")
    print("   gmail_api")
    print()
    print("4. Save and redeploy")
    print()
    print("=" * 70)

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"❌ Error: {e}")

