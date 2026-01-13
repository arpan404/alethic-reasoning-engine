"""Beta registration API schemas."""

from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, EmailStr, Field, field_validator
from api.schemas.common import TimestampMixin

# Type alias for beta registration statuses
BetaStatusType = Literal["pending", "approved", "rejected", "active", "inactive"]

VALID_BETA_STATUSES: tuple[str, ...] = ("pending", "approved", "rejected", "active", "inactive")


class BetaRegistrationRequest(BaseModel):
    """Schema for beta registration request."""

    email: EmailStr
    first_name: str = Field(..., min_length=1, max_length=100, description="User's first name")
    last_name: str = Field(..., min_length=1, max_length=100, description="User's last name")
    company_name: Optional[str] = Field(None, max_length=255, description="Optional company name")
    job_title: Optional[str] = Field(None, max_length=100, description="Optional job title")
    phone: Optional[str] = Field(None, max_length=20, description="Optional phone number")
    use_case: Optional[str] = Field(None, max_length=2000, description="Description of intended use")
    referral_source: Optional[str] = Field(None, max_length=100, description="How they found out about beta")
    newsletter_opt_in: bool = Field(default=False, description="Newsletter subscription consent")

    @field_validator("first_name", "last_name", mode="before")
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        """Strip whitespace from name fields."""
        if isinstance(v, str):
            return v.strip()
        return v

    @field_validator("phone", mode="before")
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        """Validate phone number format."""
        if v is None:
            return None
        phone = v.strip()
        if phone and not any(c.isdigit() for c in phone):
            raise ValueError("Phone must contain at least one digit")
        return phone


class BetaRegistrationResponse(TimestampMixin):
    """Schema for beta registration response."""

    id: int
    email: EmailStr
    first_name: str
    last_name: str
    company_name: Optional[str] = None
    job_title: Optional[str] = None
    phone: Optional[str] = None
    status: BetaStatusType
    use_case: Optional[str] = None
    referral_source: Optional[str] = None
    newsletter_opt_in: bool
    approved_at: Optional[datetime] = None

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 1,
                "email": "john.doe@example.com",
                "first_name": "John",
                "last_name": "Doe",
                "company_name": "Tech Corp",
                "job_title": "Hiring Manager",
                "phone": "+1-555-0123",
                "status": "pending",
                "use_case": "Streamline recruiting process",
                "referral_source": "Product Hunt",
                "newsletter_opt_in": True,
                "approved_at": None,
                "created_at": "2026-01-13T12:00:00Z",
                "updated_at": "2026-01-13T12:00:00Z",
            }
        }


class BetaRegistrationUpdate(BaseModel):
    """Schema for updating beta registration status."""

    status: BetaStatusType = Field(..., description="New registration status")
    approved_at: Optional[datetime] = Field(
        None, description="Timestamp when approved (auto-set if approving)"
    )

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> BetaStatusType:
        """Validate status is one of the allowed values."""
        if v not in VALID_BETA_STATUSES:
            raise ValueError(f"Status must be one of: {', '.join(VALID_BETA_STATUSES)}")
        return v  # type: ignore
