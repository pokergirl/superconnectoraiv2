import requests
import json

def get_access_token(email: str, password: str) -> str | None:
    """
    Logs in a user and returns the access token.
    """
    url = "http://localhost:8000/api/v1/auth/login"
    data = {
        "username": email,
        "password": password
    }
    
    try:
        response = requests.post(url, data=data)
        response.raise_for_status()
        
        token_data = response.json()
        return token_data.get("access_token")
        
    except requests.exceptions.HTTPError as http_err:
        print(f"❌ HTTP error occurred: {http_err}")
        print(f"   Response content: {response.text}")
        return None
    except Exception as err:
        print(f"❌ An unexpected error occurred: {err}")
        return None

if __name__ == "__main__":
    # Replace with your test user's credentials
    test_email = "test@example.com"
    test_password = "testpassword"
    
    print(f"🚀 Attempting to log in as {test_email}...")
    access_token = get_access_token(test_email, test_password)
    
    if access_token:
        print("✅ Successfully obtained access token:")
        print(access_token)
    else:
        print("❌ Failed to obtain access token.")