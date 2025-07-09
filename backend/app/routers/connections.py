from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query, BackgroundTasks
from typing import List, Dict
from uuid import UUID
import os
import tempfile

from app.services.auth_service import get_current_user
from app.services import connections_service
from app.services.embeddings_service import embeddings_service
from app.models.connection import ConnectionPublic
from app.core.db import get_database

router = APIRouter()

async def process_embeddings_background(csv_file_path: str, user_id: str):
    """
    Background task to process embeddings after file upload.
    
    Args:
        csv_file_path: Path to the uploaded CSV file
        user_id: User ID for namespace isolation
    """
    try:
        print(f"Starting background embedding processing for user {user_id}")
        result = await embeddings_service.process_profiles_and_upsert(
            csv_path=csv_file_path,
            user_id=user_id
        )
        print(f"Embedding processing completed: {result}")
        
        # Clean up temporary file
        if os.path.exists(csv_file_path):
            os.remove(csv_file_path)
            print(f"Cleaned up temporary file: {csv_file_path}")
            
    except Exception as e:
        print(f"Error in background embedding processing: {e}")
        # Clean up temporary file even on error
        if os.path.exists(csv_file_path):
            os.remove(csv_file_path)

@router.post("/connections/upload", status_code=status.HTTP_201_CREATED)
async def upload_connections(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database)
):
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload a CSV.")
    
    user_id = UUID(current_user["id"])
    
    # Process CSV upload to database first
    count = await connections_service.process_csv_upload(db, file, user_id)
    
    # Save uploaded file to temporary location for embedding processing
    # Reset file pointer to beginning
    await file.seek(0)
    file_content = await file.read()
    
    # Create temporary file
    with tempfile.NamedTemporaryFile(mode='wb', suffix='.csv', delete=False) as temp_file:
        temp_file.write(file_content)
        temp_file_path = temp_file.name
    
    # Add background task to process embeddings
    background_tasks.add_task(
        process_embeddings_background,
        csv_file_path=temp_file_path,
        user_id=str(user_id)
    )
    
    return {
        "message": f"Successfully uploaded and processed {count} connections. Embedding processing started in background."
    }

@router.get("/connections", response_model=List[ConnectionPublic])
async def get_connections(
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database),
    page: int = Query(1, ge=1),
    limit: int = Query(100, ge=1, le=1000)
):
    user_id = UUID(current_user["id"])
    connections = await connections_service.get_user_connections(db, user_id, page, limit)
    return connections

@router.get("/connections/count")
async def get_connections_count(
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database)
):
    user_id = UUID(current_user["id"])
    count = await connections_service.get_user_connections_count(db, user_id)
    return {"count": count}

@router.delete("/connections", status_code=status.HTTP_204_NO_CONTENT)
async def delete_connections(
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database)
):
    user_id = UUID(current_user["id"])
    await connections_service.delete_user_connections(db, user_id)
    return