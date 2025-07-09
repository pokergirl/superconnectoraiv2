#!/usr/bin/env python3
"""
Test script for the retrieval service functionality.
This script tests the main components of the retrieval service.
"""

import asyncio
import sys
import os

# Add the backend directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.retrieval_service import retrieval_service
from app.core.config import settings

async def test_query_rewrite():
    """Test the optional LLM query rewrite functionality."""
    print("=" * 50)
    print("Testing Query Rewrite Functionality")
    print("=" * 50)
    
    test_queries = [
        "I'm looking for someone who has experience in machine learning and artificial intelligence, preferably someone who has worked at a tech company in Silicon Valley and has at least 5 years of experience in the field",
        "Find me a marketing professional with social media expertise",
        "Senior software engineer with Python experience"
    ]
    
    for query in test_queries:
        print(f"\nOriginal query: {query}")
        
        # Test with rewrite enabled
        rewritten = await retrieval_service.rewrite_query_with_llm(query, enable_rewrite=True)
        print(f"Rewritten query: {rewritten}")
        
        # Test with rewrite disabled
        unchanged = await retrieval_service.rewrite_query_with_llm(query, enable_rewrite=False)
        print(f"Unchanged query: {unchanged}")
        print("-" * 30)

async def test_embedding_generation():
    """Test embedding generation for queries."""
    print("=" * 50)
    print("Testing Embedding Generation")
    print("=" * 50)
    
    test_query = "Senior software engineer with Python experience"
    
    try:
        from app.services.embeddings_service import embeddings_service
        embedding = await embeddings_service.generate_embedding(test_query)
        print(f"Query: {test_query}")
        print(f"Embedding dimension: {len(embedding)}")
        print(f"First 5 values: {embedding[:5]}")
        return embedding
    except Exception as e:
        print(f"Error generating embedding: {e}")
        return None

async def test_chunk_size_calculation():
    """Test the chunk size calculation for context budgeting."""
    print("=" * 50)
    print("Testing Chunk Size Calculation")
    print("=" * 50)
    
    chunk_size = retrieval_service.calculate_chunk_size()
    print(f"Calculated chunk size: {chunk_size}")
    print(f"Total token limit: {retrieval_service.TOTAL_TOKEN_LIMIT}")
    print(f"Estimated prompt tokens: {retrieval_service.ESTIMATED_PROMPT_TOKENS}")
    print(f"Estimated avg profile tokens: {retrieval_service.ESTIMATED_AVG_PROFILE_TOKENS}")

async def test_service_health():
    """Test the health of service components."""
    print("=" * 50)
    print("Testing Service Component Health")
    print("=" * 50)
    
    print(f"OpenAI client initialized: {retrieval_service.openai_client is not None}")
    print(f"Pinecone client initialized: {retrieval_service.pinecone_client is not None}")
    print(f"Pinecone index available: {retrieval_service.index is not None}")
    
    # Test configuration
    print(f"\nConfiguration:")
    print(f"OPENAI_API_KEY set: {'Yes' if settings.OPENAI_API_KEY else 'No'}")
    print(f"PINECONE_API_KEY set: {'Yes' if settings.PINECONE_API_KEY else 'No'}")
    print(f"PINECONE_INDEX_NAME: {settings.PINECONE_INDEX_NAME}")

async def test_hybrid_query_simulation():
    """Simulate a hybrid query (without actually calling Pinecone)."""
    print("=" * 50)
    print("Testing Hybrid Query Simulation")
    print("=" * 50)
    
    # Create a dummy embedding vector
    dummy_vector = [0.1] * 1536  # 1536 dimensions for text-embedding-3-small
    
    print(f"Simulating hybrid query with:")
    print(f"- Vector dimension: {len(dummy_vector)}")
    print(f"- Top K: 600")
    print(f"- Alpha: 0.6")
    print(f"- Namespace: default_user")
    
    if retrieval_service.index:
        try:
            # This would actually call Pinecone - commenting out for safety
            # profile_ids = await retrieval_service.hybrid_pinecone_query(
            #     vector=dummy_vector,
            #     top_k=600,
            #     alpha=0.6,
            #     namespace="default_user"
            # )
            print("Pinecone index is available - hybrid query would work")
        except Exception as e:
            print(f"Error with hybrid query: {e}")
    else:
        print("Pinecone index not available - hybrid query would fail")

async def main():
    """Run all tests."""
    print("Starting Retrieval Service Tests")
    print("=" * 60)
    
    await test_service_health()
    await test_chunk_size_calculation()
    
    # Only run OpenAI-dependent tests if the client is available
    if retrieval_service.openai_client:
        await test_query_rewrite()
        await test_embedding_generation()
    else:
        print("\nSkipping OpenAI-dependent tests (client not available)")
    
    await test_hybrid_query_simulation()
    
    print("\n" + "=" * 60)
    print("All tests completed!")

if __name__ == "__main__":
    asyncio.run(main())