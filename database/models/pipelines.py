"""
Pipelines Module

Customizable hiring pipelines with stages and application tracking.
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
    from database.models.applications import Application
    from database.models.jobs import Job
    from database.models.organizations import Organization


# ==================== Enums ===================== #
class StageType(str, PyEnum):
    """Type of pipeline stage."""

    APPLICATION = "application"
    SCREENING = "screening"
    PHONE_SCREEN = "phone_screen"
    INTERVIEW = "interview"
    TECHNICAL = "technical"
    ONSITE = "onsite"
    ASSESSMENT = "assessment"
    REFERENCE_CHECK = "reference_check"
    BACKGROUND_CHECK = "background_check"
    OFFER = "offer"
    HIRED = "hired"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"
    ON_HOLD = "on_hold"


class StageAction(str, PyEnum):
    """Actions triggered at stage transitions."""

    SEND_EMAIL = "send_email"
    SCHEDULE_INTERVIEW = "schedule_interview"
    REQUEST_ASSESSMENT = "request_assessment"
    NOTIFY_TEAM = "notify_team"
    CREATE_TASK = "create_task"
    AI_EVALUATION = "ai_evaluation"
    BACKGROUND_CHECK = "background_check"
    GENERATE_OFFER = "generate_offer"


class TransitionTrigger(str, PyEnum):
    """What triggered stage transition."""

    MANUAL = "manual"
    AI_RECOMMENDATION = "ai_recommendation"
    AUTO_ADVANCE = "auto_advance"
    SCHEDULED = "scheduled"
    CANDIDATE_ACTION = "candidate_action"
    SYSTEM = "system"


# ==================== HiringPipeline Model ===================== #
@audit_changes
class HiringPipeline(Base):
    """
    Customizable hiring pipeline per organization or job.
    """

    __tablename__ = "hiring_pipelines"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )
    organization_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    job_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("jobs.id", ondelete="CASCADE"),
        index=True,
    )

    # Pipeline info
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Settings
    allow_skip_stages: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    allow_backward_movement: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    auto_archive_rejected_days: Mapped[int | None] = mapped_column(BigInteger)

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
    job: Mapped["Job | None"] = relationship("Job", back_populates="pipeline")
    stages: Mapped[list["PipelineStage"]] = relationship(
        "PipelineStage", back_populates="pipeline", cascade="all, delete-orphan"
    )
    organization: Mapped["Organization"] = relationship(
        "Organization", back_populates="pipelines"
    )

    # Indexes
    __table_args__ = (
        Index("idx_pipeline_org", "organization_id"),
        Index("idx_pipeline_job", "job_id"),
        Index("idx_pipeline_active", "is_active"),
        Index("idx_pipeline_default", "organization_id", "is_default"),
        # Partial index for active pipelines
        Index(
            "idx_pipeline_active_org",
            "organization_id",
            "created_at",
            postgresql_where="is_active = true"
        ),
    )


# ==================== PipelineStage Model ===================== #
@audit_changes
class PipelineStage(Base):
    """
    Individual stage in a hiring pipeline.
    """

    __tablename__ = "pipeline_stages"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )
    pipeline_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("hiring_pipelines.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Stage info
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    stage_type: Mapped[StageType] = mapped_column(
        SQLEnum(StageType, native_enum=False, length=50),
        nullable=False,
    )
    description: Mapped[str | None] = mapped_column(Text)
    color: Mapped[str | None] = mapped_column(String(20))  # Hex color for UI

    # Order
    stage_order: Mapped[int] = mapped_column(BigInteger, nullable=False)
    is_terminal: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )  # hired/rejected

    # Requirements
    required_interviews: Mapped[int | None] = mapped_column(BigInteger)
    required_assessments: Mapped[list[str] | None] = mapped_column(JSON)
    required_approvals: Mapped[list[int] | None] = mapped_column(JSON)  # User IDs
    min_days_in_stage: Mapped[int | None] = mapped_column(BigInteger)
    max_days_in_stage: Mapped[int | None] = mapped_column(BigInteger)

    # Automation
    auto_actions: Mapped[list[dict[str, Any]] | None] = mapped_column(
        JSON
    )  # [{action, config}]
    entry_triggers: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON)
    exit_triggers: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON)

    # AI settings
    ai_evaluation_enabled: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    ai_auto_advance_threshold: Mapped[float | None] = mapped_column()

    # Notifications
    notify_on_entry: Mapped[list[int] | None] = mapped_column(JSON)  # User IDs
    candidate_email_template_id: Mapped[int | None] = mapped_column(BigInteger)

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
    pipeline: Mapped["HiringPipeline"] = relationship(
        "HiringPipeline", back_populates="stages"
    )

    # Indexes and constraints
    __table_args__ = (
        UniqueConstraint("pipeline_id", "stage_order", name="uq_pipeline_stage_order"),
        Index("idx_stage_pipeline", "pipeline_id", "stage_order"),
        Index("idx_stage_type", "stage_type"),
        Index("idx_stage_terminal", "is_terminal"),
        # GIN indexes for JSON arrays (PostgreSQL)
        Index(
            "idx_stage_auto_actions_gin",
            "auto_actions",
            postgresql_using="gin"
        ),
    )


# ==================== ApplicationStageHistory Model ===================== #
@audit_changes
class ApplicationStageHistory(Base):
    """
    Tracks application movement through pipeline stages.
    """

    __tablename__ = "application_stage_history"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )
    application_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("applications.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    stage_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("pipeline_stages.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    pipeline_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("hiring_pipelines.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Stage info (denormalized for history)
    stage_name: Mapped[str] = mapped_column(String(255), nullable=False)
    stage_type: Mapped[StageType] = mapped_column(
        SQLEnum(StageType, native_enum=False, length=50),
        nullable=False,
    )

    # Transition details
    previous_stage_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("pipeline_stages.id")
    )
    trigger: Mapped[TransitionTrigger] = mapped_column(
        SQLEnum(TransitionTrigger, native_enum=False, length=50),
        nullable=False,
        default=TransitionTrigger.MANUAL,
    )
    triggered_by: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id")
    )
    notes: Mapped[str | None] = mapped_column(Text)

    # Time in stage
    entered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    exited_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_seconds: Mapped[int | None] = mapped_column(BigInteger)

    # Current stage flag
    is_current: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Relationships
    application: Mapped["Application"] = relationship(
        "Application", back_populates="stage_history"
    )

    # Indexes
    __table_args__ = (
        Index("idx_stage_history_application", "application_id"),
        Index("idx_stage_history_stage", "stage_id"),
        Index("idx_stage_history_pipeline", "pipeline_id"),
        Index("idx_stage_history_entered", "entered_at"),
        Index("idx_stage_history_exited", "exited_at"),
        # Composite index for timeline queries
        Index("idx_stage_history_app_timeline", "application_id", "entered_at"),
        Index("idx_stage_history_trigger", "transition_trigger"),
    )

    # Indexes
    __table_args__ = (
        Index("idx_stage_history_app", "application_id", "is_current"),
        Index("idx_stage_history_entered", "entered_at"),
    )
