"""Candidate-related Pydantic schemas."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, HttpUrl

from api.schemas.common import TimestampMixin


class CandidateBase(BaseModel):
    """Base candidate schema."""

    email: EmailStr
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    phone: Optional[str] = None
    location: Optional[str] = None
    linkedin_url: Optional[HttpUrl] = None
    github_url: Optional[HttpUrl] = None
    portfolio_url: Optional[HttpUrl] = None


class CandidateCreate(CandidateBase):
    """Schema for creating a candidate."""

    resume_url: Optional[str] = None


class CandidateUpdate(BaseModel):
    """Schema for updating a candidate."""

    email: Optional[EmailStr] = None
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    phone: Optional[str] = None
    location: Optional[str] = None
    linkedin_url: Optional[HttpUrl] = None
    github_url: Optional[HttpUrl] = None
    portfolio_url: Optional[HttpUrl] = None


class CandidateResponse(CandidateBase, TimestampMixin):
    """Schema for candidate response."""

    id: str
    organization_id: str
    resume_parsed: bool = False
    embedding_generated: bool = False

    class Config:
        from_attributes = True
