from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query, BackgroundTasks
from typing import List, Dict, Optional
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
    count = await connections_service.process_and_store_connections(db, file, user_id)
    
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

@router.post("/connections/ingest", status_code=status.HTTP_201_CREATED)
async def ingest_connections(
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database)
):
    user_id = UUID(current_user["id"])
    
    # Construct path to data.csv, assuming it's in the backend directory
    # This makes the path relative to this file's location
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    csv_file_path = os.path.join(base_dir, "updated_connections.csv")

    if not os.path.exists(csv_file_path):
        raise HTTPException(status_code=404, detail=f"File not found at {csv_file_path}")

    # Process CSV upload to database first
    with open(csv_file_path, 'rb') as f:
        # We need to pass a file-like object to the service
        # The service expects an UploadFile, so we create a temporary one
        upload_file = UploadFile(filename="data.csv", file=f)
        count = await connections_service.process_and_store_connections(db, upload_file, user_id)

    # For the background task, we need a temporary copy of the file because the original file handle will be closed.
    with tempfile.NamedTemporaryFile(mode='wb', suffix='.csv', delete=False) as temp_file:
        with open(csv_file_path, 'rb') as original_file:
            temp_file.write(original_file.read())
        temp_file_path = temp_file.name

    # Add background task to process embeddings
    background_tasks.add_task(
        process_embeddings_background,
        csv_file_path=temp_file_path,
        user_id=str(user_id)
    )
    
    return {
        "message": f"Successfully ingested and processed {count} connections. Embedding processing started in background."
    }
@router.get("/connections", response_model=List[ConnectionPublic])
async def get_connections(
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database),
    page: int = Query(1, ge=1),
    limit: int = Query(100, ge=1, le=1000),
    min_rating: Optional[int] = Query(None, ge=1, le=10)
):
    user_id = UUID(current_user["id"])
    connections = await connections_service.get_user_connections(db, user_id, page, limit, min_rating)
    return connections

@router.get("/connections/count")
async def get_connections_count(
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database)
):
    user_id = current_user.id
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