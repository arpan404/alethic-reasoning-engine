"""
Compliance Module

EEOC/Diversity tracking for equal opportunity compliance.
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
    GDPRDataCategory,
    DataRetentionPeriod,
)
from datetime import datetime
from enum import Enum as PyEnum
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from database.models.candidates import Candidate
    from database.models.organizations import Organization


# ==================== Enums ===================== #
class GenderIdentity(str, PyEnum):
    """Gender identity options."""

    MALE = "male"
    FEMALE = "female"
    NON_BINARY = "non_binary"
    PREFER_NOT_TO_SAY = "prefer_not_to_say"
    OTHER = "other"


class Ethnicity(str, PyEnum):
    """Ethnicity options (US EEOC categories)."""

    HISPANIC_LATINO = "hispanic_latino"
    WHITE = "white"
    BLACK_AFRICAN_AMERICAN = "black_african_american"
    NATIVE_AMERICAN = "native_american"
    ASIAN = "asian"
    NATIVE_HAWAIIAN_PACIFIC = "native_hawaiian_pacific"
    TWO_OR_MORE = "two_or_more"
    PREFER_NOT_TO_SAY = "prefer_not_to_say"


class VeteranStatus(str, PyEnum):
    """Veteran status options."""

    NOT_VETERAN = "not_veteran"
    PROTECTED_VETERAN = "protected_veteran"
    RECENTLY_SEPARATED = "recently_separated"
    ACTIVE_DUTY = "active_duty"
    ARMED_FORCES_SERVICE_MEDAL = "armed_forces_service_medal"
    PREFER_NOT_TO_SAY = "prefer_not_to_say"


class DisabilityStatus(str, PyEnum):
    """Disability status options."""

    NO_DISABILITY = "no_disability"
    HAS_DISABILITY = "has_disability"
    PREFER_NOT_TO_SAY = "prefer_not_to_say"


class EEOCReportType(str, PyEnum):
    """Type of EEOC report."""

    EEO1 = "eeo1"
    VETS4212 = "vets4212"
    AFFIRMATIVE_ACTION = "affirmative_action"
    CUSTOM = "custom"


# ==================== DiversityData Model ===================== #
@audit_changes
class DiversityData(Base, ComplianceMixin):
    """
    Optional demographic data for EEOC compliance.
    Collected voluntarily and stored separately from application.
    """

    __tablename__ = "diversity_data"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )
    candidate_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("candidates.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    # Relationship
    candidate: Mapped["Candidate"] = relationship(
        "Candidate", back_populates="diversity_data"
    )

    # Gender
    gender: Mapped[GenderIdentity | None] = mapped_column(
        SQLEnum(GenderIdentity, native_enum=False, length=50),
        info=compliance_column(
            sensitivity=DataSensitivity.HIGHLY_SENSITIVE,
            gdpr_relevant=True,
            gdpr_category=GDPRDataCategory.SPECIAL_CATEGORY,
            retention_period=DataRetentionPeriod.YEARS_7,
            anonymize_on_delete=True,
        ),
    )
    gender_self_describe: Mapped[str | None] = mapped_column(
        String(100),
        info=compliance_column(
            sensitivity=DataSensitivity.HIGHLY_SENSITIVE,
            anonymize_on_delete=True,
        ),
    )

    # Ethnicity
    ethnicity: Mapped[Ethnicity | None] = mapped_column(
        SQLEnum(Ethnicity, native_enum=False, length=50),
        info=compliance_column(
            sensitivity=DataSensitivity.HIGHLY_SENSITIVE,
            gdpr_relevant=True,
            gdpr_category=GDPRDataCategory.SPECIAL_CATEGORY,
            retention_period=DataRetentionPeriod.YEARS_7,
            anonymize_on_delete=True,
        ),
    )

    # Veteran status
    veteran_status: Mapped[VeteranStatus | None] = mapped_column(
        SQLEnum(VeteranStatus, native_enum=False, length=50),
        info=compliance_column(
            sensitivity=DataSensitivity.HIGHLY_SENSITIVE,
            retention_period=DataRetentionPeriod.YEARS_7,
            anonymize_on_delete=True,
        ),
    )

    # Disability status
    disability_status: Mapped[DisabilityStatus | None] = mapped_column(
        SQLEnum(DisabilityStatus, native_enum=False, length=50),
        info=compliance_column(
            sensitivity=DataSensitivity.HIGHLY_SENSITIVE,
            gdpr_relevant=True,
            gdpr_category=GDPRDataCategory.SPECIAL_CATEGORY,
            retention_period=DataRetentionPeriod.YEARS_7,
            anonymize_on_delete=True,
        ),
    )

    # Additional info
    date_of_birth: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        info=compliance_column(
            sensitivity=DataSensitivity.HIGHLY_SENSITIVE,
            gdpr_relevant=True,
            gdpr_category=GDPRDataCategory.PERSONAL_IDENTITY,
            anonymize_on_delete=True,
        ),
    )

    # Consent
    consent_given: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    consent_given_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    consent_ip_address: Mapped[str | None] = mapped_column(String(50))

    # Timestamps
    collected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


# ==================== EEOCReport Model ===================== #
@audit_changes
class EEOCReport(Base):
    """
    Generated EEOC compliance reports.
    """

    __tablename__ = "eeoc_reports"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )
    organization_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Report info
    report_type: Mapped[EEOCReportType] = mapped_column(
        SQLEnum(EEOCReportType, native_enum=False, length=50),
        nullable=False,
    )
    report_name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

    # Period
    period_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    period_end: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    reporting_year: Mapped[int] = mapped_column(BigInteger, nullable=False)

    # Scope
    job_ids: Mapped[list[int] | None] = mapped_column(JSON)
    department_ids: Mapped[list[int] | None] = mapped_column(JSON)

    # Data (aggregated, anonymized)
    applicant_data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    hire_data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    pipeline_data: Mapped[dict[str, Any] | None] = mapped_column(JSON)

    # Summary statistics
    total_applicants: Mapped[int] = mapped_column(BigInteger, nullable=False)
    total_hires: Mapped[int] = mapped_column(BigInteger, nullable=False)
    response_rate: Mapped[float | None] = mapped_column()

    # File
    report_file_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("files.id")
    )

    # Status
    is_submitted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    submitted_by: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id")
    )

    # Timestamps
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    created_by: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id"), nullable=False
    )

    # Relationships
    organization: Mapped["Organization"] = relationship(
        "Organization", back_populates="eoc_reports"
    )

    # Indexes
    __table_args__ = (
        Index("idx_eeoc_report_period", "organization_id", "reporting_year"),
    )
