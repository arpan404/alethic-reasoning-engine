"""
AI Evaluations Module

Centralized AI evaluation system with:
- AIEvaluation central hub
- Interview scheduling with Zoom/Meet/Teams
- Specialized result tables for screening, interview, assessment
- Human interview analysis and transcription
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
from database.models.applications import EvaluationPhase, EvaluationStatus, AIRecommendation
from datetime import datetime
from enum import Enum as PyEnum
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from database.models.applications import Application
    from database.models.candidates import Candidate
    from database.models.jobs import Job
    from database.models.chat_session import ChatSession


# ==================== Enums ===================== #
class EvaluationType(str, PyEnum):
    """Types of AI evaluations."""

    SCREENING = "screening"
    INTERVIEW = "interview"
    ASSESSMENT = "assessment"
    CHAT = "chat"
    ANALYSIS = "analysis"
    RECOMMENDATION = "recommendation"
    TRANSCRIPT_ANALYSIS = "transcript_analysis"
    CUSTOM = "custom"


class InterviewType(str, PyEnum):
    """Types of interviews."""

    INITIAL_SCREENING = "initial_screening"
    PHONE_SCREEN = "phone_screen"
    TECHNICAL = "technical"
    BEHAVIORAL = "behavioral"
    CULTURAL = "cultural"
    CASE_STUDY = "case_study"
    PANEL = "panel"
    FINAL = "final"
    OFFER_DISCUSSION = "offer_discussion"


class InterviewStatus(str, PyEnum):
    """Status of an interview."""

    DRAFT = "draft"
    SCHEDULED = "scheduled"
    CONFIRMED = "confirmed"
    RESCHEDULED = "rescheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"


class MeetingPlatform(str, PyEnum):
    """Video meeting platforms."""

    ZOOM = "zoom"
    GOOGLE_MEET = "google_meet"
    MICROSOFT_TEAMS = "microsoft_teams"
    WEBEX = "webex"
    PHONE = "phone"
    IN_PERSON = "in_person"
    CUSTOM = "custom"


class BotStatus(str, PyEnum):
    """Status of AI bot in meeting."""

    PENDING = "pending"
    JOINING = "joining"
    JOINED = "joined"
    RECORDING = "recording"
    PROCESSING = "processing"
    LEFT = "left"
    ERROR = "error"


class AssessmentType(str, PyEnum):
    """Types of assessments."""

    CODING_CHALLENGE = "coding_challenge"
    TECHNICAL_QUIZ = "technical_quiz"
    COGNITIVE = "cognitive"
    PERSONALITY = "personality"
    SITUATIONAL_JUDGMENT = "situational_judgment"
    LANGUAGE = "language"
    TYPING = "typing"
    CUSTOM = "custom"


class RecordingType(str, PyEnum):
    """Types of recordings."""

    VIDEO = "video"
    AUDIO = "audio"
    SCREEN_SHARE = "screen_share"
    COMPOSITE = "composite"


class ProcessingStatus(str, PyEnum):
    """Processing status for async operations."""

    PENDING = "pending"
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class LiveSessionStatus(str, PyEnum):
    """Status of live AI assistant session."""

    CONNECTING = "connecting"
    ACTIVE = "active"
    PAUSED = "paused"
    RECONNECTING = "reconnecting"
    ENDED = "ended"
    ERROR = "error"


class FeedbackRecommendation(str, PyEnum):
    """Interview feedback recommendations."""

    STRONG_HIRE = "strong_hire"
    HIRE = "hire"
    LEAN_HIRE = "lean_hire"
    LEAN_NO_HIRE = "lean_no_hire"
    NO_HIRE = "no_hire"
    STRONG_NO_HIRE = "strong_no_hire"


class ReminderRecipient(str, PyEnum):
    """Reminder recipient types."""

    CANDIDATE = "candidate"
    INTERVIEWER = "interviewer"
    ORGANIZER = "organizer"
    ALL = "all"


class ReminderType(str, PyEnum):
    """Types of reminders."""

    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"
    CALENDAR = "calendar"


class ReminderStatus(str, PyEnum):
    """Status of reminders."""

    PENDING = "pending"
    SCHEDULED = "scheduled"
    SENT = "sent"
    FAILED = "failed"
    CANCELLED = "cancelled"


# ==================== AIEvaluation (Central Hub) ===================== #
@audit_changes
class AIEvaluation(Base, ComplianceMixin):
    """
    Central table tracking ALL AI evaluations across the system.
    Links to specialized result tables and chat sessions.
    """

    __tablename__ = "ai_evaluations"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )

    # References
    application_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("applications.id", ondelete="CASCADE"),
        index=True,
    )
    candidate_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("candidates.id", ondelete="CASCADE"),
        index=True,
    )
    job_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("jobs.id", ondelete="CASCADE"),
        index=True,
    )
    interview_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("interviews.id", ondelete="SET NULL"),
        index=True,
    )

    # Evaluation identification
    evaluation_type: Mapped[EvaluationType] = mapped_column(
        SQLEnum(EvaluationType, native_enum=False, length=50),
        nullable=False,
        index=True,
    )
    phase: Mapped[EvaluationPhase | None] = mapped_column(
        SQLEnum(EvaluationPhase, native_enum=False, length=100),
        index=True,
    )

    # Status
    status: Mapped[EvaluationStatus] = mapped_column(
        SQLEnum(EvaluationStatus, native_enum=False, length=50),
        nullable=False,
        default=EvaluationStatus.NOT_STARTED,
        index=True,
    )

    # Scoring
    score: Mapped[float | None] = mapped_column(Float)  # 0.0 to 1.0
    confidence: Mapped[float | None] = mapped_column(Float)
    recommendation: Mapped[AIRecommendation | None] = mapped_column(
        SQLEnum(AIRecommendation, native_enum=False, length=50)
    )
    result_summary: Mapped[str | None] = mapped_column(Text)

    # JSON Results - flexible schema support
    raw_result: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    structured_output: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    criteria_scores: Mapped[dict[str, float] | None] = mapped_column(JSON)
    model_config: Mapped[dict[str, Any] | None] = mapped_column(JSON)

    # AI model info
    model_name: Mapped[str | None] = mapped_column(String(100))
    model_version: Mapped[str | None] = mapped_column(String(50))
    prompt_version: Mapped[str | None] = mapped_column(String(50))

    # Processing metadata
    processing_time_ms: Mapped[int | None] = mapped_column(BigInteger)
    input_tokens: Mapped[int | None] = mapped_column(BigInteger)
    output_tokens: Mapped[int | None] = mapped_column(BigInteger)
    cost_cents: Mapped[int | None] = mapped_column(BigInteger)

    # Error handling
    error_message: Mapped[str | None] = mapped_column(Text)
    error_code: Mapped[str | None] = mapped_column(String(100))
    retry_count: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)

    # Timestamps
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
        "Application", back_populates="ai_evaluations"
    )
    screening_result: Mapped["AIScreeningResult | None"] = relationship(
        "AIScreeningResult",
        back_populates="evaluation",
        uselist=False,
        cascade="all, delete-orphan",
    )
    interview_result: Mapped["AIInterviewResult | None"] = relationship(
        "AIInterviewResult",
        back_populates="evaluation",
        uselist=False,
        cascade="all, delete-orphan",
    )
    assessment_result: Mapped["AIAssessmentResult | None"] = relationship(
        "AIAssessmentResult",
        back_populates="evaluation",
        uselist=False,
        cascade="all, delete-orphan",
    )
    human_interview_analysis: Mapped["HumanInterviewAnalysis | None"] = relationship(
        "HumanInterviewAnalysis",
        back_populates="evaluation",
        uselist=False,
        cascade="all, delete-orphan",
    )
    transcripts: Mapped[list["InterviewTranscript"]] = relationship(
        "InterviewTranscript",
        back_populates="evaluation",
        cascade="all, delete-orphan",
    )

    # Indexes
    __table_args__ = (
        Index("idx_ai_eval_app_type", "application_id", "evaluation_type"),
        Index("idx_ai_eval_status", "status", "created_at"),
    )


# ==================== Interview Model ===================== #
@audit_changes
class Interview(Base, ComplianceMixin):
    """
    Scheduled interviews with video platform integration.
    Supports Zoom, Google Meet, Microsoft Teams, and AI bot joining.
    """

    __tablename__ = "interviews"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )

    # References
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
    job_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Interview details
    interview_type: Mapped[InterviewType] = mapped_column(
        SQLEnum(InterviewType, native_enum=False, length=50),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[InterviewStatus] = mapped_column(
        SQLEnum(InterviewStatus, native_enum=False, length=50),
        nullable=False,
        default=InterviewStatus.DRAFT,
        index=True,
    )

    # Meeting platform
    platform: Mapped[MeetingPlatform] = mapped_column(
        SQLEnum(MeetingPlatform, native_enum=False, length=50),
        nullable=False,
        default=MeetingPlatform.ZOOM,
    )
    meeting_url: Mapped[str | None] = mapped_column(String(1000))
    meeting_id: Mapped[str | None] = mapped_column(String(255))
    meeting_password: Mapped[str | None] = mapped_column(
        String(255),
        info=compliance_column(
            sensitivity=DataSensitivity.RESTRICTED,
            encryption=EncryptionType.AT_REST,
            mask_in_logs=True,
        ),
    )
    dial_in_number: Mapped[str | None] = mapped_column(String(50))
    dial_in_pin: Mapped[str | None] = mapped_column(String(50))
    platform_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    platform_event_id: Mapped[str | None] = mapped_column(
        String(255), index=True
    )  # Calendar event ID

    # Location (for in-person)
    location: Mapped[str | None] = mapped_column(String(500))
    location_instructions: Mapped[str | None] = mapped_column(Text)

    # AI Bot
    ai_bot_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    ai_bot_id: Mapped[str | None] = mapped_column(String(100))
    ai_bot_status: Mapped[BotStatus | None] = mapped_column(
        SQLEnum(BotStatus, native_enum=False, length=50)
    )
    ai_bot_joined_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ai_bot_left_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ai_bot_error: Mapped[str | None] = mapped_column(Text)

    # Schedule
    scheduled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    duration_minutes: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=60
    )
    timezone: Mapped[str] = mapped_column(String(50), nullable=False, default="UTC")
    actual_start_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    actual_end_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    actual_duration_seconds: Mapped[int | None] = mapped_column(BigInteger)

    # Participants
    interviewer_ids: Mapped[list[int] | None] = mapped_column(JSON)
    organizer_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id"), nullable=False
    )

    # Scoring
    overall_score: Mapped[float | None] = mapped_column(Float)
    interviewer_feedback: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    hiring_decision: Mapped[str | None] = mapped_column(String(50))

    # Cancellation/reschedule
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_by: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.id"))
    cancellation_reason: Mapped[str | None] = mapped_column(Text)
    rescheduled_from: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("interviews.id")
    )

    # Reminders
    reminder_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    follow_up_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

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
    application: Mapped["Application"] = relationship(
        "Application", back_populates="interviews"
    )
    recordings: Mapped[list["InterviewRecording"]] = relationship(
        "InterviewRecording",
        back_populates="interview",
        cascade="all, delete-orphan",
    )

    # Indexes
    __table_args__ = (
        Index("idx_interview_schedule", "scheduled_at", "status"),
        Index("idx_interview_app", "application_id", "interview_type"),
    )


# ==================== AIScreeningResult ===================== #
@audit_changes
class AIScreeningResult(Base):
    """
    Detailed results from AI resume/profile screening.
    """

    __tablename__ = "ai_screening_results"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )
    evaluation_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("ai_evaluations.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    # Match scores
    skills_match_score: Mapped[float | None] = mapped_column(Float)
    experience_match_score: Mapped[float | None] = mapped_column(Float)
    education_match_score: Mapped[float | None] = mapped_column(Float)
    culture_fit_score: Mapped[float | None] = mapped_column(Float)
    overall_match_score: Mapped[float | None] = mapped_column(Float)

    # Detailed analysis
    skills_found: Mapped[list[str] | None] = mapped_column(JSON)
    skills_missing: Mapped[list[str] | None] = mapped_column(JSON)
    skills_breakdown: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    experience_analysis: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    education_analysis: Mapped[dict[str, Any] | None] = mapped_column(JSON)

    # Flags and highlights
    red_flags: Mapped[list[str] | None] = mapped_column(JSON)
    highlights: Mapped[list[str] | None] = mapped_column(JSON)
    concerns: Mapped[list[str] | None] = mapped_column(JSON)

    # Parsed resume data
    parsed_resume_data: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    parsed_profile_data: Mapped[dict[str, Any] | None] = mapped_column(JSON)

    # Recommendations
    suggested_interview_focus: Mapped[list[str] | None] = mapped_column(JSON)
    suggested_questions: Mapped[list[str] | None] = mapped_column(JSON)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Relationships
    evaluation: Mapped["AIEvaluation"] = relationship(
        "AIEvaluation", back_populates="screening_result"
    )


# ==================== AIInterviewResult ===================== #
@audit_changes
class AIInterviewResult(Base):
    """
    Results from AI-conducted interviews.
    """

    __tablename__ = "ai_interview_results"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )
    evaluation_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("ai_evaluations.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    # Interview details
    interview_type: Mapped[InterviewType] = mapped_column(
        SQLEnum(InterviewType, native_enum=False, length=50),
        nullable=False,
    )
    duration_seconds: Mapped[int | None] = mapped_column(BigInteger)

    # Questions and answers
    questions_asked: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON)
    response_quality_scores: Mapped[dict[str, float] | None] = mapped_column(JSON)

    # Scores
    communication_score: Mapped[float | None] = mapped_column(Float)
    technical_score: Mapped[float | None] = mapped_column(Float)
    problem_solving_score: Mapped[float | None] = mapped_column(Float)
    cultural_fit_score: Mapped[float | None] = mapped_column(Float)
    enthusiasm_score: Mapped[float | None] = mapped_column(Float)

    # Analysis
    behavioral_indicators: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    key_strengths: Mapped[list[str] | None] = mapped_column(JSON)
    areas_of_concern: Mapped[list[str] | None] = mapped_column(JSON)

    # Follow-up
    follow_up_questions: Mapped[list[str] | None] = mapped_column(JSON)
    topics_to_explore: Mapped[list[str] | None] = mapped_column(JSON)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Relationships
    evaluation: Mapped["AIEvaluation"] = relationship(
        "AIEvaluation", back_populates="interview_result"
    )


# ==================== AIAssessmentResult ===================== #
@audit_changes
class AIAssessmentResult(Base):
    """
    Results from skill/cognitive assessments.
    """

    __tablename__ = "ai_assessment_results"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )
    evaluation_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("ai_evaluations.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    # Assessment details
    assessment_type: Mapped[AssessmentType] = mapped_column(
        SQLEnum(AssessmentType, native_enum=False, length=50),
        nullable=False,
    )
    assessment_name: Mapped[str | None] = mapped_column(String(255))

    # Performance
    total_questions: Mapped[int | None] = mapped_column(BigInteger)
    correct_answers: Mapped[int | None] = mapped_column(BigInteger)
    completion_percentage: Mapped[float | None] = mapped_column(Float)
    completion_time_seconds: Mapped[int | None] = mapped_column(BigInteger)
    time_limit_seconds: Mapped[int | None] = mapped_column(BigInteger)

    # Scores
    section_scores: Mapped[dict[str, float] | None] = mapped_column(JSON)
    skill_proficiencies: Mapped[dict[str, str] | None] = mapped_column(JSON)
    percentile: Mapped[float | None] = mapped_column(Float)

    # For coding assessments
    code_submissions: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON)
    code_quality_score: Mapped[float | None] = mapped_column(Float)
    test_cases_passed: Mapped[int | None] = mapped_column(BigInteger)
    test_cases_total: Mapped[int | None] = mapped_column(BigInteger)

    # Proctoring
    proctoring_flags: Mapped[list[str] | None] = mapped_column(JSON)
    proctoring_score: Mapped[float | None] = mapped_column(Float)
    suspicious_activity: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )

    # Timestamps
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Relationships
    evaluation: Mapped["AIEvaluation"] = relationship(
        "AIEvaluation", back_populates="assessment_result"
    )


# ==================== HumanInterviewAnalysis ===================== #
@audit_changes
class HumanInterviewAnalysis(Base, ComplianceMixin):
    """
    AI analysis of human recruiter-candidate interviews.
    Provides insights on both candidate and recruiter.
    """

    __tablename__ = "human_interview_analyses"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )
    evaluation_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("ai_evaluations.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    interview_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("interviews.id", ondelete="SET NULL"),
        index=True,
    )
    recording_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("interview_recordings.id", ondelete="SET NULL"),
        index=True,
    )

    # Interview metadata
    interview_type: Mapped[InterviewType] = mapped_column(
        SQLEnum(InterviewType, native_enum=False, length=50),
        nullable=False,
    )
    duration_seconds: Mapped[int | None] = mapped_column(BigInteger)

    # Candidate analysis
    candidate_sentiment_score: Mapped[float | None] = mapped_column(Float)
    candidate_engagement_score: Mapped[float | None] = mapped_column(Float)
    candidate_communication_score: Mapped[float | None] = mapped_column(Float)
    candidate_confidence_score: Mapped[float | None] = mapped_column(Float)
    candidate_response_quality: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    candidate_red_flags: Mapped[list[str] | None] = mapped_column(JSON)
    candidate_strengths: Mapped[list[str] | None] = mapped_column(JSON)
    candidate_concerns: Mapped[list[str] | None] = mapped_column(JSON)

    # Recruiter analysis
    recruiter_sentiment_score: Mapped[float | None] = mapped_column(Float)
    recruiter_bias_indicators: Mapped[list[str] | None] = mapped_column(JSON)
    recruiter_question_quality: Mapped[float | None] = mapped_column(Float)
    recruiter_engagement_score: Mapped[float | None] = mapped_column(Float)

    # Conversation analysis
    key_moments: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON)
    topics_discussed: Mapped[list[str] | None] = mapped_column(JSON)
    questions_asked: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON)
    topic_coverage: Mapped[dict[str, float] | None] = mapped_column(JSON)

    # Recommendations
    follow_up_suggestions: Mapped[list[str] | None] = mapped_column(JSON)
    hiring_recommendation: Mapped[str | None] = mapped_column(String(50))
    recommendation_reasoning: Mapped[str | None] = mapped_column(Text)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Relationships
    evaluation: Mapped["AIEvaluation"] = relationship(
        "AIEvaluation", back_populates="human_interview_analysis"
    )


# ==================== InterviewRecording ===================== #
@audit_changes
class InterviewRecording(Base, ComplianceMixin):
    """
    Video/audio recordings of interviews.
    """

    __tablename__ = "interview_recordings"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )
    interview_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("interviews.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    application_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("applications.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Recording identification
    recording_type: Mapped[RecordingType] = mapped_column(
        SQLEnum(RecordingType, native_enum=False, length=50),
        nullable=False,
    )
    file_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("files.id")
    )

    # File details
    file_url: Mapped[str | None] = mapped_column(String(1000))
    file_format: Mapped[str | None] = mapped_column(String(20))
    file_size_bytes: Mapped[int | None] = mapped_column(BigInteger)
    duration_seconds: Mapped[int | None] = mapped_column(BigInteger)

    # Processing status
    processing_status: Mapped[ProcessingStatus] = mapped_column(
        SQLEnum(ProcessingStatus, native_enum=False, length=50),
        nullable=False,
        default=ProcessingStatus.PENDING,
    )
    transcription_status: Mapped[ProcessingStatus] = mapped_column(
        SQLEnum(ProcessingStatus, native_enum=False, length=50),
        nullable=False,
        default=ProcessingStatus.PENDING,
    )
    analysis_status: Mapped[ProcessingStatus] = mapped_column(
        SQLEnum(ProcessingStatus, native_enum=False, length=50),
        nullable=False,
        default=ProcessingStatus.PENDING,
    )

    # Metadata
    recorded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    recorded_by: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.id"))
    participants: Mapped[list[int] | None] = mapped_column(JSON)
    extra_metadata: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSON)

    # Error handling
    processing_error: Mapped[str | None] = mapped_column(Text)

    # Retention
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

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
    interview: Mapped["Interview"] = relationship(
        "Interview", back_populates="recordings"
    )
    transcripts: Mapped[list["InterviewTranscript"]] = relationship(
        "InterviewTranscript",
        back_populates="recording",
        cascade="all, delete-orphan",
    )


# ==================== InterviewTranscript ===================== #
@audit_changes
class InterviewTranscript(Base, ComplianceMixin):
    """
    Timestamped transcript from interview recordings.
    """

    __tablename__ = "interview_transcripts"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )
    recording_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("interview_recordings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    evaluation_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("ai_evaluations.id", ondelete="SET NULL"),
        index=True,
    )

    # Transcript content
    full_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        info=compliance_column(
            sensitivity=DataSensitivity.CONFIDENTIAL,
            gdpr_relevant=True,
            retention_period=DataRetentionPeriod.YEARS_2,
        ),
    )
    utterances: Mapped[list[dict[str, Any]] | None] = mapped_column(
        JSON
    )  # [{speaker, text, start_ms, end_ms}]
    word_timings: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON)

    # Speaker identification
    speakers: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON)
    speaker_mapping: Mapped[dict[str, int] | None] = mapped_column(
        JSON
    )  # {speaker_id: user/candidate_id}

    # Quality metrics
    confidence_score: Mapped[float | None] = mapped_column(Float)
    language: Mapped[str | None] = mapped_column(String(10))
    model_used: Mapped[str | None] = mapped_column(String(100))

    # Processing
    processing_time_ms: Mapped[int | None] = mapped_column(BigInteger)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Relationships
    recording: Mapped["InterviewRecording"] = relationship(
        "InterviewRecording", back_populates="transcripts"
    )
    evaluation: Mapped["AIEvaluation | None"] = relationship(
        "AIEvaluation", back_populates="transcripts"
    )


# ==================== LiveAISession ===================== #
@audit_changes
class LiveAISession(Base, ComplianceMixin):
    """
    Live AI assistant session during video calls.
    Provides real-time insights, suggestions, and nudges.
    """

    __tablename__ = "live_ai_sessions"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )
    interview_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("interviews.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Connection info
    meeting_platform: Mapped[MeetingPlatform] = mapped_column(
        SQLEnum(MeetingPlatform, native_enum=False, length=50),
        nullable=False,
    )
    bot_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    meeting_url: Mapped[str | None] = mapped_column(String(1000))
    session_status: Mapped[LiveSessionStatus] = mapped_column(
        SQLEnum(LiveSessionStatus, native_enum=False, length=50),
        nullable=False,
        default=LiveSessionStatus.CONNECTING,
        index=True,
    )

    # Connection timing
    joined_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    left_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reconnect_count: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)

    # Real-time data (updated during session)
    live_transcript: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON)
    live_insights: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON)
    suggested_questions: Mapped[list[str] | None] = mapped_column(JSON)
    talking_points: Mapped[list[str] | None] = mapped_column(JSON)
    current_topic: Mapped[str | None] = mapped_column(String(255))

    # Alerts and nudges sent
    alerts_sent: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON)
    nudges: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON)

    # AI assistant config
    assistant_config: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    assistant_mode: Mapped[str | None] = mapped_column(String(50))  # passive, active

    # Error handling
    last_error: Mapped[str | None] = mapped_column(Text)
    error_count: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)

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


# ==================== InterviewScheduleSlot ===================== #
@audit_changes
class InterviewScheduleSlot(Base):
    """
    Available interview time slots for scheduling.
    Supports recurrence for recurring availability.
    """

    __tablename__ = "interview_schedule_slots"

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
    interviewer_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Time slot
    start_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    end_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    timezone: Mapped[str] = mapped_column(String(50), nullable=False, default="UTC")

    # Availability
    is_available: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    booked_interview_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("interviews.id")
    )

    # Recurrence (iCal RRULE format)
    recurrence_rule: Mapped[str | None] = mapped_column(String(500))
    recurrence_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    parent_slot_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("interview_schedule_slots.id")
    )

    # Preferences
    interview_types: Mapped[list[str] | None] = mapped_column(JSON)
    max_interviews_per_day: Mapped[int | None] = mapped_column(BigInteger)

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

    # Indexes
    __table_args__ = (
        Index("idx_slot_availability", "interviewer_id", "start_time", "is_available"),
    )


# ==================== InterviewFeedback ===================== #
@audit_changes
class InterviewFeedback(Base, ComplianceMixin):
    """
    Post-interview feedback from interviewers.
    """

    __tablename__ = "interview_feedback"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )
    interview_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("interviews.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    interviewer_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Overall rating
    overall_rating: Mapped[int | None] = mapped_column(BigInteger)  # 1-5
    recommendation: Mapped[FeedbackRecommendation | None] = mapped_column(
        SQLEnum(FeedbackRecommendation, native_enum=False, length=50)
    )

    # Detailed feedback
    strengths: Mapped[list[str] | None] = mapped_column(JSON)
    concerns: Mapped[list[str] | None] = mapped_column(JSON)
    notes: Mapped[str | None] = mapped_column(
        Text,
        info=compliance_column(
            sensitivity=DataSensitivity.CONFIDENTIAL,
            retention_period=DataRetentionPeriod.YEARS_2,
        ),
    )

    # Scorecard reference
    scorecard_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("interview_scorecards.id")
    )

    # Status
    is_submitted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

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

    # Unique constraint: one feedback per interviewer per interview
    __table_args__ = (
        UniqueConstraint(
            "interview_id", "interviewer_id", name="uq_interview_feedback"
        ),
    )


# ==================== InterviewScorecard ===================== #
@audit_changes
class InterviewScorecard(Base):
    """
    Structured scoring rubric for interviews.
    """

    __tablename__ = "interview_scorecards"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )
    interview_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("interviews.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    interviewer_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    template_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("scorecard_templates.id")
    )

    # Scores
    criteria_scores: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False
    )  # {criterion: {score, notes, weight}}
    total_score: Mapped[float | None] = mapped_column(Float)
    weighted_score: Mapped[float | None] = mapped_column(Float)

    # Status
    is_complete: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

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

    # Unique constraint: one scorecard per interviewer per interview
    __table_args__ = (
        UniqueConstraint(
            "interview_id", "interviewer_id", name="uq_interview_scorecard"
        ),
    )


# ==================== ScorecardTemplate ===================== #
@audit_changes
class ScorecardTemplate(Base):
    """
    Reusable scorecard templates per job or organization.
    """

    __tablename__ = "scorecard_templates"

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
        BigInteger, ForeignKey("jobs.id", ondelete="CASCADE"), index=True
    )

    # Template info
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    interview_type: Mapped[InterviewType | None] = mapped_column(
        SQLEnum(InterviewType, native_enum=False, length=50)
    )

    # Criteria definition
    criteria: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON, nullable=False
    )  # [{name, description, weight, scale_min, scale_max}]

    # Settings
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
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


# ==================== MeetingPlatformCredential ===================== #
@audit_changes
class MeetingPlatformCredential(Base, ComplianceMixin):
    """
    OAuth credentials for Zoom/Google Meet/Microsoft Teams per organization.
    """

    __tablename__ = "meeting_platform_credentials"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )
    organization_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Platform
    platform: Mapped[MeetingPlatform] = mapped_column(
        SQLEnum(MeetingPlatform, native_enum=False, length=50),
        nullable=False,
    )

    # OAuth tokens (encrypted)
    access_token: Mapped[str | None] = mapped_column(
        Text,
        info=compliance_column(
            sensitivity=DataSensitivity.RESTRICTED,
            encryption=EncryptionType.AT_REST,
            mask_in_logs=True,
            soc2_critical=True,
        ),
    )
    refresh_token: Mapped[str | None] = mapped_column(
        Text,
        info=compliance_column(
            sensitivity=DataSensitivity.RESTRICTED,
            encryption=EncryptionType.AT_REST,
            mask_in_logs=True,
            soc2_critical=True,
        ),
    )
    token_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Scopes and permissions
    scopes: Mapped[list[str] | None] = mapped_column(JSON)
    account_id: Mapped[str | None] = mapped_column(String(255))
    account_email: Mapped[str | None] = mapped_column(String(255))

    # Webhook
    webhook_secret: Mapped[str | None] = mapped_column(
        String(255),
        info=compliance_column(
            sensitivity=DataSensitivity.RESTRICTED,
            encryption=EncryptionType.AT_REST,
            mask_in_logs=True,
        ),
    )
    webhook_url: Mapped[str | None] = mapped_column(String(1000))

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
    connected_by: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id"), nullable=False
    )

    # Unique constraint: one credential per platform per org
    __table_args__ = (
        UniqueConstraint(
            "organization_id", "platform", name="uq_org_meeting_platform"
        ),
    )


# ==================== InterviewReminder ===================== #
@audit_changes
class InterviewReminder(Base):
    """
    Scheduled reminders for interviews.
    """

    __tablename__ = "interview_reminders"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )
    interview_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("interviews.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Recipient
    recipient_type: Mapped[ReminderRecipient] = mapped_column(
        SQLEnum(ReminderRecipient, native_enum=False, length=50),
        nullable=False,
    )
    recipient_id: Mapped[int | None] = mapped_column(BigInteger)
    recipient_email: Mapped[str | None] = mapped_column(String(255))
    recipient_phone: Mapped[str | None] = mapped_column(String(50))

    # Reminder config
    reminder_type: Mapped[ReminderType] = mapped_column(
        SQLEnum(ReminderType, native_enum=False, length=50),
        nullable=False,
    )
    remind_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    minutes_before: Mapped[int] = mapped_column(BigInteger, nullable=False)

    # Status
    status: Mapped[ReminderStatus] = mapped_column(
        SQLEnum(ReminderStatus, native_enum=False, length=50),
        nullable=False,
        default=ReminderStatus.PENDING,
    )
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_message: Mapped[str | None] = mapped_column(Text)
    retry_count: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Index for pending reminders
    __table_args__ = (Index("idx_reminder_pending", "remind_at", "status"),)


# ==================== AI Question Bank Enums ===================== #
class QuestionDifficulty(str, PyEnum):
    """Difficulty level of questions."""

    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"
    EXPERT = "expert"


class QuestionSkillLevel(str, PyEnum):
    """Target skill level for question."""

    ENTRY = "entry"
    JUNIOR = "junior"
    MID = "mid"
    SENIOR = "senior"
    LEAD = "lead"
    PRINCIPAL = "principal"


# ==================== AIQuestionCategory Model ===================== #
@audit_changes
class AIQuestionCategory(Base):
    """
    Categories for organizing AI interview questions.
    """

    __tablename__ = "ai_question_categories"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )
    organization_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        index=True,
    )  # Null for system categories

    # Category info
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    slug: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    # Hierarchy
    parent_category_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("ai_question_categories.id")
    )

    # Settings
    is_system: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )  # Built-in categories
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    display_order: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)

    # Icon/color for UI
    icon: Mapped[str | None] = mapped_column(String(50))
    color: Mapped[str | None] = mapped_column(String(20))

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
    questions: Mapped[list["AIQuestionBank"]] = relationship(
        "AIQuestionBank", back_populates="category", cascade="all, delete-orphan"
    )


# ==================== AIQuestionBank Model ===================== #
@audit_changes
class AIQuestionBank(Base):
    """
    Reusable AI interview questions with scoring rubrics.
    """

    __tablename__ = "ai_question_bank"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )
    organization_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        index=True,
    )  # Null for system questions
    category_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("ai_question_categories.id", ondelete="SET NULL"),
        index=True,
    )

    # Question content
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    question_context: Mapped[str | None] = mapped_column(
        Text
    )  # Additional context for AI
    follow_up_questions: Mapped[list[str] | None] = mapped_column(JSON)

    # Classification
    interview_type: Mapped[InterviewType | None] = mapped_column(
        SQLEnum(InterviewType, native_enum=False, length=50)
    )
    difficulty: Mapped[QuestionDifficulty] = mapped_column(
        SQLEnum(QuestionDifficulty, native_enum=False, length=50),
        nullable=False,
        default=QuestionDifficulty.MEDIUM,
    )
    skill_level: Mapped[QuestionSkillLevel | None] = mapped_column(
        SQLEnum(QuestionSkillLevel, native_enum=False, length=50)
    )

    # Skills/competencies assessed
    skills_assessed: Mapped[list[str] | None] = mapped_column(JSON)
    competencies_assessed: Mapped[list[str] | None] = mapped_column(JSON)

    # Scoring
    scoring_rubric: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False
    )  # {score_level: {criteria, keywords, examples}}
    ideal_answer: Mapped[str | None] = mapped_column(Text)
    answer_keywords: Mapped[list[str] | None] = mapped_column(JSON)
    max_score: Mapped[float] = mapped_column(Float, nullable=False, default=5.0)

    # AI evaluation settings
    evaluation_prompt: Mapped[str | None] = mapped_column(Text)
    evaluation_criteria: Mapped[list[str] | None] = mapped_column(JSON)
    min_response_length: Mapped[int | None] = mapped_column(BigInteger)
    expected_duration_seconds: Mapped[int | None] = mapped_column(BigInteger)

    # Usage tracking
    times_used: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    avg_score: Mapped[float | None] = mapped_column(Float)

    # Tags
    tags: Mapped[list[str] | None] = mapped_column(JSON)

    # Status
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
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
    created_by: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.id"))

    # Relationships
    category: Mapped["AIQuestionCategory | None"] = relationship(
        "AIQuestionCategory", back_populates="questions"
    )

    # Indexes
    __table_args__ = (
        Index("idx_question_category", "category_id", "difficulty"),
        Index("idx_question_type", "interview_type", "skill_level"),
    )
