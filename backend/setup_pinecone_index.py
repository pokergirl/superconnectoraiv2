#!/usr/bin/env python3
"""
Pinecone Index Setup Script

This script creates and configures a Pinecone serverless index for storing profile embeddings.
It includes support for hybrid search and metadata filtering.

Usage:
    python setup_pinecone_index.py

Requirements:
    - PINECONE_API_KEY must be set in environment or .env file
    - PINECONE_INDEX_NAME must be set in environment or .env file (optional, defaults to 'profile-embeddings')
"""

import sys
import os
from pathlib import Path

# Add the backend directory to Python path so we can import our modules
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from app.services.pinecone_index_service import pinecone_index_service
from app.core.config import settings


def main():
    """Main function to set up the Pinecone index."""
    print("🚀 Pinecone Index Setup Script")
    print("=" * 50)
    
    # Validate configuration
    if not settings.PINECONE_API_KEY:
        print("❌ Error: PINECONE_API_KEY is not set in environment variables or .env file")
        print("Please set your Pinecone API key and try again.")
        sys.exit(1)
    
    print(f"📋 Configuration:")
    print(f"   Index Name: {settings.PINECONE_INDEX_NAME}")
    print(f"   API Key: {'*' * (len(settings.PINECONE_API_KEY) - 4) + settings.PINECONE_API_KEY[-4:]}")
    print()
    
    try:
        # Set up the index
        result = pinecone_index_service.setup_index()
        
        if result["success"]:
            print("\n🎉 Setup completed successfully!")
            
            if result["created"]:
                print("✅ New index created")
            else:
                print("ℹ️  Index already existed")
            
            # Display index information
            if result["index_info"]:
                info = result["index_info"]
                print(f"\n📊 Index Information:")
                print(f"   Name: {info['name']}")
                print(f"   Dimension: {info['dimension']}")
                print(f"   Metric: {info['metric']}")
                print(f"   Status: {info['status']}")
                print(f"   Host: {info['host']}")
            
            print(f"\n✨ Your Pinecone index '{settings.PINECONE_INDEX_NAME}' is ready to use!")
            print("\nNext steps:")
            print("1. Run your application")
            print("2. Use the embeddings service to process and store profile data")
            print("3. Perform similarity searches on your embedded profiles")
            
        else:
            print(f"\n❌ Setup failed: {result['message']}")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n💥 Unexpected error during setup: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()