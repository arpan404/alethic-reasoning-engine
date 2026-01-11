"""
Screening Module

Custom screening questions per job with AI scoring support.
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
from datetime import datetime
from enum import Enum as PyEnum
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from database.models.applications import Application
    from database.models.jobs import Job


# ==================== Enums ===================== #
class QuestionType(str, PyEnum):
    """Type of screening question."""

    TEXT = "text"
    TEXTAREA = "textarea"
    SELECT = "select"
    MULTI_SELECT = "multi_select"
    YES_NO = "yes_no"
    NUMBER = "number"
    DATE = "date"
    FILE = "file"
    URL = "url"
    PHONE = "phone"
    EMAIL = "email"
    LOCATION = "location"
    SALARY_EXPECTATION = "salary_expectation"
    WORK_AUTHORIZATION = "work_authorization"
    AVAILABILITY = "availability"


class QuestionCategory(str, PyEnum):
    """Category of question."""

    GENERAL = "general"
    EXPERIENCE = "experience"
    SKILLS = "skills"
    EDUCATION = "education"
    AVAILABILITY = "availability"
    COMPENSATION = "compensation"
    WORK_AUTHORIZATION = "work_authorization"
    CULTURE_FIT = "culture_fit"
    MOTIVATION = "motivation"
    TECHNICAL = "technical"
    CUSTOM = "custom"


class AnswerValidation(str, PyEnum):
    """Validation rules for answers."""

    NONE = "none"
    REQUIRED = "required"
    MIN_LENGTH = "min_length"
    MAX_LENGTH = "max_length"
    REGEX = "regex"
    KEYWORD_MATCH = "keyword_match"


# ==================== QuestionTemplate Model ===================== #
@audit_changes
class QuestionTemplate(Base):
    """
    Reusable question templates for organizations.
    """

    __tablename__ = "question_templates"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )
    organization_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Question info
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    question_type: Mapped[QuestionType] = mapped_column(
        SQLEnum(QuestionType, native_enum=False, length=50),
        nullable=False,
    )
    category: Mapped[QuestionCategory] = mapped_column(
        SQLEnum(QuestionCategory, native_enum=False, length=50),
        nullable=False,
        default=QuestionCategory.GENERAL,
    )

    # Options (for select/multi-select)
    options: Mapped[list[str] | None] = mapped_column(JSON)
    option_scores: Mapped[dict[str, float] | None] = mapped_column(
        JSON
    )  # {option: score}

    # Validation
    is_required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    validation_rules: Mapped[dict[str, Any] | None] = mapped_column(JSON)

    # AI scoring
    ai_scoring_enabled: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    ai_scoring_prompt: Mapped[str | None] = mapped_column(Text)
    ideal_answer: Mapped[str | None] = mapped_column(Text)
    scoring_rubric: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    max_score: Mapped[float | None] = mapped_column(Float)

    # Knockout
    is_knockout: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    knockout_values: Mapped[list[str] | None] = mapped_column(
        JSON
    )  # Values that disqualify

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
    created_by: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id"), nullable=False
    )

    # Indexes
    __table_args__ = (
        Index("idx_question_template_org", "organization_id"),
        Index("idx_question_template_type", "question_type"),
        Index("idx_question_template_category", "category"),
        Index("idx_question_template_active", "is_active"),
        Index("idx_question_template_knockout", "is_knockout"),
        # Partial index for active templates
        Index(
            "idx_question_template_active_org",
            "organization_id",
            "category",
            postgresql_where="is_active = true"
        ),
    )


# ==================== ScreeningQuestion Model ===================== #
@audit_changes
class ScreeningQuestion(Base):
    """
    Custom screening question per job.
    Can be created from template or custom.
    """

    __tablename__ = "screening_questions"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )
    job_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    template_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("question_templates.id")
    )

    # Question info
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    question_type: Mapped[QuestionType] = mapped_column(
        SQLEnum(QuestionType, native_enum=False, length=50),
        nullable=False,
    )
    category: Mapped[QuestionCategory] = mapped_column(
        SQLEnum(QuestionCategory, native_enum=False, length=50),
        nullable=False,
        default=QuestionCategory.GENERAL,
    )

    # Display
    display_order: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    placeholder: Mapped[str | None] = mapped_column(String(255))
    help_text: Mapped[str | None] = mapped_column(Text)

    # Options
    options: Mapped[list[str] | None] = mapped_column(JSON)
    option_scores: Mapped[dict[str, float] | None] = mapped_column(JSON)

    # Validation
    is_required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    validation_rules: Mapped[dict[str, Any] | None] = mapped_column(JSON)

    # AI scoring
    ai_scoring_enabled: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    ai_scoring_prompt: Mapped[str | None] = mapped_column(Text)
    ideal_answer: Mapped[str | None] = mapped_column(Text)
    scoring_rubric: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    max_score: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    weight: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)

    # Knockout
    is_knockout: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    knockout_values: Mapped[list[str] | None] = mapped_column(JSON)

    # Visibility
    is_visible_to_candidate: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
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
    job: Mapped["Job"] = relationship("Job", back_populates="screening_questions")
    answers: Mapped[list["ScreeningAnswer"]] = relationship(
        "ScreeningAnswer", back_populates="question", cascade="all, delete-orphan"
    )

    # Indexes
    __table_args__ = (
        Index("idx_screening_question_job", "job_id"),
        Index("idx_screening_question_template", "template_id"),
        Index("idx_screening_question_order", "job_id", "display_order"),
        Index("idx_screening_question_type", "question_type"),
        Index("idx_screening_question_required", "is_required"),
        Index("idx_screening_question_knockout", "is_knockout"),
    )


# ==================== ScreeningAnswer Model ===================== #
@audit_changes
class ScreeningAnswer(Base, ComplianceMixin):
    """
    Candidate's answer to a screening question.
    """

    __tablename__ = "screening_answers"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )
    application_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("applications.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    question_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("screening_questions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Answer content
    answer_text: Mapped[str | None] = mapped_column(
        Text,
        info=compliance_column(
            sensitivity=DataSensitivity.CONFIDENTIAL,
            gdpr_relevant=True,
            retention_period=DataRetentionPeriod.YEARS_2,
        ),
    )
    answer_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    answer_file_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("files.id")
    )

    # Scoring
    score: Mapped[float | None] = mapped_column(Float)
    max_score: Mapped[float | None] = mapped_column(Float)
    is_knockout_triggered: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )

    # AI evaluation
    ai_score: Mapped[float | None] = mapped_column(Float)
    ai_evaluation: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    ai_feedback: Mapped[str | None] = mapped_column(Text)
    ai_evaluated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Manual review
    manual_score: Mapped[float | None] = mapped_column(Float)
    manual_reviewed_by: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id")
    )
    manual_reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reviewer_notes: Mapped[str | None] = mapped_column(Text)

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
    question: Mapped["ScreeningQuestion"] = relationship(
        "ScreeningQuestion", back_populates="answers"
    )
    application: Mapped["Application"] = relationship(
        "Application", back_populates="screening_answers"
    )

    # Unique constraint
    __table_args__ = (
        UniqueConstraint(
            "application_id", "question_id", name="uq_application_question"
        ),
    )
