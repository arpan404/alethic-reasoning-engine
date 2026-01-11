from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import (
    String,
    Boolean,
    ForeignKey,
    BigInteger,
    DateTime,
    func,
    JSON,
    Text,
    Float,
    Enum as SQLEnum,
)
from database.engine import Base
from datetime import datetime
from enum import Enum as PyEnum
from typing import Any


# ============ Audit Enums ============ #
class AuditAction(str, PyEnum):
    """Audit action types."""

    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    VIEW = "view"
    EXPORT = "export"


class AIDecisionType(str, PyEnum):
    """Types of AI decisions for tracking."""

    SCREENING = "screening"
    SCORING = "scoring"
    RECOMMENDATION = "recommendation"
    REJECTION = "rejection"
    MATCHING = "matching"
    RANKING = "ranking"


class AIDecisionReviewOutcome(str, PyEnum):
    """Outcomes for human review of AI decisions."""

    APPROVED = "approved"
    REJECTED = "rejected"
    MODIFIED = "modified"
    PENDING = "pending"


class GDPRRequestStatus(str, PyEnum):
    """Status of GDPR requests."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    REJECTED = "rejected"


# ==================== Models ===================== #
class AuditLog(Base):
    """
    Complete audit trail for all system actions.
    """

    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )
    # Actor
    user_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id"), index=True
    )
    user_email: Mapped[str | None] = mapped_column(String(255))

    # Action
    action: Mapped[AuditAction] = mapped_column(
        SQLEnum(AuditAction, native_enum=False, length=50),
        nullable=False,
        index=True,
    )
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    entity_id: Mapped[int | None] = mapped_column(BigInteger, index=True)

    # Details
    description: Mapped[str | None] = mapped_column(Text)
    changes: Mapped[dict[str, Any] | None] = mapped_column(JSON)  # Before/after values
    metadata: Mapped[dict[str, Any] | None] = mapped_column(JSON)

    # Request context
    ip_address: Mapped[str | None] = mapped_column(String(45))
    user_agent: Mapped[str | None] = mapped_column(Text)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )


# =================== Application Status Enum ==================== #
class ApplicationStatus(str, PyEnum):
    """Canonical statuses for a job application."""

    APPLIED = "applied"
    UNDER_REVIEW = "under_review"
    SHORTLISTED = "shortlisted"
    PHONE_SCREEN = "phone_screen"
    INTERVIEW_SCHEDULED = "interview_scheduled"
    REFERENCE_CHECK = "reference_check"
    BACKGROUND_CHECK = "background_check"
    NEGOTIATION = "negotiation"
    OFFER_EXTENDED = "offer_extended"
    OFFER_ACCEPTED = "offer_accepted"
    OFFER_DECLINED = "offer_declined"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"
    ON_HOLD = "on_hold"
    HIRED = "hired"

    def is_terminal(self) -> bool:
        return self in APPLICATION_STATUS_TERMINALS

    def can_transition_to(self, new: "ApplicationStatus") -> bool:
        allowed = APPLICATION_STATUS_TRANSITIONS.get(self, set())
        return new in allowed

    @property
    def label(self) -> str:
        return self.value.replace("_", " ").title()

    @classmethod
    def try_parse(cls, value: str) -> "ApplicationStatus | None":
        if value is None:
            return None
        try:
            normalized = str(value).strip().lower().replace(" ", "_").replace("-", "_")
            return cls(normalized)
        except ValueError:
            return None


class AIApplicationStatus(str, PyEnum):
    """AI-generated statuses for a job application."""

    INITIAL_SCREENING = "initial_screening"
    FULL_SCREENING = "full_screening"
    REQUIRES_HUMAN_REVIEW = "requires_human_review"
    AI_ASSESSMENT_COMPLETED = "ai_assessment_completed"
    AI_SCREENED = "ai_screened"
    RESUME_PARSED = "resume_parsed"
    SKILLS_EXTRACTED = "skills_extracted"
    MATCHING_COMPLETE = "matching_complete"
    LOW_FIT = "low_fit"
    MEDIUM_FIT = "medium_fit"
    HIGH_FIT = "high_fit"
    DUPLICATE_DETECTED = "duplicate_detected"
    SPAM_DETECTED = "spam_detected"
    AUTO_PROGRESS = "auto_progress"
    AUTO_REJECTED = "auto_rejected"

    def is_terminal(self) -> bool:
        return self in AI_STATUS_TERMINALS

    @property
    def label(self) -> str:
        return self.value.replace("_", " ").title()

    @classmethod
    def try_parse(cls, value: str) -> "AIApplicationStatus | None":
        if value is None:
            return None
        try:
            normalized = str(value).strip().lower().replace(" ", "_").replace("-", "_")
            return cls(normalized)
        except ValueError:
            return None

    def suggested_application_status(self) -> "ApplicationStatus | None":
        return AI_TO_APP_STATUS_HINT.get(self)


# Helpers
APPLICATION_STATUS_TERMINALS = {
    ApplicationStatus.REJECTED,
    ApplicationStatus.WITHDRAWN,
    ApplicationStatus.OFFER_DECLINED,
    ApplicationStatus.HIRED,
}

APPLICATION_STATUS_TRANSITIONS = {
    ApplicationStatus.APPLIED: {
        ApplicationStatus.UNDER_REVIEW,
        ApplicationStatus.WITHDRAWN,
    },
    ApplicationStatus.UNDER_REVIEW: {
        ApplicationStatus.SHORTLISTED,
        ApplicationStatus.PHONE_SCREEN,
        ApplicationStatus.INTERVIEW_SCHEDULED,
        ApplicationStatus.REJECTED,
        ApplicationStatus.ON_HOLD,
    },
    ApplicationStatus.ON_HOLD: {
        ApplicationStatus.UNDER_REVIEW,
        ApplicationStatus.WITHDRAWN,
    },
    ApplicationStatus.SHORTLISTED: {
        ApplicationStatus.PHONE_SCREEN,
        ApplicationStatus.INTERVIEW_SCHEDULED,
        ApplicationStatus.REJECTED,
    },
    ApplicationStatus.PHONE_SCREEN: {
        ApplicationStatus.INTERVIEW_SCHEDULED,
        ApplicationStatus.REJECTED,
    },
    ApplicationStatus.INTERVIEW_SCHEDULED: {
        ApplicationStatus.REFERENCE_CHECK,
        ApplicationStatus.BACKGROUND_CHECK,
        ApplicationStatus.OFFER_EXTENDED,
        ApplicationStatus.REJECTED,
        ApplicationStatus.UNDER_REVIEW,
    },
    ApplicationStatus.REFERENCE_CHECK: {
        ApplicationStatus.BACKGROUND_CHECK,
        ApplicationStatus.OFFER_EXTENDED,
        ApplicationStatus.REJECTED,
    },
    ApplicationStatus.BACKGROUND_CHECK: {
        ApplicationStatus.OFFER_EXTENDED,
        ApplicationStatus.REJECTED,
        ApplicationStatus.HIRED,
    },
    ApplicationStatus.OFFER_EXTENDED: {
        ApplicationStatus.NEGOTIATION,
        ApplicationStatus.OFFER_ACCEPTED,
        ApplicationStatus.OFFER_DECLINED,
        ApplicationStatus.REJECTED,
    },
    ApplicationStatus.NEGOTIATION: {
        ApplicationStatus.OFFER_ACCEPTED,
        ApplicationStatus.OFFER_DECLINED,
    },
    ApplicationStatus.OFFER_ACCEPTED: {
        ApplicationStatus.BACKGROUND_CHECK,
        ApplicationStatus.HIRED,
    },
    ApplicationStatus.REJECTED: set(),
    ApplicationStatus.WITHDRAWN: set(),
    ApplicationStatus.OFFER_DECLINED: set(),
    ApplicationStatus.HIRED: set(),
}

AI_STATUS_TERMINALS = {
    AIApplicationStatus.AI_ASSESSMENT_COMPLETED,
    AIApplicationStatus.AI_SCREENED,
    AIApplicationStatus.AUTO_REJECTED,
}

AI_TO_APP_STATUS_HINT = {
    AIApplicationStatus.INITIAL_SCREENING: ApplicationStatus.UNDER_REVIEW,
    AIApplicationStatus.FULL_SCREENING: ApplicationStatus.UNDER_REVIEW,
    AIApplicationStatus.REQUIRES_HUMAN_REVIEW: ApplicationStatus.UNDER_REVIEW,
    AIApplicationStatus.AI_ASSESSMENT_COMPLETED: ApplicationStatus.UNDER_REVIEW,
    AIApplicationStatus.AI_SCREENED: ApplicationStatus.UNDER_REVIEW,
    AIApplicationStatus.RESUME_PARSED: ApplicationStatus.UNDER_REVIEW,
    AIApplicationStatus.SKILLS_EXTRACTED: ApplicationStatus.UNDER_REVIEW,
    AIApplicationStatus.MATCHING_COMPLETE: ApplicationStatus.UNDER_REVIEW,
    AIApplicationStatus.MEDIUM_FIT: ApplicationStatus.UNDER_REVIEW,
    AIApplicationStatus.HIGH_FIT: ApplicationStatus.SHORTLISTED,
    AIApplicationStatus.LOW_FIT: ApplicationStatus.REJECTED,
    AIApplicationStatus.DUPLICATE_DETECTED: ApplicationStatus.REJECTED,
    AIApplicationStatus.SPAM_DETECTED: ApplicationStatus.REJECTED,
    AIApplicationStatus.AUTO_PROGRESS: ApplicationStatus.UNDER_REVIEW,
    AIApplicationStatus.AUTO_REJECTED: ApplicationStatus.REJECTED,
}


# ==================== Application Status History ===================== #
class ApplicationStatusHistory(Base):
    """
    History of status changes for applications.
    """

    __tablename__ = "application_status_history"
    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )
    application_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("applications.id"), nullable=False, index=True
    )
    from_status: Mapped[ApplicationStatus | None] = mapped_column(
        SQLEnum(ApplicationStatus, native_enum=False, length=50), index=True
    )
    to_status: Mapped[ApplicationStatus] = mapped_column(
        SQLEnum(ApplicationStatus, native_enum=False, length=50),
        nullable=False,
        index=True,
    )
    ai_from_status: Mapped[AIApplicationStatus | None] = mapped_column(
        SQLEnum(AIApplicationStatus, native_enum=False, length=50), index=True
    )
    ai_to_status: Mapped[AIApplicationStatus | None] = mapped_column(
        SQLEnum(AIApplicationStatus, native_enum=False, length=50), index=True
    )
    reason: Mapped[str | None] = mapped_column(Text)
    ai_reason: Mapped[str | None] = mapped_column(Text)

    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    changed_by: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.id"))


class AIDecisionLog(Base):
    """
    Track AI-made decisions for transparency and compliance.
    """

    __tablename__ = "ai_decision_logs"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )

    # Decision context
    decision_type: Mapped[AIDecisionType] = mapped_column(
        SQLEnum(AIDecisionType, native_enum=False, length=50),
        nullable=False,
        index=True,
    )
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)

    # AI model info
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    model_version: Mapped[str | None] = mapped_column(String(50))

    # Decision details
    decision: Mapped[str] = mapped_column(Text, nullable=False)
    confidence_score: Mapped[float | None] = mapped_column(Float)
    reasoning: Mapped[str | None] = mapped_column(Text)
    input_data: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    output_data: Mapped[dict[str, Any] | None] = mapped_column(JSON)

    # Human review
    reviewed_by: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id"), index=True
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    review_outcome: Mapped[AIDecisionReviewOutcome | None] = mapped_column(
        SQLEnum(AIDecisionReviewOutcome, native_enum=False, length=50)
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


# ==================== Data Retention Policies ====================== #
class DataRetentionPolicy(Base):
    """Compliance policies for data retention."""

    __tablename__ = "data_retention_policies"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )
    organization_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)

    # Policy details
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    retention_period_days: Mapped[int] = mapped_column(BigInteger, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

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


# ==================== GDPR Request ====================== #
class GDPRRequestType(str, PyEnum):
    """Types of GDPR requests."""

    DATA_ACCESS = "data_access"
    DATA_DELETION = "data_deletion"
    DATA_PORTABILITY = "data_portability"
    DATA_CORRECTION = "data_correction"


class GDPRRequest(Base):
    """Handles GDPR-related data requests."""

    __tablename__ = "gdpr_requests"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )
    organization_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    user_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id"), index=True
    )

    request_type: Mapped[GDPRRequestType] = mapped_column(
        SQLEnum(GDPRRequestType, native_enum=False, length=50),
        nullable=False,
        index=True,
    )
    status: Mapped[GDPRRequestStatus] = mapped_column(
        SQLEnum(GDPRRequestStatus, native_enum=False, length=50),
        nullable=False,
        default=GDPRRequestStatus.PENDING,
    )
    details: Mapped[dict[str, Any] | None] = mapped_column(JSON)

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
