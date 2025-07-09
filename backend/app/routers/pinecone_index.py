from fastapi import APIRouter, HTTPException
from typing import Dict, Any
from app.services.pinecone_index_service import pinecone_index_service

router = APIRouter(prefix="/api/v1/pinecone", tags=["pinecone"])


@router.post("/index/setup", response_model=Dict[str, Any])
async def setup_pinecone_index():
    """
    Set up the Pinecone index with the required configuration.
    This endpoint is idempotent - it will not create the index if it already exists.
    
    Returns:
        Dictionary containing setup result and index information
    """
    try:
        result = pinecone_index_service.setup_index()
        
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result["message"])
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to setup Pinecone index: {str(e)}")


@router.get("/index/info", response_model=Dict[str, Any])
async def get_index_info():
    """
    Get information about the current Pinecone index.
    
    Returns:
        Dictionary containing index information or None if index doesn't exist
    """
    try:
        if not pinecone_index_service.index_exists():
            raise HTTPException(status_code=404, detail="Pinecone index does not exist")
        
        index_info = pinecone_index_service.get_index_info()
        
        if not index_info:
            raise HTTPException(status_code=404, detail="Could not retrieve index information")
        
        return {
            "success": True,
            "index_info": index_info
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get index info: {str(e)}")


@router.get("/index/exists", response_model=Dict[str, Any])
async def check_index_exists():
    """
    Check if the Pinecone index exists.
    
    Returns:
        Dictionary indicating whether the index exists
    """
    try:
        exists = pinecone_index_service.index_exists()
        
        return {
            "success": True,
            "exists": exists,
            "index_name": pinecone_index_service.index_name
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to check index existence: {str(e)}")


@router.delete("/index", response_model=Dict[str, Any])
async def delete_pinecone_index():
    """
    Delete the Pinecone index. Use with caution!
    This will permanently delete all stored embeddings.
    
    Returns:
        Dictionary containing deletion result
    """
    try:
        result = pinecone_index_service.delete_index()
        
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result["message"])
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete Pinecone index: {str(e)}")