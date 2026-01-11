"""
Background Checks Module

Integration with background check providers (Checkr, etc.).
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
class BackgroundCheckProviderType(str, PyEnum):
    """Background check providers."""

    CHECKR = "checkr"
    STERLING = "sterling"
    GOODHIRE = "goodhire"
    HIRERIGHT = "hireright"
    CERTN = "certn"
    ACCURATE = "accurate"
    CUSTOM = "custom"


class CheckType(str, PyEnum):
    """Types of background checks."""

    CRIMINAL = "criminal"
    EMPLOYMENT = "employment"
    EDUCATION = "education"
    CREDIT = "credit"
    DRUG = "drug"
    REFERENCE = "reference"
    DRIVING = "driving"
    PROFESSIONAL_LICENSE = "professional_license"
    SOCIAL_MEDIA = "social_media"
    IDENTITY = "identity"
    GLOBAL_WATCHLIST = "global_watchlist"


class CheckStatus(str, PyEnum):
    """Status of background check."""

    PENDING = "pending"
    INITIATED = "initiated"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    DISPUTE = "dispute"


class CheckResult(str, PyEnum):
    """Result of background check."""

    CLEAR = "clear"
    CONSIDER = "consider"
    ADVERSE = "adverse"
    PENDING_REVIEW = "pending_review"
    UNABLE_TO_VERIFY = "unable_to_verify"


# ==================== BackgroundCheckProvider Model ===================== #
@audit_changes
class BackgroundCheckProvider(Base, ComplianceMixin):
    """
    Configuration for background check provider per organization.
    """

    __tablename__ = "background_check_providers"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )
    organization_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Provider info
    provider_type: Mapped[BackgroundCheckProviderType] = mapped_column(
        SQLEnum(BackgroundCheckProviderType, native_enum=False, length=50),
        nullable=False,
    )
    provider_name: Mapped[str] = mapped_column(String(255), nullable=False)

    # API credentials (encrypted)
    api_key: Mapped[str | None] = mapped_column(
        Text,
        info=compliance_column(
            sensitivity=DataSensitivity.RESTRICTED,
            encryption=EncryptionType.AT_REST,
            mask_in_logs=True,
            soc2_critical=True,
        ),
    )
    api_secret: Mapped[str | None] = mapped_column(
        Text,
        info=compliance_column(
            sensitivity=DataSensitivity.RESTRICTED,
            encryption=EncryptionType.AT_REST,
            mask_in_logs=True,
            soc2_critical=True,
        ),
    )
    account_id: Mapped[str | None] = mapped_column(String(255))

    # Webhook
    webhook_url: Mapped[str | None] = mapped_column(String(1000))
    webhook_secret: Mapped[str | None] = mapped_column(
        String(255),
        info=compliance_column(
            sensitivity=DataSensitivity.RESTRICTED,
            encryption=EncryptionType.AT_REST,
            mask_in_logs=True,
        ),
    )

    # Packages/products
    available_packages: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON)
    default_package_id: Mapped[str | None] = mapped_column(String(100))

    # Settings
    auto_initiate: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    auto_initiate_stage_id: Mapped[int | None] = mapped_column(
        BigInteger
    )  # Pipeline stage

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)

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
    checks: Mapped[list["BackgroundCheck"]] = relationship(
        "BackgroundCheck", back_populates="provider", cascade="all, delete-orphan"
    )

    # Unique constraint
    __table_args__ = (
        UniqueConstraint(
            "organization_id", "provider_type", name="uq_org_bg_provider"
        ),
    )


# ==================== BackgroundCheck Model ===================== #
@audit_changes
class BackgroundCheck(Base, ComplianceMixin):
    """
    Individual background check request and result.
    """

    __tablename__ = "background_checks"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )
    provider_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("background_check_providers.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    application_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("applications.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    candidate_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("candidates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # External reference
    external_check_id: Mapped[str | None] = mapped_column(
        String(255), index=True
    )
    external_report_url: Mapped[str | None] = mapped_column(String(1000))
    package_id: Mapped[str | None] = mapped_column(String(100))
    package_name: Mapped[str | None] = mapped_column(String(255))

    # Check types
    check_types: Mapped[list[str]] = mapped_column(JSON, nullable=False)

    # Status
    status: Mapped[CheckStatus] = mapped_column(
        SQLEnum(CheckStatus, native_enum=False, length=50),
        nullable=False,
        default=CheckStatus.PENDING,
        index=True,
    )
    result: Mapped[CheckResult | None] = mapped_column(
        SQLEnum(CheckResult, native_enum=False, length=50)
    )

    # Results by check type
    check_results: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        info=compliance_column(
            sensitivity=DataSensitivity.HIGHLY_SENSITIVE,
            retention_period=DataRetentionPeriod.YEARS_7,
        ),
    )

    # Candidate consent
    consent_given: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    consent_given_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    consent_document_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("files.id")
    )

    # Adverse action
    adverse_action_initiated: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    adverse_action_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    pre_adverse_notice_sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    final_adverse_notice_sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )

    # Cost
    cost_cents: Mapped[int | None] = mapped_column(BigInteger)

    # Timing
    initiated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Notes
    internal_notes: Mapped[str | None] = mapped_column(Text)
    
    # Initiated by
    initiated_by: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id")
    )

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
    provider: Mapped["BackgroundCheckProvider | None"] = relationship(
        "BackgroundCheckProvider", back_populates="checks"
    )

    # Indexes
    __table_args__ = (
        Index("idx_bg_check_app", "application_id", "status"),
    )
