"""Beta registration model for early access program."""

from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, DateTime, Boolean, Text, func, Index
from database.engine import Base
from database.security import ComplianceMixin, audit_changes
from datetime import datetime
from enum import Enum as PyEnum


class BetaStatus(str, PyEnum):
    """Status of beta registration."""
    PENDING = "pending"  # Awaiting review
    APPROVED = "approved"  # Approved for beta access
    REJECTED = "rejected"  # Not approved
    ACTIVE = "active"  # Currently using beta features
    INACTIVE = "inactive"  # No longer using beta


@audit_changes
class BetaRegistration(Base, ComplianceMixin):
    """
    User beta program registration with status tracking.
    """

    __tablename__: str = "beta_registrations"
    id: Mapped[int] = mapped_column(primary_key=True, nullable=False, autoincrement=True)
    email: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    company_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    job_title: Mapped[str | None] = mapped_column(String(100), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    
    # Beta program details
    status: Mapped[BetaStatus] = mapped_column(
        String(20), 
        default=BetaStatus.PENDING,
        nullable=False,
        index=True
    )
    use_case: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Description of how they plan to use the product"
    )
    referral_source: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="How they heard about the beta program"
    )
    newsletter_opt_in: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False
    )
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )
    approved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    # Indices for common queries
    __table_args__ = (
        Index("idx_beta_status_created", "status", "created_at"),
        Index("idx_beta_email_status", "email", "status"),
    )
