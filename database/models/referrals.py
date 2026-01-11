"""
Referrals Module

Employee referral program with bonus tracking.
"""

from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import (
    String,
    Boolean,
    ForeignKey,
    BigInteger,
    DateTime,
    func,
    Text,
    JSON,
    Enum as SQLEnum,
    Index,
    UniqueConstraint,
)
from database.engine import Base
from database.security import audit_changes
from datetime import datetime
from enum import Enum as PyEnum
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from database.models.candidates import Candidate
    from database.models.jobs import Job
    from database.models.organizations import Organization


# ==================== Enums ===================== #
class ReferralStatus(str, PyEnum):
    """Status of referral."""

    SUBMITTED = "submitted"
    REVIEWING = "reviewing"
    INTERVIEWING = "interviewing"
    OFFERED = "offered"
    HIRED = "hired"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"
    DUPLICATE = "duplicate"


class BonusStatus(str, PyEnum):
    """Status of referral bonus."""

    PENDING = "pending"
    ELIGIBLE = "eligible"
    PROCESSING = "processing"
    PAID = "paid"
    CANCELLED = "cancelled"
    FORFEITED = "forfeited"


class BonusTier(str, PyEnum):
    """Bonus tier levels."""

    STANDARD = "standard"
    CRITICAL_ROLE = "critical_role"
    EXECUTIVE = "executive"
    HARD_TO_FILL = "hard_to_fill"
    CUSTOM = "custom"


# ==================== ReferralProgram Model ===================== #
@audit_changes
class ReferralProgram(Base):
    """
    Referral program settings per organization.
    """

    __tablename__ = "referral_programs"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )
    organization_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    # Program info
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Bonus structure
    default_bonus_amount: Mapped[int] = mapped_column(
        BigInteger, nullable=False
    )  # In cents
    bonus_currency: Mapped[str] = mapped_column(
        String(10), nullable=False, default="USD"
    )
    bonus_tiers: Mapped[dict[str, int] | None] = mapped_column(
        JSON
    )  # {tier: amount}

    # Eligibility rules
    eligible_referrer_roles: Mapped[list[str] | None] = mapped_column(JSON)
    excluded_departments: Mapped[list[int] | None] = mapped_column(JSON)
    min_tenure_days: Mapped[int | None] = mapped_column(BigInteger)

    # Payout rules
    payout_after_days: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=90
    )
    require_referrer_employed: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    require_hire_employed: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )

    # Limits
    max_referrals_per_employee: Mapped[int | None] = mapped_column(BigInteger)
    max_bonus_per_year: Mapped[int | None] = mapped_column(BigInteger)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    created_by: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id"), nullable=False
    )

    # Relationships
    referrals: Mapped[list["Referral"]] = relationship(
        "Referral", back_populates="program", cascade="all, delete-orphan"
    )
    organization: Mapped["Organization"] = relationship(
        "Organization", back_populates="referral_program"
    )

    # Indexes
    __table_args__ = (
        Index("idx_referral_program_active", "is_active"),
        # GIN indexes for JSON arrays
        Index(
            "idx_referral_program_tiers_gin",
            "bonus_tiers",
            postgresql_using="gin"
        ),
    )


# ==================== Referral Model ===================== #
@audit_changes
class Referral(Base):
    """
    Employee referral for a candidate.
    """

    __tablename__ = "referrals"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )
    program_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("referral_programs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    organization_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Referrer
    referrer_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    referrer_email: Mapped[str | None] = mapped_column(String(255))

    # Candidate
    candidate_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("candidates.id", ondelete="SET NULL"),
        index=True,
    )
    candidate_email: Mapped[str] = mapped_column(String(255), nullable=False)
    candidate_name: Mapped[str] = mapped_column(String(255), nullable=False)
    candidate_phone: Mapped[str | None] = mapped_column(String(50))
    candidate_linkedin: Mapped[str | None] = mapped_column(String(500))

    # Job
    job_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("jobs.id", ondelete="SET NULL"),
        index=True,
    )

    # Application
    application_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("applications.id", ondelete="SET NULL"),
        index=True,
    )

    # Referral details
    relationship_to_candidate: Mapped[str | None] = mapped_column(String(100))
    how_long_known: Mapped[str | None] = mapped_column(String(100))
    referral_reason: Mapped[str | None] = mapped_column(Text)
    additional_notes: Mapped[str | None] = mapped_column(Text)

    # Resume
    resume_file_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("files.id")
    )

    # Status
    status: Mapped[ReferralStatus] = mapped_column(
        SQLEnum(ReferralStatus, native_enum=False, length=50),
        nullable=False,
        default=ReferralStatus.SUBMITTED,
        index=True,
    )

    # Bonus
    bonus_tier: Mapped[BonusTier] = mapped_column(
        SQLEnum(BonusTier, native_enum=False, length=50),
        nullable=False,
        default=BonusTier.STANDARD,
    )
    bonus_eligible: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )

    # Hire details
    hired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    start_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Timestamps
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    program: Mapped["ReferralProgram"] = relationship(
        "ReferralProgram", back_populates="referrals"
    )
    candidate: Mapped["Candidate | None"] = relationship(
        "Candidate", back_populates="referrals_received"
    )
    job: Mapped["Job | None"] = relationship(
        "Job", back_populates="referrals"
    )
    bonuses: Mapped[list["ReferralBonus"]] = relationship(
        "ReferralBonus", back_populates="referral", cascade="all, delete-orphan"
    )

    # Indexes and constraints
    __table_args__ = (
        UniqueConstraint(
            "organization_id", "candidate_email", "job_id", name="uq_referral_candidate_job"
        ),
        Index("idx_referral_status", "organization_id", "status"),
        Index("idx_referral_job", "job_id"),
        Index("idx_referral_hired", "hired_at"),
        Index("idx_referral_bonus_eligible", "bonus_eligible"),
        Index("idx_referral_tier", "bonus_tier"),
        # Partial index for pending referrals
        Index(
            "idx_referral_pending",
            "organization_id",
            "submitted_at",
            postgresql_where="status IN ('submitted', 'reviewing')"
        ),
    )


# ==================== ReferralBonus Model ===================== #
@audit_changes
class ReferralBonus(Base):
    """
    Bonus payout tracking for referrals.
    """

    __tablename__ = "referral_bonuses"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )
    referral_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("referrals.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    referrer_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Amount
    amount: Mapped[int] = mapped_column(BigInteger, nullable=False)  # In cents
    currency: Mapped[str] = mapped_column(String(10), nullable=False, default="USD")
    bonus_tier: Mapped[BonusTier] = mapped_column(
        SQLEnum(BonusTier, native_enum=False, length=50),
        nullable=False,
    )

    # Status
    status: Mapped[BonusStatus] = mapped_column(
        SQLEnum(BonusStatus, native_enum=False, length=50),
        nullable=False,
        default=BonusStatus.PENDING,
        index=True,
    )

    # Eligibility
    eligible_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    eligibility_check_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    eligibility_notes: Mapped[str | None] = mapped_column(Text)

    # Payout
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    payment_reference: Mapped[str | None] = mapped_column(String(255))
    payment_method: Mapped[str | None] = mapped_column(String(50))

    # Forfeiture
    forfeited_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    forfeit_reason: Mapped[str | None] = mapped_column(Text)

    # Approved by
    approved_by: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id")
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    referral: Mapped["Referral"] = relationship(
        "Referral", back_populates="bonuses"
    )

    # Indexes
    __table_args__ = (
        Index("idx_referral_bonus_status", "status"),
        Index("idx_referral_bonus_eligible", "eligible_date"),
        Index("idx_referral_bonus_paid", "paid_at"),
        # Partial index for pending bonuses
        Index(
            "idx_referral_bonus_pending",
            "referral_id",
            "eligible_date",
            postgresql_where="status IN ('pending', 'eligible', 'processing')"
        ),
    )
