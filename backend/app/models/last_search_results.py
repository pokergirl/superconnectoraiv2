from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict, Any, List
from datetime import datetime
import uuid

class LastSearchResultsBase(BaseModel):
    query: str
    filters: Optional[Dict[str, Any]] = None
    results: List[Dict[str, Any]]  # Store the actual search results
    results_count: int
    page: int = 1
    page_size: int = 20

class LastSearchResultsCreate(LastSearchResultsBase):
    pass

class LastSearchResultsInDB(LastSearchResultsBase):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), alias="_id")
    user_id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(populate_by_name=True)

class LastSearchResultsPublic(LastSearchResultsBase):
    id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)