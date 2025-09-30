import os
import asyncio
import google.generativeai as genai
from dotenv import load_dotenv

async def test_specific_gemini_model():
    """Tests the specific gemini-2.5-flash-lite model."""
    load_dotenv()
    print("--- Testing gemini-2.5-flash-lite ---")
    
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("❌ ERROR: GEMINI_API_KEY not found in .env file.")
        return

    try:
        genai.configure(api_key=api_key)
        
        model_name = "gemini-2.5-flash-lite"
        print(f"🔧 Initializing model: {model_name}")
        
        model = genai.GenerativeModel(model_name)
        
        print("🧪 Generating content...")
        response = model.generate_content("test")
        
        if response and response.text:
            print(f"✅ SUCCESS: Model '{model_name}' generated a response.")
            print(f"   Response: {response.text[:80]}...")
        else:
            print(f"❌ FAILED: Model '{model_name}' produced an empty response.")

    except Exception as e:
        print(f"❌ FAILED: An error occurred while testing model '{model_name}'.")
        print(f"   Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_specific_gemini_model())