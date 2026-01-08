"""
Enhanced AI Assessment, Evaluation, and Screening Models

This module extends the existing assessment models with advanced AI features:
- Automated AI grading for essays and coding
- AI-powered question generation
- Adaptive testing (difficulty adjustment)
- Proctoring and cheating detection
- Real-time AI assistance during assessments
"""

from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import (
    String,
    BigInteger,
    DateTime,
    func,
    Text,
    Boolean,
    ForeignKey,
    Integer,
    Numeric,
    JSON,
    Enum as SQLEnum,
)
from database.engine import Base
from database.security import SecurityMixin, sensitive_column
from datetime import datetime
from enum import Enum as PyEnum


class AIGradingStatus(str, PyEnum):
    """AI grading status."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    MANUAL_REVIEW_REQUIRED = "manual_review_required"


class ProctoringStatus(str, PyEnum):
    """Proctoring detection status."""

    CLEAN = "clean"
    SUSPICIOUS = "suspicious"
    FLAGGED = "flagged"
    VIOLATION = "violation"


class AIAssessmentGrading(Base):
    """AI-powered automated grading for assessments."""

    __tablename__ = "ai_assessment_grading"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )

    response_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("assessment_responses.id"), nullable=False, index=True
    )

    # AI grading details
    grading_status: Mapped[AIGradingStatus] = mapped_column(
        SQLEnum(AIGradingStatus, name="ai_grading_status"),
        default=AIGradingStatus.PENDING,
        nullable=False,
        index=True,
    )

    # Scores
    ai_score: Mapped[float | None] = mapped_column(Numeric(10, 2))
    confidence_score: Mapped[float | None] = mapped_column(
        Numeric(5, 4)
    )  # 0.00 to 1.00

    # AI feedback
    ai_feedback: Mapped[str | None] = mapped_column(Text)
    strengths_identified: Mapped[list | None] = mapped_column(JSON)
    areas_for_improvement: Mapped[list | None] = mapped_column(JSON)

    # Rubric scoring (for essays, coding)
    rubric_scores: Mapped[dict | None] = mapped_column(JSON)  # {criterion: score}

    # AI model info
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    model_version: Mapped[str | None] = mapped_column(String(50))

    # Manual review
    requires_manual_review: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    manual_review_reason: Mapped[str | None] = mapped_column(Text)
    reviewed_by: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.id"))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    final_score: Mapped[float | None] = mapped_column(Numeric(10, 2))

    # Timestamps
    graded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class AIQuestionGeneration(Base):
    """AI-generated assessment questions."""

    __tablename__ = "ai_question_generation"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )

    assessment_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("assessments.id"), nullable=False, index=True
    )

    # Generation parameters
    topic: Mapped[str] = mapped_column(String(500), nullable=False)
    difficulty_level: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # easy, medium, hard
    question_type: Mapped[str] = mapped_column(String(50), nullable=False)

    # Generated content
    generated_question: Mapped[str] = mapped_column(Text, nullable=False)
    generated_options: Mapped[list | None] = mapped_column(JSON)
    correct_answer: Mapped[str | None] = mapped_column(Text)
    explanation: Mapped[str | None] = mapped_column(Text)

    # Quality metrics
    quality_score: Mapped[float | None] = mapped_column(Numeric(5, 4))
    is_approved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    approved_by: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.id"))

    # AI model info
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    generation_prompt: Mapped[str | None] = mapped_column(Text)

    # Timestamps
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class AdaptiveTestingSession(Base):
    """Adaptive testing that adjusts difficulty based on performance."""

    __tablename__ = "adaptive_testing_sessions"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )

    candidate_assessment_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("candidate_assessments.id"),
        unique=True,
        nullable=False,
        index=True,
    )

    # Adaptive parameters
    starting_difficulty: Mapped[str] = mapped_column(
        String(20), default="medium", nullable=False
    )
    current_difficulty: Mapped[str] = mapped_column(String(20), nullable=False)

    # Performance tracking
    questions_attempted: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    correct_answers: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    current_accuracy: Mapped[float | None] = mapped_column(Numeric(5, 4))

    # Difficulty adjustments
    difficulty_adjustments: Mapped[list | None] = mapped_column(
        JSON
    )  # History of adjustments

    # AI decision log
    ai_decisions: Mapped[list | None] = mapped_column(
        JSON
    )  # Track AI decisions for transparency

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


class AssessmentProctoring(Base, SecurityMixin):
    """AI-powered proctoring and cheating detection."""

    __tablename__ = "assessment_proctoring"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )

    candidate_assessment_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("candidate_assessments.id"), nullable=False, index=True
    )

    # Proctoring status
    overall_status: Mapped[ProctoringStatus] = mapped_column(
        SQLEnum(ProctoringStatus, name="proctoring_status"),
        default=ProctoringStatus.CLEAN,
        nullable=False,
        index=True,
    )

    # Detection events
    tab_switches: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    copy_paste_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    multiple_faces_detected: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )
    no_face_detected: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    suspicious_audio: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Detailed events log
    events_log: Mapped[list | None] = mapped_column(JSON)  # Timestamped events

    # AI analysis
    ai_risk_score: Mapped[float | None] = mapped_column(Numeric(5, 4))  # 0.00 to 1.00
    ai_analysis: Mapped[str | None] = mapped_column(Text)

    # Video/screenshots (if enabled)
    recording_file_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("files.id")
    )
    screenshots: Mapped[list | None] = mapped_column(JSON)  # File IDs

    # Manual review
    reviewed_by: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.id"))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    review_notes: Mapped[str | None] = mapped_column(Text)

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


class CodingAssessmentExecution(Base):
    """Code execution and testing for coding assessments."""

    __tablename__ = "coding_assessment_execution"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )

    response_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("assessment_responses.id"), nullable=False, index=True
    )

    # Code submission
    submitted_code: Mapped[str] = mapped_column(Text, nullable=False)
    programming_language: Mapped[str] = mapped_column(String(50), nullable=False)

    # Execution results
    execution_status: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # success, runtime_error, timeout, compilation_error

    # Test results
    test_cases_passed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    test_cases_total: Mapped[int] = mapped_column(Integer, nullable=False)
    test_results: Mapped[list | None] = mapped_column(JSON)  # Detailed test results

    # Performance metrics
    execution_time_ms: Mapped[int | None] = mapped_column(Integer)
    memory_used_mb: Mapped[float | None] = mapped_column(Numeric(10, 2))

    # Code quality (AI analysis)
    code_quality_score: Mapped[float | None] = mapped_column(Numeric(5, 4))
    complexity_score: Mapped[float | None] = mapped_column(Numeric(5, 4))
    best_practices_score: Mapped[float | None] = mapped_column(Numeric(5, 4))

    # AI feedback
    ai_code_review: Mapped[str | None] = mapped_column(Text)
    suggestions: Mapped[list | None] = mapped_column(JSON)

    # Error details
    error_message: Mapped[str | None] = mapped_column(Text)
    stack_trace: Mapped[str | None] = mapped_column(Text)

    # Timestamps
    executed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class ScreeningWorkflow(Base):
    """AI-powered automated screening workflows."""

    __tablename__ = "screening_workflows"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )

    organization_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("organizations.id"), nullable=False, index=True
    )
    job_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("jobs.id"), index=True
    )

    # Workflow configuration
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

    # Screening steps (ordered)
    steps: Mapped[list] = mapped_column(JSON, nullable=False)
    # Example: [
    #   {"type": "resume_screening", "threshold": 0.7},
    #   {"type": "skill_assessment", "assessment_id": 123},
    #   {"type": "video_interview", "questions": [...]},
    #   {"type": "ai_evaluation", "criteria": [...]}
    # ]

    # Auto-advance rules
    auto_advance_enabled: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    auto_advance_threshold: Mapped[float | None] = mapped_column(Numeric(5, 4))

    # Auto-reject rules
    auto_reject_enabled: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    auto_reject_threshold: Mapped[float | None] = mapped_column(Numeric(5, 4))

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


class ScreeningWorkflowExecution(Base):
    """Track execution of screening workflows for applications."""

    __tablename__ = "screening_workflow_executions"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )

    workflow_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("screening_workflows.id"), nullable=False, index=True
    )
    application_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("applicants.id"), nullable=False, index=True
    )

    # Execution status
    status: Mapped[str] = mapped_column(
        String(50), default="in_progress", nullable=False, index=True
    )  # in_progress, completed, failed, cancelled

    # Current step
    current_step_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    current_step_status: Mapped[str | None] = mapped_column(String(50))

    # Step results
    step_results: Mapped[list | None] = mapped_column(JSON)
    # Example: [
    #   {"step": "resume_screening", "score": 0.85, "passed": true},
    #   {"step": "skill_assessment", "score": 0.72, "passed": true}
    # ]

    # Overall result
    overall_score: Mapped[float | None] = mapped_column(Numeric(5, 4))
    final_decision: Mapped[str | None] = mapped_column(
        String(50)
    )  # advance, reject, manual_review

    # AI decision tracking
    ai_decisions: Mapped[list | None] = mapped_column(JSON)

    # Timestamps
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
