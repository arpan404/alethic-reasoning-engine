"""
Candidate Models

Candidates are job seekers who can have multiple applications across different jobs.
A single candidate profile (bound by email) can apply to multiple positions across organizations.
Candidates can login via WorkOS email verification.
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
)
from database.engine import Base
from database.security import ComplianceMixin, audit_changes
from database.security import (
    compliance_column,
    DataSensitivity,
    EncryptionType,
    GDPRDataCategory,
    DataRetentionPeriod,
)
from datetime import datetime
from enum import Enum as PyEnum
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from database.models.applications import Application
    from database.models.offers import Offer
    from database.models.ai_evaluations import Interview, AIEvaluation
    from database.models.talent_pools import TalentPoolMember
    from database.models.compliance import DiversityData
    from database.models.referrals import Referral
    from database.models.background_checks import BackgroundCheck


# ==================== Candidate Enums ===================== #
class CandidateStatus(str, PyEnum):
    """Status of a candidate profile."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    BLACKLISTED = "blacklisted"
    VERIFIED = "verified"
    PENDING_VERIFICATION = "pending_verification"


class CandidateSource(str, PyEnum):
    """Source from which the candidate was acquired."""

    DIRECT = "direct"
    LINKEDIN = "linkedin"
    INDEED = "indeed"
    GLASSDOOR = "glassdoor"
    GREENHOUSE = "greenhouse"
    REFERRAL = "referral"
    CAREER_PAGE = "career_page"
    JOB_BOARD = "job_board"
    AGENCY = "agency"
    SOCIAL_MEDIA = "social_media"
    INTERNAL = "internal"
    OTHER = "other"


class ExperienceLevel(str, PyEnum):
    """Experience level of candidate."""

    INTERN = "intern"
    ENTRY_LEVEL = "entry_level"
    JUNIOR = "junior"
    MID_LEVEL = "mid_level"
    SENIOR = "senior"
    LEAD = "lead"
    MANAGER = "manager"
    DIRECTOR = "director"
    VP = "vp"
    EXECUTIVE = "executive"


class EducationLevel(str, PyEnum):
    """Highest education level."""

    HIGH_SCHOOL = "high_school"
    ASSOCIATE = "associate"
    BACHELOR = "bachelor"
    MASTER = "master"
    PHD = "phd"
    PROFESSIONAL = "professional"
    OTHER = "other"


class WorkAuthorization(str, PyEnum):
    """Work authorization status."""

    CITIZEN = "citizen"
    PERMANENT_RESIDENT = "permanent_resident"
    WORK_VISA = "work_visa"
    STUDENT_VISA = "student_visa"
    REQUIRES_SPONSORSHIP = "requires_sponsorship"
    OTHER = "other"


class EmploymentType(str, PyEnum):
    """Employment type for work experience."""

    FULL_TIME = "full_time"
    PART_TIME = "part_time"
    CONTRACT = "contract"
    FREELANCE = "freelance"
    INTERNSHIP = "internship"
    TEMPORARY = "temporary"
    OTHER = "other"


# ==================== Candidate Model ===================== #
@audit_changes
class Candidate(Base, ComplianceMixin):
    """
    Candidate profile - represents a job seeker.
    One candidate can have multiple applications across different jobs/organizations.
    Email is the unique identifier that binds all applications to one profile.
    Candidates can login via WorkOS email verification.
    """

    __tablename__ = "candidates"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )

    # WorkOS integration for candidate login
    workos_user_id: Mapped[str | None] = mapped_column(
        String(100), unique=True, nullable=True, index=True
    )

    # Primary identifier - email binds all applications
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
        info=compliance_column(
            sensitivity=DataSensitivity.RESTRICTED,
            encryption=EncryptionType.AT_REST,
            pii=True,
            gdpr_relevant=True,
            gdpr_category=GDPRDataCategory.IDENTITY,
            soc2_critical=True,
            retention_period=DataRetentionPeriod.TWO_YEARS,
            anonymize_on_delete=True,
        ),
    )

    # Profile information (PII with GDPR compliance)
    first_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        info=compliance_column(
            sensitivity=DataSensitivity.RESTRICTED,
            pii=True,
            gdpr_relevant=True,
            gdpr_category=GDPRDataCategory.IDENTITY,
            retention_period=DataRetentionPeriod.TWO_YEARS,
            anonymize_on_delete=True,
        ),
    )
    last_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        info=compliance_column(
            sensitivity=DataSensitivity.RESTRICTED,
            pii=True,
            gdpr_relevant=True,
            gdpr_category=GDPRDataCategory.IDENTITY,
            retention_period=DataRetentionPeriod.TWO_YEARS,
            anonymize_on_delete=True,
        ),
    )
    phone: Mapped[str | None] = mapped_column(
        String(20),
        info=compliance_column(
            sensitivity=DataSensitivity.RESTRICTED,
            encryption=EncryptionType.AT_REST,
            pii=True,
            gdpr_relevant=True,
            gdpr_category=GDPRDataCategory.CONTACT,
            requires_consent=True,
            retention_period=DataRetentionPeriod.TWO_YEARS,
            anonymize_on_delete=True,
        ),
    )

    # Profile picture
    avatar_file_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("files.id"), nullable=True
    )

    # Status
    status: Mapped[CandidateStatus] = mapped_column(
        SQLEnum(CandidateStatus, native_enum=False, length=50),
        nullable=False,
        default=CandidateStatus.PENDING_VERIFICATION,
        index=True,
    )
    is_email_verified: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )

    # Original source (first application)
    source: Mapped[CandidateSource] = mapped_column(
        SQLEnum(CandidateSource, native_enum=False, length=50),
        nullable=False,
        default=CandidateSource.DIRECT,
    )
    source_details: Mapped[str | None] = mapped_column(String(500))

    # Professional info
    headline: Mapped[str | None] = mapped_column(String(500))
    summary: Mapped[str | None] = mapped_column(Text)
    experience_level: Mapped[ExperienceLevel | None] = mapped_column(
        SQLEnum(ExperienceLevel, native_enum=False, length=50)
    )
    years_of_experience: Mapped[int | None] = mapped_column(BigInteger)
    education_level: Mapped[EducationLevel | None] = mapped_column(
        SQLEnum(EducationLevel, native_enum=False, length=50)
    )

    # Location (PII)
    city: Mapped[str | None] = mapped_column(
        String(100),
        info=compliance_column(
            sensitivity=DataSensitivity.CONFIDENTIAL,
            pii=True,
            gdpr_relevant=True,
            gdpr_category=GDPRDataCategory.CONTACT,
            retention_period=DataRetentionPeriod.TWO_YEARS,
            anonymize_on_delete=True,
        ),
    )
    state: Mapped[str | None] = mapped_column(String(100))
    country: Mapped[str | None] = mapped_column(String(100))
    timezone: Mapped[str | None] = mapped_column(String(50))
    work_authorization: Mapped[WorkAuthorization | None] = mapped_column(
        SQLEnum(WorkAuthorization, native_enum=False, length=50)
    )

    # Links
    linkedin_url: Mapped[str | None] = mapped_column(String(500))
    github_url: Mapped[str | None] = mapped_column(String(500))
    portfolio_url: Mapped[str | None] = mapped_column(String(500))
    website_url: Mapped[str | None] = mapped_column(String(500))

    # Resume
    resume_file_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("files.id"), nullable=True
    )
    resume_text: Mapped[str | None] = mapped_column(
        Text,
        info=compliance_column(
            sensitivity=DataSensitivity.CONFIDENTIAL,
            gdpr_relevant=True,
            retention_period=DataRetentionPeriod.TWO_YEARS,
        ),
    )

    # Skills and preferences (JSON for flexibility)
    skills: Mapped[list[str] | None] = mapped_column(JSON)
    languages: Mapped[list[str] | None] = mapped_column(JSON)
    preferred_locations: Mapped[list[str] | None] = mapped_column(JSON)
    salary_expectation_min: Mapped[int | None] = mapped_column(BigInteger)
    salary_expectation_max: Mapped[int | None] = mapped_column(BigInteger)
    salary_currency: Mapped[str | None] = mapped_column(String(10))

    # Additional metadata
    extra_metadata: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSON)
    tags: Mapped[list[str] | None] = mapped_column(JSON)

    # Last activity tracking
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_activity_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

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
    applications: Mapped[list["Application"]] = relationship(
        "Application", back_populates="candidate", cascade="all, delete-orphan"
    )
    education: Mapped[list["CandidateEducation"]] = relationship(
        "CandidateEducation", back_populates="candidate", cascade="all, delete-orphan"
    )
    experience: Mapped[list["CandidateExperience"]] = relationship(
        "CandidateExperience", back_populates="candidate", cascade="all, delete-orphan"
    )
    
    # Cross-module relationships
    offers: Mapped[list["Offer"]] = relationship(
        "Offer", back_populates="candidate", cascade="all, delete-orphan"
    )
    interviews: Mapped[list["Interview"]] = relationship(
        "Interview", back_populates="candidate", cascade="all, delete-orphan"
    )
    ai_evaluations: Mapped[list["AIEvaluation"]] = relationship(
        "AIEvaluation", back_populates="candidate", cascade="all, delete-orphan"
    )
    talent_pool_memberships: Mapped[list["TalentPoolMember"]] = relationship(
        "TalentPoolMember", back_populates="candidate", cascade="all, delete-orphan"
    )
    diversity_data: Mapped["DiversityData | None"] = relationship(
        "DiversityData", back_populates="candidate", uselist=False, cascade="all, delete-orphan"
    )
    referrals_received: Mapped[list["Referral"]] = relationship(
        "Referral", back_populates="candidate", cascade="all, delete-orphan"
    )
    background_checks: Mapped[list["BackgroundCheck"]] = relationship(
        "BackgroundCheck", back_populates="candidate", cascade="all, delete-orphan"
    )

    # Indexes
    __table_args__ = (
        Index("idx_candidate_email", "email"),
        Index("idx_candidate_status", "status"),
        Index("idx_candidate_source", "source"),
        Index("idx_candidate_created_at", "created_at"),
        Index("idx_candidate_workos_user", "workos_user_id"),
        # Partial index for active candidates
        Index(
            "idx_candidate_active",
            "email",
            "created_at",
            postgresql_where="status = 'active'"
        ),
        # GIN indexes for JSON columns (PostgreSQL)
        Index(
            "idx_candidate_skills_gin",
            "skills",
            postgresql_using="gin"
        ),
        Index(
            "idx_candidate_metadata_gin",
            "metadata",
            postgresql_using="gin"
        ),
    )


# ==================== Candidate Education Model ===================== #
@audit_changes
class CandidateEducation(Base):
    """Education history for a candidate."""

    __tablename__ = "candidate_education"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )
    candidate_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("candidates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Education details
    institution: Mapped[str] = mapped_column(String(255), nullable=False)
    degree: Mapped[str | None] = mapped_column(String(255))
    field_of_study: Mapped[str | None] = mapped_column(String(255))
    education_level: Mapped[EducationLevel | None] = mapped_column(
        SQLEnum(EducationLevel, native_enum=False, length=50)
    )

    # Dates
    start_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    end_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_current: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Additional info
    gpa: Mapped[str | None] = mapped_column(String(20))
    description: Mapped[str | None] = mapped_column(Text)

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
    candidate: Mapped["Candidate"] = relationship(
        "Candidate", back_populates="education"
    )

    # Indexes
    __table_args__ = (
        Index("idx_candidate_education_candidate", "candidate_id"),
        Index("idx_candidate_education_institution", "institution"),
    )


# ==================== Candidate Experience Model ===================== #
@audit_changes
class CandidateExperience(Base):
    """Work experience for a candidate."""

    __tablename__ = "candidate_experience"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )
    candidate_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("candidates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Job details
    company: Mapped[str] = mapped_column(String(255), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    employment_type: Mapped[EmploymentType | None] = mapped_column(
        SQLEnum(EmploymentType, native_enum=False, length=50)
    )
    location: Mapped[str | None] = mapped_column(String(255))
    is_remote: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Dates
    start_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    end_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_current: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Description
    description: Mapped[str | None] = mapped_column(Text)
    skills_used: Mapped[list[str] | None] = mapped_column(JSON)
    achievements: Mapped[list[str] | None] = mapped_column(JSON)

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
    candidate: Mapped["Candidate"] = relationship(
        "Candidate", back_populates="experience"
    )

    # Indexes
    __table_args__ = (
        Index("idx_candidate_experience_candidate", "candidate_id"),
        Index("idx_candidate_experience_company", "company"),
        Index("idx_candidate_experience_dates", "candidate_id", "start_date", "end_date"),
    )
