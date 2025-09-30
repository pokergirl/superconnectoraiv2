import asyncio
import httpx

async def run_test():
    test_url = "http://localhost:8000/api/v1/search"
    
    # Replace with a valid access token
    access_token = "your_jwt_token_here"
    
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    
    payload = {
        "query": "software engineer"
    }
    
    print("Running search ranking diagnosis...")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(test_url, headers=headers, json=payload, timeout=120)
        
        if response.status_code == 200:
            print("Search request successful.")
            results = response.json()
            if results:
                print(f"Received {len(results)} results.")
                # Check if scores are present and greater than 0
                if all(r.get("score", 0) > 0 for r in results):
                    print("Ranking appears to be working.")
                else:
                    print("Ranking issue detected: scores are missing or zero.")
            else:
                print("Search returned no results.")
        else:
            print(f"Search request failed with status code: {response.status_code}")
            print(f"Response: {response.text}")
            
    except httpx.RequestError as e:
        print(f"An error occurred while making the request: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    asyncio.run(run_test())