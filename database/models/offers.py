"""
Offers Module

Offer management with approval workflows, negotiations, and e-signatures.
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
    Float,
    Enum as SQLEnum,
    Index,
    UniqueConstraint,
)
from database.engine import Base
from database.security import ComplianceMixin, audit_changes
from database.security import (
    compliance_column,
    DataSensitivity,
    EncryptionType,
    DataRetentionPeriod,
)
from datetime import datetime
from enum import Enum as PyEnum
from typing import Any


# ==================== Enums ===================== #
class OfferStatus(str, PyEnum):
    """Status of job offer."""

    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    SENT = "sent"
    VIEWED = "viewed"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    EXPIRED = "expired"
    WITHDRAWN = "withdrawn"
    NEGOTIATING = "negotiating"


class ApprovalStatus(str, PyEnum):
    """Status of offer approval."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    SKIPPED = "skipped"


class NegotiationStatus(str, PyEnum):
    """Status of offer negotiation."""

    PENDING = "pending"
    COUNTERED = "countered"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EXPIRED = "expired"


class CompensationType(str, PyEnum):
    """Type of compensation."""

    SALARY = "salary"
    HOURLY = "hourly"
    CONTRACT = "contract"
    COMMISSION = "commission"


# ==================== Offer Model ===================== #
@audit_changes
class Offer(Base, ComplianceMixin):
    """
    Job offer with compensation, benefits, and terms.
    """

    __tablename__ = "offers"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )
    application_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("applications.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    job_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    candidate_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("candidates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    organization_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Status
    status: Mapped[OfferStatus] = mapped_column(
        SQLEnum(OfferStatus, native_enum=False, length=50),
        nullable=False,
        default=OfferStatus.DRAFT,
        index=True,
    )
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)

    # Compensation
    compensation_type: Mapped[CompensationType] = mapped_column(
        SQLEnum(CompensationType, native_enum=False, length=50),
        nullable=False,
        default=CompensationType.SALARY,
    )
    base_salary: Mapped[int | None] = mapped_column(
        BigInteger,
        info=compliance_column(
            sensitivity=DataSensitivity.CONFIDENTIAL,
            retention_period=DataRetentionPeriod.YEARS_7,
        ),
    )  # In cents
    salary_currency: Mapped[str] = mapped_column(
        String(10), nullable=False, default="USD"
    )
    salary_period: Mapped[str | None] = mapped_column(String(20))  # yearly, monthly, hourly

    # Bonus & equity
    signing_bonus: Mapped[int | None] = mapped_column(BigInteger)
    annual_bonus_target: Mapped[float | None] = mapped_column(Float)  # Percentage
    equity_shares: Mapped[int | None] = mapped_column(BigInteger)
    equity_type: Mapped[str | None] = mapped_column(String(50))  # options, RSUs
    equity_vesting_schedule: Mapped[str | None] = mapped_column(String(100))

    # Benefits
    benefits_summary: Mapped[str | None] = mapped_column(Text)
    benefits_details: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    pto_days: Mapped[int | None] = mapped_column(BigInteger)
    remote_policy: Mapped[str | None] = mapped_column(String(100))

    # Terms
    job_title: Mapped[str] = mapped_column(String(255), nullable=False)
    department: Mapped[str | None] = mapped_column(String(255))
    reports_to: Mapped[str | None] = mapped_column(String(255))
    start_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    location: Mapped[str | None] = mapped_column(String(500))

    # Offer letter
    offer_letter_content: Mapped[str | None] = mapped_column(Text)
    offer_letter_file_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("files.id")
    )
    template_id: Mapped[int | None] = mapped_column(BigInteger)

    # Expiration
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # E-signature
    signature_requested_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    signed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    signature_file_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("files.id")
    )
    esignature_provider: Mapped[str | None] = mapped_column(String(50))
    esignature_document_id: Mapped[str | None] = mapped_column(String(255))

    # Response
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    decline_reason: Mapped[str | None] = mapped_column(Text)

    # Timestamps
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    viewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
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
    approvals: Mapped[list["OfferApproval"]] = relationship(
        "OfferApproval", back_populates="offer", cascade="all, delete-orphan"
    )
    negotiations: Mapped[list["OfferNegotiation"]] = relationship(
        "OfferNegotiation", back_populates="offer", cascade="all, delete-orphan"
    )

    # Indexes
    __table_args__ = (
        Index("idx_offer_app_status", "application_id", "status"),
        Index("idx_offer_org", "organization_id", "status"),
    )


# ==================== OfferApproval Model ===================== #
@audit_changes
class OfferApproval(Base):
    """
    Approval workflow for offers.
    """

    __tablename__ = "offer_approvals"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )
    offer_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("offers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    approver_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Approval details
    approval_order: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    status: Mapped[ApprovalStatus] = mapped_column(
        SQLEnum(ApprovalStatus, native_enum=False, length=50),
        nullable=False,
        default=ApprovalStatus.PENDING,
    )
    comments: Mapped[str | None] = mapped_column(Text)

    # Timing
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    due_by: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Reminder
    reminder_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Relationships
    offer: Mapped["Offer"] = relationship("Offer", back_populates="approvals")

    # Unique constraint
    __table_args__ = (
        UniqueConstraint("offer_id", "approver_id", name="uq_offer_approver"),
    )


# ==================== OfferNegotiation Model ===================== #
@audit_changes
class OfferNegotiation(Base, ComplianceMixin):
    """
    Counter-offer and negotiation history.
    """

    __tablename__ = "offer_negotiations"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )
    offer_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("offers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Negotiation round
    round_number: Mapped[int] = mapped_column(BigInteger, nullable=False)
    initiated_by: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # candidate, employer

    # Counter terms
    status: Mapped[NegotiationStatus] = mapped_column(
        SQLEnum(NegotiationStatus, native_enum=False, length=50),
        nullable=False,
        default=NegotiationStatus.PENDING,
    )
    requested_salary: Mapped[int | None] = mapped_column(
        BigInteger,
        info=compliance_column(
            sensitivity=DataSensitivity.CONFIDENTIAL,
        ),
    )
    requested_signing_bonus: Mapped[int | None] = mapped_column(BigInteger)
    requested_equity: Mapped[int | None] = mapped_column(BigInteger)
    requested_start_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    other_requests: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    message: Mapped[str | None] = mapped_column(Text)

    # Response
    response_message: Mapped[str | None] = mapped_column(Text)
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    responded_by: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id")
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Relationships
    offer: Mapped["Offer"] = relationship("Offer", back_populates="negotiations")
