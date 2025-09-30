#!/usr/bin/env python3
"""
Diagnostic and fix script to test Gemini model names and update the .env file.
This script will test a list of Gemini models, find the best available one,
and then update the GEMINI_MODEL variable in the .env file.
"""

import asyncio
import sys
import os

# Add the backend directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import google.generativeai as genai
from app.core.config import settings

def update_env_file(key: str, value: str):
    """Update the .env file with the given key-value pair."""
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
    
    lines = []
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            lines = f.readlines()

    key_found = False
    for i, line in enumerate(lines):
        if line.strip().startswith(f"{key}="):
            lines[i] = f'{key}="{value}"\n'
            key_found = True
            break
    
    if not key_found:
        lines.append(f'\n{key}="{value}"\n')

    with open(env_path, 'w') as f:
        f.writelines(lines)
    
    print(f"✅ Successfully updated {key} in .env file to '{value}'")

async def test_and_fix_gemini_models():
    """Test different Gemini model names and update .env with the best working one"""
    print("🔍 GEMINI MODEL DIAGNOSIS & FIX")
    print("=" * 60)
    
    if not settings.GEMINI_API_KEY:
        print("❌ GEMINI_API_KEY not found in environment variables")
        return
    
    # Configure Gemini
    genai.configure(api_key=settings.GEMINI_API_KEY)
    
    # List of model names to test, in order of preference
    model_names_to_test = [
        "gemini-1.5-pro-latest",
        "gemini-2.5-flash-lite",
        "gemini-1.5-flash-latest",
        "gemini-pro",
        "gemini-1.5-pro",
        "gemini-1.5-flash",
        "gemini-flash",
    ]
    
    print(f"📋 Testing {len(model_names_to_test)} different model names...")
    print()
    
    working_models = []
    
    for i, model_name in enumerate(model_names_to_test, 1):
        print(f"{i}. Testing model: '{model_name}'")
        
        try:
            model = genai.GenerativeModel(model_name)
            test_prompt = "Say 'Hello' in one word."
            response = model.generate_content(test_prompt)
            
            if response and response.text:
                print(f"   ✅ SUCCESS: Model works! Response: '{response.text.strip()}'")
                working_models.append(model_name)
                
        except Exception as e:
            error_msg = str(e)
            print(f"   ❌ FAILED: {error_msg}")
        
        print()

    print("=" * 60)
    
    if working_models:
        best_model = working_models  # The first one found is the highest priority
        print(f"🏆 Found best available model: '{best_model}'")
        print("\n🔧 Applying fix...")
        update_env_file("GEMINI_MODEL", best_model)
        print("\n🎉 Fix applied. Please restart the backend server to see the changes.")
    else:
        print("❌ No working models found. Please check your GEMINI_API_KEY and network connection.")

if __name__ == "__main__":
    asyncio.run(test_and_fix_gemini_models())