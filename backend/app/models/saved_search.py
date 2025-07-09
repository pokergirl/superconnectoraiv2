from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID, uuid4
from datetime import datetime

class SavedSearchBase(BaseModel):
    name: str
    query: str
    filters: Optional[dict] = None

class SavedSearchCreate(SavedSearchBase):
    pass

class SavedSearchInDB(SavedSearchBase):
    id: UUID = Field(default_factory=uuid4)
    user_id: UUID
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class SavedSearchPublic(SavedSearchBase):
    id: UUID
    created_at: datetime
    updated_at: datetime