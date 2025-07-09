from pydantic import BaseModel, Field, EmailStr
from typing import Optional
from uuid import UUID, uuid4

class ConnectionBase(BaseModel):
    # Personal Information
    first_name: str
    last_name: str
    linkedin_url: Optional[str] = None
    email_address: Optional[EmailStr] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    followers: Optional[str] = None
    description: Optional[str] = None
    
    # Connection Information
    connected_on: Optional[str] = None
    
    # Current Company Information
    company: Optional[str] = None
    title: Optional[str] = None
    
    # Company Details
    company_size: Optional[str] = None
    company_name: Optional[str] = None
    company_website: Optional[str] = None
    company_phone: Optional[str] = None
    company_industry: Optional[str] = None
    company_industry_topics: Optional[str] = None
    company_description: Optional[str] = None
    company_address: Optional[str] = None
    company_city: Optional[str] = None
    company_state: Optional[str] = None
    company_country: Optional[str] = None
    company_revenue: Optional[str] = None
    company_latest_funding: Optional[str] = None
    company_linkedin: Optional[str] = None

class ConnectionInDB(ConnectionBase):
    id: UUID = Field(default_factory=uuid4)
    user_id: UUID

class ConnectionPublic(ConnectionBase):
    id: UUID