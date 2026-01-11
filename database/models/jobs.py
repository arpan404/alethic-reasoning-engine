"""
Jobs Module

Job postings with multi-source tracking, AI evaluation settings,
ideal candidate descriptions, and org-wide defaults with per-job overrides.
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
from database.security import audit_changes
from database.models.candidates import ExperienceLevel
from datetime import datetime
from enum import Enum as PyEnum
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from database.models.applications import Application
    from database.models.organizations import Organization


# ==================== Job Enums ===================== #
class JobStatus(str, PyEnum):
    """Job posting status."""

    DRAFT = "draft"
    OPEN = "open"
    PAUSED = "paused"
    CLOSED = "closed"
    CANCELLED = "cancelled"
    FILLED = "filled"
    ARCHIVED = "archived"


class JobType(str, PyEnum):
    """Job employment type."""

    FULL_TIME = "full_time"
    PART_TIME = "part_time"
    CONTRACT = "contract"
    INTERNSHIP = "internship"
    TEMPORARY = "temporary"
    FREELANCE = "freelance"
    VOLUNTEER = "volunteer"


class JobVisibility(str, PyEnum):
    """Job posting visibility."""

    PUBLIC = "public"  # Anyone can see
    INTERNAL = "internal"  # Only org members
    CONFIDENTIAL = "confidential"  # Limited access


class JobSourceType(str, PyEnum):
    """Source platforms for job postings."""

    # Direct
    CAREER_PAGE = "career_page"
    COMPANY_WEBSITE = "company_website"

    # Job boards
    LINKEDIN = "linkedin"
    INDEED = "indeed"
    GLASSDOOR = "glassdoor"
    ZIPRECRUITER = "ziprecruiter"
    MONSTER = "monster"

    # ATS
    GREENHOUSE = "greenhouse"
    LEVER = "lever"
    WORKDAY = "workday"

    # Referral
    REFERRAL = "referral"
    EMPLOYEE_REFERRAL = "employee_referral"

    # Agency
    AGENCY = "agency"
    HEADHUNTER = "headhunter"

    # Other
    SOCIAL_MEDIA = "social_media"
    UNIVERSITY = "university"
    JOB_FAIR = "job_fair"
    OTHER = "other"


class SourceStatus(str, PyEnum):
    """Status of a job source posting."""

    PENDING = "pending"
    ACTIVE = "active"
    PAUSED = "paused"
    EXPIRED = "expired"
    REMOVED = "removed"
    ERROR = "error"


class LocationType(str, PyEnum):
    """Job location type."""

    REMOTE = "remote"
    HYBRID = "hybrid"
    ONSITE = "onsite"
    FLEXIBLE = "flexible"


class RequirementType(str, PyEnum):
    """Types of job requirements."""

    SKILL = "skill"
    EXPERIENCE = "experience"
    EDUCATION = "education"
    CERTIFICATION = "certification"
    LANGUAGE = "language"
    CLEARANCE = "clearance"  # Security clearance
    LICENSE = "license"
    OTHER = "other"


class ProficiencyLevel(str, PyEnum):
    """Proficiency/skill level."""

    BASIC = "basic"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"
    NATIVE = "native"  # For languages


class HiringTeamRole(str, PyEnum):
    """Roles in the hiring team."""

    HIRING_MANAGER = "hiring_manager"
    RECRUITER = "recruiter"
    SOURCER = "sourcer"
    INTERVIEWER = "interviewer"
    COORDINATOR = "coordinator"
    OBSERVER = "observer"


# ==================== Organization Job Settings ===================== #
@audit_changes
class OrganizationJobSettings(Base):
    """
    Organization-wide default settings for jobs.
    Applied automatically to all jobs unless overridden.
    """

    __tablename__ = "organization_job_settings"

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

    # Default AI phases to run
    default_enabled_phases: Mapped[list[str] | None] = mapped_column(
        JSON
    )  # List of EvaluationPhase values
    default_phase_order: Mapped[list[str] | None] = mapped_column(JSON)
    default_phase_thresholds: Mapped[dict[str, float] | None] = mapped_column(
        JSON
    )  # {phase: threshold}

    # Default thresholds
    default_overall_threshold: Mapped[float | None] = mapped_column(Float)
    default_auto_reject_below: Mapped[float | None] = mapped_column(Float)
    default_auto_advance_above: Mapped[float | None] = mapped_column(Float)

    # Default AI config
    default_ai_model: Mapped[str | None] = mapped_column(String(100))
    default_scoring_weights: Mapped[dict[str, float] | None] = mapped_column(JSON)
    require_manual_review_default: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )

    # Org-level policies
    allow_job_overrides: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    mandatory_phases: Mapped[list[str] | None] = mapped_column(
        JSON
    )  # Phases that MUST run
    forbidden_phases: Mapped[list[str] | None] = mapped_column(
        JSON
    )  # Phases NOT allowed
    max_auto_reject_threshold: Mapped[float | None] = mapped_column(
        Float
    )  # Can't auto-reject above this

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
    updated_by: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id"), nullable=False
    )

    # Relationships
    organization: Mapped["Organization"] = relationship(
        "Organization", back_populates="job_settings"
    )


# ==================== Job Department ===================== #
@audit_changes
class JobDepartment(Base):
    """
    Department structure within organization.
    Supports hierarchy with parent departments.
    """

    __tablename__ = "job_departments"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )
    organization_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Department info
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    code: Mapped[str | None] = mapped_column(String(50), index=True)  # Dept code
    description: Mapped[str | None] = mapped_column(Text)

    # Hierarchy
    parent_department_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("job_departments.id")
    )

    # Leadership
    head_user_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id")
    )

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

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
    organization: Mapped["Organization"] = relationship(
        "Organization", back_populates="departments"
    )
    jobs: Mapped[list["Job"]] = relationship(
        "Job", back_populates="department", cascade="all, delete-orphan"
    )


# ==================== Job Model ===================== #
@audit_changes
class Job(Base):
    """
    Job posting with full lifecycle management.
    Supports multiple sources, locations, and AI configurations.
    """

    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )

    # Organization reference
    organization_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Basic info
    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    slug: Mapped[str] = mapped_column(
        String(300), unique=True, nullable=False, index=True
    )  # URL-friendly
    description: Mapped[str] = mapped_column(Text, nullable=False)
    short_description: Mapped[str | None] = mapped_column(String(500))
    requirements: Mapped[str | None] = mapped_column(Text)
    responsibilities: Mapped[str | None] = mapped_column(Text)
    benefits: Mapped[str | None] = mapped_column(Text)
    qualifications: Mapped[str | None] = mapped_column(Text)

    # Job classification
    status: Mapped[JobStatus] = mapped_column(
        SQLEnum(JobStatus, native_enum=False, length=50),
        nullable=False,
        default=JobStatus.DRAFT,
        index=True,
    )
    job_type: Mapped[JobType] = mapped_column(
        SQLEnum(JobType, native_enum=False, length=50),
        nullable=False,
        default=JobType.FULL_TIME,
    )
    visibility: Mapped[JobVisibility] = mapped_column(
        SQLEnum(JobVisibility, native_enum=False, length=50),
        nullable=False,
        default=JobVisibility.PUBLIC,
    )
    experience_level: Mapped[ExperienceLevel | None] = mapped_column(
        SQLEnum(ExperienceLevel, native_enum=False, length=50)
    )

    # Department & team
    department_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("job_departments.id"), index=True
    )
    hiring_manager_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id"), index=True
    )

    # Compensation
    salary_min: Mapped[int | None] = mapped_column(BigInteger)  # In cents
    salary_max: Mapped[int | None] = mapped_column(BigInteger)
    salary_currency: Mapped[str] = mapped_column(
        String(10), default="USD", nullable=False
    )
    show_salary: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    salary_period: Mapped[str | None] = mapped_column(
        String(20)
    )  # hourly, monthly, yearly

    # Headcount
    positions_available: Mapped[int] = mapped_column(
        BigInteger, default=1, nullable=False
    )
    positions_filled: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)

    # Posting dates
    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    closes_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    filled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Application tracking
    applications_count: Mapped[int] = mapped_column(
        BigInteger, default=0, nullable=False
    )
    views_count: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)

    # SEO & metadata
    meta_title: Mapped[str | None] = mapped_column(String(255))
    meta_description: Mapped[str | None] = mapped_column(String(500))
    keywords: Mapped[list[str] | None] = mapped_column(JSON)
    metadata: Mapped[dict[str, Any] | None] = mapped_column(JSON)

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
    updated_by: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id"), nullable=False
    )

    # Relationships
    organization: Mapped["Organization"] = relationship(
        "Organization", back_populates="jobs"
    )
    department: Mapped["JobDepartment | None"] = relationship(
        "JobDepartment", back_populates="jobs"
    )
    sources: Mapped[list["JobSource"]] = relationship(
        "JobSource", back_populates="job", cascade="all, delete-orphan"
    )
    locations: Mapped[list["JobLocation"]] = relationship(
        "JobLocation", back_populates="job", cascade="all, delete-orphan"
    )
    requirements_list: Mapped[list["JobRequirement"]] = relationship(
        "JobRequirement", back_populates="job", cascade="all, delete-orphan"
    )
    ai_settings: Mapped["JobAISettings | None"] = relationship(
        "JobAISettings",
        back_populates="job",
        uselist=False,
        cascade="all, delete-orphan",
    )
    hiring_team: Mapped[list["JobHiringTeam"]] = relationship(
        "JobHiringTeam", back_populates="job", cascade="all, delete-orphan"
    )
    applications: Mapped[list["Application"]] = relationship(
        "Application", back_populates="job", cascade="all, delete-orphan"
    )

    # Indexes
    __table_args__ = (
        Index("idx_job_org_status", "organization_id", "status"),
        Index("idx_job_search", "organization_id", "title", "status"),
    )


# ==================== Job Source Model ===================== #
@audit_changes
class JobSource(Base):
    """
    Tracks where a job is posted (multiple sources per job).
    """

    __tablename__ = "job_sources"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )
    job_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Source identification
    source_type: Mapped[JobSourceType] = mapped_column(
        SQLEnum(JobSourceType, native_enum=False, length=50),
        nullable=False,
        index=True,
    )
    source_name: Mapped[str | None] = mapped_column(String(255))  # Custom name

    # External references
    external_id: Mapped[str | None] = mapped_column(
        String(255), index=True
    )  # ID on source platform
    external_url: Mapped[str | None] = mapped_column(String(1000))  # URL on platform

    # Status
    status: Mapped[SourceStatus] = mapped_column(
        SQLEnum(SourceStatus, native_enum=False, length=50),
        nullable=False,
        default=SourceStatus.PENDING,
        index=True,
    )

    # Dates
    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Tracking
    applications_count: Mapped[int] = mapped_column(
        BigInteger, default=0, nullable=False
    )
    views_count: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    clicks_count: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)

    # Cost tracking
    cost_per_post: Mapped[int | None] = mapped_column(BigInteger)  # In cents
    cost_per_click: Mapped[int | None] = mapped_column(BigInteger)
    total_spend: Mapped[int | None] = mapped_column(BigInteger)

    # Error handling
    last_error: Mapped[str | None] = mapped_column(Text)
    last_error_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

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
    job: Mapped["Job"] = relationship("Job", back_populates="sources")

    # Unique constraint: one source type per job
    __table_args__ = (
        UniqueConstraint("job_id", "source_type", name="uq_job_source_type"),
    )


# ==================== Job Location Model ===================== #
@audit_changes
class JobLocation(Base):
    """
    Job location details (multiple locations per job supported).
    """

    __tablename__ = "job_locations"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )
    job_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Location type
    location_type: Mapped[LocationType] = mapped_column(
        SQLEnum(LocationType, native_enum=False, length=50),
        nullable=False,
    )

    # Address (nullable for remote)
    address_line_1: Mapped[str | None] = mapped_column(String(255))
    address_line_2: Mapped[str | None] = mapped_column(String(255))
    city: Mapped[str | None] = mapped_column(String(100))
    state: Mapped[str | None] = mapped_column(String(100))
    country: Mapped[str] = mapped_column(String(100), nullable=False)
    postal_code: Mapped[str | None] = mapped_column(String(20))

    # Additional details
    timezone: Mapped[str | None] = mapped_column(String(50))
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    relocation_assistance: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    visa_sponsorship: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )

    # Remote specifics
    remote_regions: Mapped[list[str] | None] = mapped_column(
        JSON
    )  # Allowed regions for remote

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
    job: Mapped["Job"] = relationship("Job", back_populates="locations")


# ==================== Job Requirement Model ===================== #
@audit_changes
class JobRequirement(Base):
    """
    Structured job requirements for AI matching.
    """

    __tablename__ = "job_requirements"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )
    job_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Requirement details
    requirement_type: Mapped[RequirementType] = mapped_column(
        SQLEnum(RequirementType, native_enum=False, length=50),
        nullable=False,
        index=True,
    )
    requirement_value: Mapped[str] = mapped_column(String(500), nullable=False)
    proficiency_level: Mapped[ProficiencyLevel | None] = mapped_column(
        SQLEnum(ProficiencyLevel, native_enum=False, length=50)
    )

    # Experience requirement
    years_min: Mapped[int | None] = mapped_column(BigInteger)
    years_max: Mapped[int | None] = mapped_column(BigInteger)

    # Importance
    is_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    weight: Mapped[float | None] = mapped_column(Float)  # For AI scoring weight

    # Order
    display_order: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)

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
    job: Mapped["Job"] = relationship("Job", back_populates="requirements_list")


# ==================== Job AI Settings Model ===================== #
@audit_changes
class JobAISettings(Base):
    """
    Job-specific AI evaluation settings.
    Can override organization defaults.
    """

    __tablename__ = "job_ai_settings"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )
    job_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    # Override control
    override_org_settings: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    inherit_org_for_missing: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )

    # =================== Ideal Candidate Description ===================
    ideal_candidate_description: Mapped[str | None] = mapped_column(
        Text
    )  # Free-form AI guidance
    ideal_candidate_summary: Mapped[str | None] = mapped_column(
        Text
    )  # Short version for AI
    ideal_candidate_skills: Mapped[dict[str, Any] | None] = mapped_column(
        JSON
    )  # {skill: {level, required, weight}}
    ideal_candidate_experience: Mapped[dict[str, Any] | None] = mapped_column(
        JSON
    )  # Experience requirements
    ideal_candidate_education: Mapped[dict[str, Any] | None] = mapped_column(
        JSON
    )  # Education requirements
    ideal_candidate_traits: Mapped[list[str] | None] = mapped_column(
        JSON
    )  # Soft skills/personality

    # =================== Evaluation Configuration ===================
    enabled_phases: Mapped[list[str] | None] = mapped_column(
        JSON
    )  # EvaluationPhase values
    phase_order: Mapped[list[str] | None] = mapped_column(JSON)
    phase_thresholds: Mapped[dict[str, float] | None] = mapped_column(
        JSON
    )  # {phase: threshold}

    # =================== Thresholds ===================
    overall_threshold: Mapped[float | None] = mapped_column(Float)  # 0.0 to 1.0
    auto_reject_below: Mapped[float | None] = mapped_column(Float)
    auto_advance_above: Mapped[float | None] = mapped_column(Float)

    # =================== AI Behavior ===================
    ai_model_preference: Mapped[str | None] = mapped_column(String(100))
    scoring_weights: Mapped[dict[str, float] | None] = mapped_column(
        JSON
    )  # {phase: weight}
    custom_prompts: Mapped[dict[str, str] | None] = mapped_column(
        JSON
    )  # {phase: prompt}
    require_manual_review: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )

    # =================== Additional Config ===================
    enable_ai_screening: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    screening_priority: Mapped[str | None] = mapped_column(
        String(20)
    )  # high, normal, low

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
    updated_by: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id")
    )

    # Relationships
    job: Mapped["Job"] = relationship("Job", back_populates="ai_settings")


# ==================== Job Hiring Team Model ===================== #
@audit_changes
class JobHiringTeam(Base):
    """
    Hiring team members for a job with role-based permissions.
    """

    __tablename__ = "job_hiring_team"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )
    job_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Role
    role: Mapped[HiringTeamRole] = mapped_column(
        SQLEnum(HiringTeamRole, native_enum=False, length=50),
        nullable=False,
        default=HiringTeamRole.INTERVIEWER,
    )

    # Permissions
    can_view_salary: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    can_view_applications: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    can_evaluate: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    can_make_decisions: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    can_edit_job: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Timestamps
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    added_by: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id"), nullable=False
    )

    # Relationships
    job: Mapped["Job"] = relationship("Job", back_populates="hiring_team")

    # Unique constraint: one user per job per role
    __table_args__ = (
        UniqueConstraint("job_id", "user_id", name="uq_job_hiring_team_user"),
    )
