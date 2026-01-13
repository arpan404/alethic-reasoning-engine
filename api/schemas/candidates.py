"""Candidate-related Pydantic schemas."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, HttpUrl, field_validator

from api.schemas.common import TimestampMixin


class CandidateBase(BaseModel):
    """Base candidate schema."""

    email: EmailStr
    first_name: str = Field(min_length=1, max_length=100, description="Candidate's first name")
    last_name: str = Field(min_length=1, max_length=100, description="Candidate's last name")
    phone: Optional[str] = Field(None, max_length=20, description="Contact phone number")
    location: Optional[str] = Field(None, max_length=255, description="Geographic location")
    linkedin_url: Optional[HttpUrl] = Field(None, description="LinkedIn profile URL")
    github_url: Optional[HttpUrl] = Field(None, description="GitHub profile URL")
    portfolio_url: Optional[HttpUrl] = Field(None, description="Portfolio website URL")

    @field_validator("first_name", "last_name", mode="before")
    @classmethod
    def strip_names(cls, v: str) -> str:
        """Strip whitespace from name fields."""
        if isinstance(v, str):
            return v.strip()
        return v


class CandidateCreate(CandidateBase):
    """Schema for creating a candidate."""

    resume_url: Optional[str] = Field(None, max_length=2048, description="URL to candidate's resume")


class CandidateUpdate(BaseModel):
    """Schema for updating a candidate."""

    email: Optional[EmailStr] = Field(None, description="Candidate email")
    first_name: Optional[str] = Field(None, min_length=1, max_length=100, description="First name")
    last_name: Optional[str] = Field(None, min_length=1, max_length=100, description="Last name")
    phone: Optional[str] = Field(None, max_length=20, description="Phone number")
    location: Optional[str] = Field(None, max_length=255, description="Location")
    linkedin_url: Optional[HttpUrl] = Field(None, description="LinkedIn URL")
    github_url: Optional[HttpUrl] = Field(None, description="GitHub URL")
    portfolio_url: Optional[HttpUrl] = Field(None, description="Portfolio URL")


class CandidateResponse(CandidateBase, TimestampMixin):
    """Schema for candidate response."""

    id: str = Field(description="Unique candidate identifier")
    organization_id: str = Field(description="Organization this candidate belongs to")
    resume_parsed: bool = Field(default=False, description="Whether resume has been parsed")
    embedding_generated: bool = Field(default=False, description="Whether embeddings have been generated")

    class Config:
        from_attributes = True
