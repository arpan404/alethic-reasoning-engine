from sqlalchemy.orm import Mapped, mapped_column
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
    Enum as SQLEnum,
)
from database.engine import Base
from datetime import datetime
from enum import Enum as PyEnum


class InterviewStatus(str, PyEnum):
    """Interview status."""

    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"


class Interview(Base):
    """Interview scheduling (includes video interview references)."""

    __tablename__ = "interviews"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )

    # Relationships
    application_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("applicants.id"), nullable=False, index=True
    )
    candidate_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("candidates.id"), nullable=False, index=True
    )
    job_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("jobs.id"), nullable=False, index=True
    )
    video_interview_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("video_interviews.id"), index=True
    )

    # Interview details
    interview_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # phone, video, in_person, technical, behavioral
    interview_round: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    status: Mapped[InterviewStatus] = mapped_column(
        SQLEnum(InterviewStatus, name="interview_status"),
        default=InterviewStatus.SCHEDULED,
        nullable=False,
        index=True,
    )

    # Scheduling
    scheduled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    duration_minutes: Mapped[int] = mapped_column(Integer, default=60, nullable=False)
    location: Mapped[str | None] = mapped_column(String(500))
    meeting_link: Mapped[str | None] = mapped_column(String(500))

    # Notes
    interviewer_notes: Mapped[str | None] = mapped_column(Text)
    candidate_notes: Mapped[str | None] = mapped_column(Text)

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


class InterviewParticipant(Base):
    """Interviewers and participants in interviews."""

    __tablename__ = "interview_participants"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )

    interview_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("interviews.id"), nullable=False, index=True
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id"), nullable=False, index=True
    )

    role: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # interviewer, observer, coordinator

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class InterviewFeedback(Base):
    """Interviewer feedback and ratings."""

    __tablename__ = "interview_feedback"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )

    interview_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("interviews.id"), nullable=False, index=True
    )
    interviewer_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id"), nullable=False, index=True
    )

    # Ratings (1-5 scale)
    overall_rating: Mapped[int | None] = mapped_column(Integer)
    technical_skills_rating: Mapped[int | None] = mapped_column(Integer)
    communication_rating: Mapped[int | None] = mapped_column(Integer)
    culture_fit_rating: Mapped[int | None] = mapped_column(Integer)
    problem_solving_rating: Mapped[int | None] = mapped_column(Integer)

    # Feedback
    strengths: Mapped[str | None] = mapped_column(Text)
    weaknesses: Mapped[str | None] = mapped_column(Text)
    overall_feedback: Mapped[str | None] = mapped_column(Text)
    recommendation: Mapped[str | None] = mapped_column(
        String(50)
    )  # strong_yes, yes, maybe, no, strong_no

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


class InterviewQuestion(Base):
    """Question bank for interviews."""

    __tablename__ = "interview_questions"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )

    organization_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("organizations.id"), nullable=False, index=True
    )

    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    question_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # technical, behavioral, situational, cultural
    difficulty_level: Mapped[str | None] = mapped_column(
        String(20)
    )  # easy, medium, hard
    expected_answer: Mapped[str | None] = mapped_column(Text)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    created_by: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id"), nullable=False
    )


class InterviewResponse(Base):
    """Candidate responses to interview questions."""

    __tablename__ = "interview_responses"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )

    interview_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("interviews.id"), nullable=False, index=True
    )
    question_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("interview_questions.id"), nullable=False, index=True
    )

    response_text: Mapped[str | None] = mapped_column(Text)
    response_rating: Mapped[int | None] = mapped_column(Integer)  # 1-5
    interviewer_notes: Mapped[str | None] = mapped_column(Text)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class InterviewAIInsight(Base):
    """AI-generated insights from interviews."""

    __tablename__ = "interview_ai_insights"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )

    interview_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("interviews.id"), nullable=False, index=True
    )

    insight_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # summary, strength, weakness, recommendation
    insight_text: Mapped[str] = mapped_column(Text, nullable=False)
    confidence_score: Mapped[float | None] = mapped_column(Numeric(5, 4))

    # AI model
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)

    # Timestamps
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
