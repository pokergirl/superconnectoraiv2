from pydantic import BaseModel, Field, EmailStr
from typing import Optional
from uuid import UUID, uuid4
from datetime import datetime
from enum import Enum

class AccessRequestFollowUpStatus(str, Enum):
    scheduled = "scheduled"
    sent = "sent"
    failed = "failed"
    cancelled = "cancelled"

class AccessRequestFollowUpBase(BaseModel):
    access_request_id: UUID
    user_email: EmailStr
    user_name: str
    scheduled_date: datetime
    follow_up_days: int = 14  # Default to 2 weeks

class AccessRequestFollowUpCreate(BaseModel):
    access_request_id: UUID
    user_email: EmailStr
    user_name: str
    follow_up_days: int = 14  # Default to 2 weeks
    scheduled_date: Optional[datetime] = None  # Will be calculated by service

class AccessRequestFollowUpInDB(AccessRequestFollowUpBase):
    id: UUID = Field(default_factory=uuid4)
    status: AccessRequestFollowUpStatus = AccessRequestFollowUpStatus.scheduled
    created_at: datetime = Field(default_factory=datetime.utcnow)
    sent_at: Optional[datetime] = None
    error_message: Optional[str] = None

class AccessRequestFollowUpPublic(AccessRequestFollowUpBase):
    id: UUID
    status: AccessRequestFollowUpStatus
    created_at: datetime
    sent_at: Optional[datetime] = None
    error_message: Optional[str] = None

class AccessRequestFollowUpUpdate(BaseModel):
    status: AccessRequestFollowUpStatus
    sent_at: Optional[datetime] = None
    error_message: Optional[str] = None
