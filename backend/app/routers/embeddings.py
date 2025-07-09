from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, Optional
from pydantic import BaseModel
from app.services.embeddings_service import embeddings_service
from app.services.auth_service import get_current_user
from app.models.user import UserInDB

router = APIRouter()

class ProfileTextRequest(BaseModel):
    name: str
    headline: str = ""
    experience: str = ""
    skills: str = ""
    location: str = ""

class ProcessProfilesRequest(BaseModel):
    csv_path: Optional[str] = "Connections.csv"
    chunk_size: Optional[int] = 100

class EmbeddingResponse(BaseModel):
    embedding: list[float]
    canonical_text: str

class ProcessingResponse(BaseModel):
    total_rows: int
    processed_count: int
    error_count: int
    vectors_upserted: int
    chunks_processed: int
    namespace: str
    message: str

@router.post("/canonicalize", response_model=Dict[str, str])
async def canonicalize_profile_text(request: ProfileTextRequest):
    """
    Canonicalize profile text from individual fields.
    """
    try:
        canonical_text = embeddings_service.canonicalize_profile_text(
            name=request.name,
            headline=request.headline,
            experience=request.experience,
            skills=request.skills,
            location=request.location
        )
        
        return {
            "canonical_text": canonical_text,
            "original_fields": {
                "name": request.name,
                "headline": request.headline,
                "experience": request.experience,
                "skills": request.skills,
                "location": request.location
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error canonicalizing text: {str(e)}")

@router.post("/generate", response_model=EmbeddingResponse)
async def generate_embedding(request: ProfileTextRequest):
    """
    Generate embedding for profile text.
    """
    try:
        # Canonicalize the text first
        canonical_text = embeddings_service.canonicalize_profile_text(
            name=request.name,
            headline=request.headline,
            experience=request.experience,
            skills=request.skills,
            location=request.location
        )
        
        # Generate embedding
        embedding = await embeddings_service.generate_embedding(canonical_text)
        
        return EmbeddingResponse(
            embedding=embedding,
            canonical_text=canonical_text
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating embedding: {str(e)}")

@router.get("/cached/{profile_id}")
async def get_cached_embedding(profile_id: str):
    """
    Get cached embedding for a profile.
    """
    try:
        embedding = await embeddings_service.get_cached_embedding(profile_id)
        
        if embedding is None:
            raise HTTPException(status_code=404, detail="Cached embedding not found")
        
        return {
            "profile_id": profile_id,
            "embedding": embedding,
            "cached": True
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving cached embedding: {str(e)}")

@router.post("/process-profiles", response_model=ProcessingResponse)
async def process_profiles(
    request: ProcessProfilesRequest,
    current_user: UserInDB = Depends(get_current_user)
):
    """
    Process all profiles from CSV, generate embeddings, and upsert to Pinecone.
    Requires authentication to use user ID as namespace.
    """
    try:
        # Use the authenticated user's ID as the namespace
        user_id = str(current_user.id)
        
        result = await embeddings_service.process_profiles_and_upsert(
            csv_path=request.csv_path,
            user_id=user_id,
            chunk_size=request.chunk_size
        )
        
        return ProcessingResponse(
            total_rows=result["total_rows"],
            processed_count=result["processed_count"],
            error_count=result["error_count"],
            vectors_upserted=result["vectors_upserted"],
            chunks_processed=result["chunks_processed"],
            namespace=result["namespace"],
            message=f"Successfully processed {result['processed_count']} profiles in {result['chunks_processed']} chunks and upserted {result['vectors_upserted']} vectors to Pinecone"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing profiles: {str(e)}")

@router.post("/batch-upsert")
async def batch_upsert_vectors(
    vectors_data: Dict[str, Any],
    current_user: UserInDB = Depends(get_current_user)
):
    """
    Perform batch upsert to Pinecone with custom vector data.
    Expects: {"vectors": [(id, vector, metadata), ...]}
    """
    try:
        vectors = vectors_data.get("vectors", [])
        if not vectors:
            raise HTTPException(status_code=400, detail="No vectors provided")
        
        # Use the authenticated user's ID as the namespace
        user_id = str(current_user.id)
        
        # Validate vector format
        for i, vector_data in enumerate(vectors):
            if not isinstance(vector_data, (list, tuple)) or len(vector_data) != 3:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Vector {i} must be a tuple/list of (id, vector, metadata)"
                )
        
        embeddings_service.batch_upsert_to_pinecone(vectors, namespace=user_id)
        
        return {
            "message": f"Successfully upserted {len(vectors)} vectors to namespace {user_id}",
            "vectors_count": len(vectors),
            "namespace": user_id
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error upserting vectors: {str(e)}")

@router.get("/health")
async def embeddings_health_check():
    """
    Health check for embeddings service.
    """
    try:
        # Test OpenAI connection
        test_embedding = await embeddings_service.generate_embedding("test")
        
        return {
            "status": "healthy",
            "openai_connection": "ok",
            "embedding_dimension": len(test_embedding),
            "model": embeddings_service.embedding_model
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Embeddings service unhealthy: {str(e)}")