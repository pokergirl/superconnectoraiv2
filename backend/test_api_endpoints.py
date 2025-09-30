import asyncio
import sys
import os
import requests
import json

# Add the backend directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_api_endpoints():
    """Test the failing API endpoints to get exact error details"""
    base_url = "http://localhost:8000/api/v1"
    
    # First, login to get a token
    login_data = {
        "username": "admin@superconnect.ai",
        "password": "admin123"
    }
    
    print("🔐 Logging in...")
    try:
        login_response = requests.post(f"{base_url}/auth/login", data=login_data)
        if login_response.status_code != 200:
            print(f"❌ Login failed: {login_response.status_code} - {login_response.text}")
            return
        
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print("✅ Login successful")
        
        # Test last-search-results endpoint
        print("\n🔍 Testing /api/v1/last-search-results...")
        try:
            response = requests.get(f"{base_url}/last-search-results", headers=headers)
            print(f"Status: {response.status_code}")
            if response.status_code != 200:
                print(f"Error response: {response.text}")
            else:
                print(f"Success response: {response.json()}")
        except Exception as e:
            print(f"Request failed: {e}")
        
        # Test saved-searches endpoint
        print("\n💾 Testing /api/v1/saved-searches...")
        try:
            response = requests.get(f"{base_url}/saved-searches", headers=headers)
            print(f"Status: {response.status_code}")
            if response.status_code != 200:
                print(f"Error response: {response.text}")
            else:
                print(f"Success response: {response.json()}")
        except Exception as e:
            print(f"Request failed: {e}")
            
    except Exception as e:
        print(f"❌ Login request failed: {e}")

if __name__ == "__main__":
    test_api_endpoints()