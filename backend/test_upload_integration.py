#!/usr/bin/env python3
"""
Test script to verify the upload integration with embedding processing.
This script simulates the background task that would be triggered after file upload.
"""

import asyncio
import sys
import os

# Add the app directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.services.embeddings_service import embeddings_service

async def test_embedding_processing():
    """Test the embedding processing with the existing Connections.csv file."""
    
    csv_path = "Connections.csv"
    test_user_id = "test_user_123"
    
    if not os.path.exists(csv_path):
        print(f"Error: {csv_path} not found in current directory")
        return False
    
    print(f"Testing embedding processing with {csv_path}")
    print(f"User ID: {test_user_id}")
    print("-" * 50)
    
    try:
        # This simulates what the background task would do
        result = await embeddings_service.process_profiles_and_upsert(
            csv_path=csv_path,
            user_id=test_user_id
        )
        
        print("✅ Embedding processing completed successfully!")
        print(f"Results: {result}")
        return True
        
    except Exception as e:
        print(f"❌ Error during embedding processing: {e}")
        return False

async def main():
    """Main test function."""
    print("🚀 Testing Upload Integration with Embedding Processing")
    print("=" * 60)
    
    success = await test_embedding_processing()
    
    if success:
        print("\n✅ Integration test PASSED!")
        print("The upload endpoint will now automatically trigger embedding processing.")
    else:
        print("\n❌ Integration test FAILED!")
        print("Please check the error messages above.")

if __name__ == "__main__":
    asyncio.run(main())