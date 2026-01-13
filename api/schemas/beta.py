"""Beta registration API schemas."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field
from api.schemas.common import TimestampMixin


class BetaRegistrationRequest(BaseModel):
    """Schema for beta registration request."""

    email: EmailStr
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    company_name: Optional[str] = Field(None, max_length=255)
    job_title: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)
    use_case: Optional[str] = Field(None, max_length=2000)
    referral_source: Optional[str] = Field(None, max_length=100)
    newsletter_opt_in: bool = Field(default=False)


class BetaRegistrationResponse(TimestampMixin):
    """Schema for beta registration response."""

    id: int
    email: EmailStr
    first_name: str
    last_name: str
    company_name: Optional[str]
    job_title: Optional[str]
    phone: Optional[str]
    status: str
    use_case: Optional[str]
    referral_source: Optional[str]
    newsletter_opt_in: bool
    approved_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class BetaRegistrationUpdate(BaseModel):
    """Schema for updating beta registration status."""

    status: str = Field(..., min_length=1)
    approved_at: Optional[datetime] = None
