from pydantic import BaseModel, Field
from uuid import UUID, uuid4
from datetime import datetime

class FavoriteConnectionBase(BaseModel):
    connection_id: UUID

class FavoriteConnectionCreate(FavoriteConnectionBase):
    pass

class FavoriteConnectionInDB(FavoriteConnectionBase):
    id: UUID = Field(default_factory=uuid4)
    user_id: UUID
    created_at: datetime = Field(default_factory=datetime.utcnow)

class FavoriteConnectionPublic(FavoriteConnectionBase):
    id: UUID
    created_at: datetime