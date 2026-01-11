"""
Application Models

Job applications with full lifecycle tracking, AI scoring, source attribution,
notes, tags, and activity logging. Designed for scalability and type safety.
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
    DataRetentionPeriod,
)
from database.models.audit import ApplicationStatus, AIApplicationStatus
from datetime import datetime
from enum import Enum as PyEnum
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from database.models.candidates import Candidate
    from database.models.jobs import Job


# ==================== Application Enums ===================== #
class ApplicationSource(str, PyEnum):
    """Source of the application."""

    # Direct sources
    DIRECT = "direct"
    CAREER_PAGE = "career_page"
    COMPANY_WEBSITE = "company_website"

    # Job boards
    LINKEDIN = "linkedin"
    INDEED = "indeed"
    GLASSDOOR = "glassdoor"
    ZIPRECRUITER = "ziprecruiter"
    MONSTER = "monster"

    # ATS integrations
    GREENHOUSE = "greenhouse"
    LEVER = "lever"
    WORKDAY = "workday"

    # Referral
    REFERRAL = "referral"
    EMPLOYEE_REFERRAL = "employee_referral"

    # Recruitment
    AGENCY = "agency"
    HEADHUNTER = "headhunter"

    # Other
    API = "api"
    IMPORT = "import"
    MANUAL = "manual"
    SOCIAL_MEDIA = "social_media"
    OTHER = "other"


class AIScreeningStatus(str, PyEnum):
    """Status of AI screening process."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class AIRecommendation(str, PyEnum):
    """AI recommendation levels."""

    STRONG_MATCH = "strong_match"
    MATCH = "match"
    WEAK_MATCH = "weak_match"
    NO_MATCH = "no_match"
    REQUIRES_REVIEW = "requires_review"


class EvaluationPhase(str, PyEnum):
    """Phases of AI evaluation for applications."""

    # Initial screening
    RESUME_SCREENING = "resume_screening"
    RESUME_PARSING = "resume_parsing"

    # Skills & qualifications
    SKILLS_ASSESSMENT = "skills_assessment"
    TECHNICAL_SCREENING = "technical_screening"
    EXPERIENCE_MATCHING = "experience_matching"
    EDUCATION_VERIFICATION = "education_verification"

    # Fit assessment
    CULTURE_FIT = "culture_fit"
    ROLE_FIT = "role_fit"
    TEAM_FIT = "team_fit"

    # Behavioral
    PERSONALITY_ASSESSMENT = "personality_assessment"
    SOFT_SKILLS = "soft_skills"
    COMMUNICATION_ASSESSMENT = "communication_assessment"

    # Background & compliance
    BACKGROUND_CHECK = "background_check"
    REFERENCE_CHECK = "reference_check"
    EMPLOYMENT_VERIFICATION = "employment_verification"
    IDENTITY_VERIFICATION = "identity_verification"
    CREDENTIAL_VERIFICATION = "credential_verification"

    # Interview-related
    VIDEO_INTERVIEW_ANALYSIS = "video_interview_analysis"
    INTERVIEW_SCORING = "interview_scoring"
    TRANSCRIPT_ANALYSIS = "transcript_analysis"

    # Final evaluation
    COMPREHENSIVE_SCORING = "comprehensive_scoring"
    FINAL_RECOMMENDATION = "final_recommendation"
    OFFER_OPTIMIZATION = "offer_optimization"

    # Custom
    CUSTOM = "custom"


class EvaluationStatus(str, PyEnum):
    """Status of an individual evaluation phase."""

    NOT_STARTED = "not_started"
    QUEUED = "queued"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    REQUIRES_MANUAL_REVIEW = "requires_manual_review"
    CANCELLED = "cancelled"


class ApplicationActivityType(str, PyEnum):
    """Types of application activities."""

    # Status changes
    STATUS_CHANGED = "status_changed"
    AI_STATUS_CHANGED = "ai_status_changed"

    # Document actions
    RESUME_UPLOADED = "resume_uploaded"
    COVER_LETTER_UPLOADED = "cover_letter_uploaded"
    DOCUMENT_VIEWED = "document_viewed"

    # Communication
    EMAIL_SENT = "email_sent"
    EMAIL_RECEIVED = "email_received"
    NOTE_ADDED = "note_added"
    MESSAGE_SENT = "message_sent"

    # Interview
    INTERVIEW_SCHEDULED = "interview_scheduled"
    INTERVIEW_COMPLETED = "interview_completed"
    INTERVIEW_CANCELLED = "interview_cancelled"
    INTERVIEW_FEEDBACK_ADDED = "interview_feedback_added"

    # Screening
    AI_SCREENING_STARTED = "ai_screening_started"
    AI_SCREENING_COMPLETED = "ai_screening_completed"
    MANUAL_SCREENING_COMPLETED = "manual_screening_completed"

    # Assignment
    ASSIGNED = "assigned"
    REASSIGNED = "reassigned"

    # Offer
    OFFER_CREATED = "offer_created"
    OFFER_SENT = "offer_sent"
    OFFER_ACCEPTED = "offer_accepted"
    OFFER_DECLINED = "offer_declined"
    OFFER_EXPIRED = "offer_expired"

    # Other
    TAG_ADDED = "tag_added"
    TAG_REMOVED = "tag_removed"
    COMMENT_ADDED = "comment_added"
    VIEWED = "viewed"
    EXPORTED = "exported"

    # Evaluation phases
    EVALUATION_STARTED = "evaluation_started"
    EVALUATION_COMPLETED = "evaluation_completed"
    EVALUATION_FAILED = "evaluation_failed"
    EVALUATION_SKIPPED = "evaluation_skipped"


class NoteVisibility(str, PyEnum):
    """Visibility of application notes."""

    PRIVATE = "private"  # Only author
    TEAM = "team"  # Hiring team
    ORGANIZATION = "organization"  # Entire org


# ==================== Application Model ===================== #
@audit_changes
class Application(Base, ComplianceMixin):
    """
    Job application - represents a candidate applying to a specific job.
    A candidate can have multiple applications to different jobs across organizations.
    Organizations can only see applications to their own job postings.
    """

    __tablename__ = "applications"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )

    # References
    candidate_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("candidates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    job_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    organization_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Application identification
    application_number: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, index=True
    )  # Human-readable ID like APP-2024-001234

    # Status tracking (uses enums from audit.py)
    status: Mapped[ApplicationStatus] = mapped_column(
        SQLEnum(ApplicationStatus, native_enum=False, length=50),
        nullable=False,
        default=ApplicationStatus.APPLIED,
        index=True,
    )
    ai_status: Mapped[AIApplicationStatus | None] = mapped_column(
        SQLEnum(AIApplicationStatus, native_enum=False, length=50),
        index=True,
    )

    # Source tracking - where did this application come from?
    source: Mapped[ApplicationSource] = mapped_column(
        SQLEnum(ApplicationSource, native_enum=False, length=50),
        nullable=False,
        default=ApplicationSource.DIRECT,
        index=True,
    )
    source_id: Mapped[str | None] = mapped_column(
        String(255), index=True
    )  # External ID from source platform
    source_url: Mapped[str | None] = mapped_column(String(1000))  # Original listing URL
    referrer_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id")
    )  # If referred by an employee
    referrer_notes: Mapped[str | None] = mapped_column(Text)

    # Application-specific documents (may differ from candidate profile)
    resume_file_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("files.id"), nullable=True
    )
    cover_letter_file_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("files.id"), nullable=True
    )
    cover_letter_text: Mapped[str | None] = mapped_column(Text)

    # Application data - answers to application questions
    application_data: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    application_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSON)

    # AI Screening
    ai_screening_status: Mapped[AIScreeningStatus] = mapped_column(
        SQLEnum(AIScreeningStatus, native_enum=False, length=50),
        nullable=False,
        default=AIScreeningStatus.PENDING,
    )
    ai_screening_score: Mapped[float | None] = mapped_column(Float)  # 0.0 to 1.0
    ai_recommendation: Mapped[AIRecommendation | None] = mapped_column(
        SQLEnum(AIRecommendation, native_enum=False, length=50)
    )
    ai_score_breakdown: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    ai_summary: Mapped[str | None] = mapped_column(Text)
    ai_recommendations: Mapped[list[str] | None] = mapped_column(JSON)
    ai_screened_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Manual screening
    screening_completed: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    screening_score: Mapped[float | None] = mapped_column(Float)
    screening_notes: Mapped[str | None] = mapped_column(Text)
    screened_by: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id")
    )
    screened_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Interview tracking
    current_interview_stage: Mapped[int | None] = mapped_column(BigInteger)
    total_interview_stages: Mapped[int | None] = mapped_column(BigInteger)

    # Offer details
    offer_amount: Mapped[int | None] = mapped_column(BigInteger)  # In cents
    offer_currency: Mapped[str | None] = mapped_column(String(10))
    offer_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    offer_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    offer_accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    offer_declined_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    offer_declined_reason: Mapped[str | None] = mapped_column(Text)

    # Rejection details
    rejected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rejection_reason: Mapped[str | None] = mapped_column(Text)
    rejection_stage: Mapped[str | None] = mapped_column(String(100))
    rejected_by: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id")
    )

    # Withdrawal
    withdrawn_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    withdrawal_reason: Mapped[str | None] = mapped_column(Text)

    # Assignment
    assigned_to: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id"), index=True
    )
    assigned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Internal notes (quick notes, detailed notes are in ApplicationNote)
    internal_notes: Mapped[str | None] = mapped_column(Text)

    # Timestamps
    applied_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    last_activity_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
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
    candidate: Mapped["Candidate"] = relationship(
        "Candidate", back_populates="applications"
    )
    job: Mapped["Job"] = relationship(
        "Job", back_populates="applications"
    )
    notes: Mapped[list["ApplicationNote"]] = relationship(
        "ApplicationNote", back_populates="application", cascade="all, delete-orphan"
    )
    tags: Mapped[list["ApplicationTag"]] = relationship(
        "ApplicationTag", back_populates="application", cascade="all, delete-orphan"
    )
    activities: Mapped[list["ApplicationActivity"]] = relationship(
        "ApplicationActivity", back_populates="application", cascade="all, delete-orphan"
    )
    evaluations: Mapped[list["ApplicationEvaluation"]] = relationship(
        "ApplicationEvaluation", back_populates="application", cascade="all, delete-orphan"
    )

    # Unique constraint: one application per candidate per job
    __table_args__ = (
        UniqueConstraint("candidate_id", "job_id", name="uq_candidate_job_application"),
        Index("idx_application_org_status", "organization_id", "status"),
        Index("idx_application_source", "organization_id", "source"),
    )


# ==================== Application Note Model ===================== #
@audit_changes
class ApplicationNote(Base):
    """
    Notes and comments on applications.
    Supports visibility levels and threading.
    """

    __tablename__ = "application_notes"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )
    application_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("applications.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Note content
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        info=compliance_column(
            sensitivity=DataSensitivity.CONFIDENTIAL,
            retention_period=DataRetentionPeriod.YEARS_2,
        ),
    )

    # Visibility
    visibility: Mapped[NoteVisibility] = mapped_column(
        SQLEnum(NoteVisibility, native_enum=False, length=50),
        nullable=False,
        default=NoteVisibility.TEAM,
    )

    # Threading (reply to another note)
    parent_note_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("application_notes.id")
    )

    # Pinned note
    is_pinned: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    created_by: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id"), nullable=False
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
    application: Mapped["Application"] = relationship(
        "Application", back_populates="notes"
    )


# ==================== Application Tag Model ===================== #
@audit_changes
class ApplicationTag(Base):
    """
    Tags for organizing and filtering applications.
    """

    __tablename__ = "application_tags"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )
    application_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("applications.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Tag info
    tag: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    color: Mapped[str | None] = mapped_column(String(20))  # Hex color for UI

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    created_by: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id"), nullable=False
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
    application: Mapped["Application"] = relationship(
        "Application", back_populates="tags"
    )

    # Unique constraint: one tag per application
    __table_args__ = (
        UniqueConstraint("application_id", "tag", name="uq_application_tag"),
    )


# ==================== Application Activity Model ===================== #
@audit_changes
class ApplicationActivity(Base):
    """
    Activity log for applications - tracks all actions and changes.
    Provides complete audit trail for compliance.
    """

    __tablename__ = "application_activities"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )
    application_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("applications.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Activity type
    activity_type: Mapped[ApplicationActivityType] = mapped_column(
        SQLEnum(ApplicationActivityType, native_enum=False, length=100),
        nullable=False,
        index=True,
    )

    # Activity details
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    activity_data: Mapped[dict[str, Any] | None] = mapped_column(JSON)

    # For status changes
    old_value: Mapped[str | None] = mapped_column(String(255))
    new_value: Mapped[str | None] = mapped_column(String(255))

    # Reference to related entity
    related_entity_type: Mapped[str | None] = mapped_column(String(50))
    related_entity_id: Mapped[int | None] = mapped_column(BigInteger)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )
    created_by: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id")
    )  # Nullable for system-generated activities

    # Relationships
    application: Mapped["Application"] = relationship(
        "Application", back_populates="activities"
    )

    # Index for timeline queries
    __table_args__ = (
        Index("idx_application_activity_timeline", "application_id", "created_at"),
    )


# ==================== Application Evaluation Model ===================== #
@audit_changes
class ApplicationEvaluation(Base):
    """
    Tracks individual AI evaluation phases for applications.
    Each application can have multiple evaluations across different phases.
    This enables multi-stage AI processing: resume screening, skills assessment,
    background check, culture fit, etc.
    """

    __tablename__ = "application_evaluations"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )
    application_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("applications.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Evaluation phase identification
    phase: Mapped[EvaluationPhase] = mapped_column(
        SQLEnum(EvaluationPhase, native_enum=False, length=100),
        nullable=False,
        index=True,
    )
    phase_order: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=0
    )  # Order in evaluation pipeline

    # Status
    status: Mapped[EvaluationStatus] = mapped_column(
        SQLEnum(EvaluationStatus, native_enum=False, length=50),
        nullable=False,
        default=EvaluationStatus.NOT_STARTED,
        index=True,
    )

    # Scoring
    score: Mapped[float | None] = mapped_column(Float)  # 0.0 to 1.0
    score_breakdown: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    confidence: Mapped[float | None] = mapped_column(Float)  # AI confidence in result
    recommendation: Mapped[AIRecommendation | None] = mapped_column(
        SQLEnum(AIRecommendation, native_enum=False, length=50)
    )

    # Detailed results
    summary: Mapped[str | None] = mapped_column(Text)
    findings: Mapped[list[str] | None] = mapped_column(JSON)  # Key findings
    strengths: Mapped[list[str] | None] = mapped_column(JSON)
    weaknesses: Mapped[list[str] | None] = mapped_column(JSON)
    recommendations: Mapped[list[str] | None] = mapped_column(JSON)
    raw_result: Mapped[dict[str, Any] | None] = mapped_column(JSON)  # Full AI response

    # Flags for review
    requires_manual_review: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    manual_review_reason: Mapped[str | None] = mapped_column(Text)
    manual_reviewed: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    manual_reviewed_by: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id")
    )
    manual_reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    manual_review_notes: Mapped[str | None] = mapped_column(Text)
    manual_override_score: Mapped[float | None] = mapped_column(Float)

    # Error handling
    error_message: Mapped[str | None] = mapped_column(Text)
    error_code: Mapped[str | None] = mapped_column(String(100))
    retry_count: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    max_retries: Mapped[int] = mapped_column(BigInteger, nullable=False, default=3)

    # AI model info
    model_name: Mapped[str | None] = mapped_column(String(100))
    model_version: Mapped[str | None] = mapped_column(String(50))
    prompt_version: Mapped[str | None] = mapped_column(String(50))

    # Processing metadata
    processing_time_ms: Mapped[int | None] = mapped_column(BigInteger)
    input_tokens: Mapped[int | None] = mapped_column(BigInteger)
    output_tokens: Mapped[int | None] = mapped_column(BigInteger)
    cost_cents: Mapped[int | None] = mapped_column(BigInteger)  # Cost in cents

    # Timestamps
    queued_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
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
    application: Mapped["Application"] = relationship(
        "Application", back_populates="evaluations"
    )

    # Indexes and constraints
    __table_args__ = (
        # One evaluation per phase per application (can be re-run by deleting old)
        UniqueConstraint("application_id", "phase", name="uq_application_evaluation_phase"),
        Index("idx_evaluation_status", "application_id", "status"),
        Index("idx_evaluation_phase_status", "phase", "status"),
    )
