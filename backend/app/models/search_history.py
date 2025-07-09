from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID, uuid4
from datetime import datetime

class SearchHistoryBase(BaseModel):
    query: str
    filters: Optional[dict] = None
    results_count: int = 0

class SearchHistoryCreate(SearchHistoryBase):
    pass

class SearchHistoryInDB(SearchHistoryBase):
    id: UUID = Field(default_factory=uuid4)
    user_id: UUID
    searched_at: datetime = Field(default_factory=datetime.utcnow)

class SearchHistoryPublic(SearchHistoryBase):
    id: UUID
    searched_at: datetime