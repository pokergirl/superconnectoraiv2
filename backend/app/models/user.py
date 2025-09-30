from pydantic import BaseModel, Field, EmailStr
from typing import Optional
from uuid import UUID, uuid4
from datetime import datetime
from enum import Enum

class UserRole(str, Enum):
    admin = "admin"
    user = "user"

class UserStatus(str, Enum):
    active = "active"
    inactive = "inactive"
    suspended = "suspended"

class UserBase(BaseModel):
    email: EmailStr

class UserCreate(UserBase):
    password: str
    invitation_code: Optional[str] = None  # Required for registration

class UserInDB(UserBase):
    id: UUID = Field(default_factory=uuid4)
    hashed_password: str
    role: UserRole = UserRole.user
    status: UserStatus = UserStatus.active
    is_premium: bool = False  # Premium membership status
    invitation_id: Optional[UUID] = None  # Link to the invitation used
    must_change_password: bool = False  # Flag to force password reset on next login
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = None
    persist_search_results: bool = True

class UserPublic(UserBase):
    id: UUID
    role: UserRole
    status: UserStatus
    is_premium: bool = False  # Premium membership status
    must_change_password: bool = False  # Flag to force password reset on next login
    created_at: datetime
    last_login: Optional[datetime] = None

class UserUpdate(BaseModel):
    role: Optional[UserRole] = None
    status: Optional[UserStatus] = None
    is_premium: Optional[bool] = None  # Allow updating premium status
    must_change_password: Optional[bool] = None  # Allow updating password change requirement
    last_login: Optional[datetime] = None

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None

class AdminUserCreate(BaseModel):
    email: EmailStr

class UserWithOTP(UserPublic):
    otp: str

class PasswordResetToken(BaseModel):
    reset_token: str
    token_type: str = "password_reset"

class PasswordResetRequest(BaseModel):
    new_password: str
    reset_token: str