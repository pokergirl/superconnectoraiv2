#!/usr/bin/env python3
"""
Gemini API Key Validation Script

This script validates the Gemini API key configuration and tests basic functionality
to help diagnose 404 errors and other API issues.

Usage:
    python test_gemini_api_validation.py
"""

import os
import sys
import asyncio
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_environment_setup():
    """Test basic environment setup."""
    print("🔧 GEMINI API VALIDATION SCRIPT")
    print("=" * 50)
    
    # Check if API key is set
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("❌ GEMINI_API_KEY not found in environment variables")
        print("   Please set GEMINI_API_KEY in your .env file")
        return False
    
    print(f"✅ GEMINI_API_KEY found (length: {len(api_key)} characters)")
    print(f"   Key preview: {api_key[:10]}...{api_key[-4:]}")
    
    return True

def test_gemini_import():
    """Test if Gemini library can be imported."""
    try:
        import google.generativeai as genai
        print("✅ google.generativeai library imported successfully")
        return True
    except ImportError as e:
        print(f"❌ Failed to import google.generativeai: {e}")
        print("   Please install: pip install google-generativeai")
        return False

def test_gemini_configuration():
    """Test Gemini API configuration."""
    try:
        import google.generativeai as genai
        
        api_key = os.getenv("GEMINI_API_KEY")
        genai.configure(api_key=api_key)
        print("✅ Gemini API configured successfully")
        return True
    except Exception as e:
        print(f"❌ Failed to configure Gemini API: {e}")
        return False

def test_model_availability():
    """Test different Gemini model availability."""
    try:
        import google.generativeai as genai
        
        models_to_test = [
            "gemini-1.5-pro-latest",
            "gemini-1.5-flash-latest", 
            "gemini-pro",
            "gemini-1.5-pro",
            "gemini-1.5-flash"
        ]
        
        print("\n📋 Testing model availability:")
        available_models = []
        
        for model_name in models_to_test:
            try:
                model = genai.GenerativeModel(model_name)
                print(f"✅ {model_name} - Available")
                available_models.append(model_name)
            except Exception as e:
                print(f"❌ {model_name} - Error: {e}")
        
        return available_models
        
    except Exception as e:
        print(f"❌ Error testing model availability: {e}")
        return []

def test_basic_generation():
    """Test basic content generation."""
    try:
        import google.generativeai as genai
        
        print("\n🧪 Testing basic content generation:")
        
        # Test with recommended model
        model = genai.GenerativeModel("gemini-1.5-pro-latest")
        
        test_prompt = "Say 'Hello, Gemini API is working!' in exactly those words."
        
        print(f"   Prompt: {test_prompt}")
        print("   Generating response...")
        
        response = model.generate_content(test_prompt)
        
        if response and response.text:
            print(f"✅ Response received: {response.text.strip()}")
            return True
        else:
            print("❌ Empty response received")
            return False
            
    except Exception as e:
        print(f"❌ Error during content generation: {e}")
        
        # Try to provide more specific error information
        if "404" in str(e):
            print("   🔍 404 Error detected - this usually means:")
            print("      - Invalid API key")
            print("      - Model name not available in your region")
            print("      - API endpoint issues")
        elif "403" in str(e):
            print("   🔍 403 Error detected - this usually means:")
            print("      - API key doesn't have permission")
            print("      - Quota exceeded")
            print("      - Billing not set up")
        elif "429" in str(e):
            print("   🔍 429 Error detected - rate limiting:")
            print("      - Too many requests")
            print("      - Try again in a few minutes")
        
        return False

def test_with_fallback_models():
    """Test with different models as fallback."""
    try:
        import google.generativeai as genai
        
        print("\n🔄 Testing fallback models:")
        
        fallback_models = [
            "gemini-1.5-pro-latest",
            "gemini-1.5-flash-latest",
            "gemini-pro",
            "gemini-1.5-pro"
        ]
        
        for model_name in fallback_models:
            try:
                print(f"   Testing {model_name}...")
                model = genai.GenerativeModel(model_name)
                response = model.generate_content("Hello")
                
                if response and response.text:
                    print(f"✅ {model_name} works! Response: {response.text.strip()[:50]}...")
                    return model_name
                else:
                    print(f"⚠️ {model_name} returned empty response")
                    
            except Exception as e:
                print(f"❌ {model_name} failed: {e}")
                continue
        
        print("❌ All fallback models failed")
        return None
        
    except Exception as e:
        print(f"❌ Error testing fallback models: {e}")
        return None

def test_api_quota_and_billing():
    """Test API quota and billing status."""
    try:
        import google.generativeai as genai
        
        print("\n💳 Testing API quota and billing:")
        
        # Try a very simple request to check quota
        model = genai.GenerativeModel("gemini-1.5-pro-latest")
        response = model.generate_content("Hi", 
                                        generation_config=genai.types.GenerationConfig(
                                            max_output_tokens=1
                                        ))
        
        if response:
            print("✅ API quota appears to be available")
            return True
        else:
            print("⚠️ Quota may be exhausted or billing issue")
            return False
            
    except Exception as e:
        error_str = str(e).lower()
        if "quota" in error_str or "billing" in error_str:
            print(f"❌ Quota/Billing issue detected: {e}")
            print("   Please check your Google Cloud billing and quota settings")
        else:
            print(f"❌ Error testing quota: {e}")
        return False

def main():
    """Main validation function."""
    print("Starting Gemini API validation...\n")
    
    # Test 1: Environment setup
    if not test_environment_setup():
        print("\n❌ Environment setup failed. Please fix and try again.")
        return False
    
    print()
    
    # Test 2: Import
    if not test_gemini_import():
        print("\n❌ Import failed. Please install required packages.")
        return False
    
    # Test 3: Configuration
    if not test_gemini_configuration():
        print("\n❌ Configuration failed. Please check your API key.")
        return False
    
    # Test 4: Model availability
    available_models = test_model_availability()
    if not available_models:
        print("\n❌ No models available. Please check your API key and region.")
        return False
    
    # Test 5: Basic generation
    if not test_basic_generation():
        print("\n⚠️ Basic generation failed. Trying fallback models...")
        
        # Test 6: Fallback models
        working_model = test_with_fallback_models()
        if not working_model:
            print("\n❌ All models failed. Please check your API configuration.")
            
            # Test 7: Quota and billing
            test_api_quota_and_billing()
            return False
        else:
            print(f"\n✅ Found working model: {working_model}")
    
    print("\n" + "=" * 50)
    print("🎉 VALIDATION COMPLETE!")
    print("✅ Gemini API is working correctly")
    print(f"✅ Recommended model: gemini-1.5-pro-latest")
    print(f"✅ Available models: {', '.join(available_models)}")
    
    print("\n📋 RECOMMENDATIONS:")
    print("1. Use 'gemini-1.5-pro-latest' as your primary model")
    print("2. Implement fallback to 'gemini-1.5-flash-latest' if needed")
    print("3. Add proper error handling for 404/403/429 errors")
    print("4. Monitor your API usage and quotas")
    
    return True

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️ Validation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        sys.exit(1)