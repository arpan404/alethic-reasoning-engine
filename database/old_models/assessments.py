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
    JSON,
)
from database.engine import Base
from datetime import datetime


class Assessment(Base):
    """Assessment definitions for skills testing."""

    __tablename__ = "assessments"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )

    organization_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("organizations.id"), nullable=False, index=True
    )

    # Assessment details
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    assessment_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # coding, aptitude, personality, skills
    duration_minutes: Mapped[int | None] = mapped_column(Integer)
    passing_score: Mapped[float | None] = mapped_column(Numeric(5, 2))

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


class AssessmentQuestion(Base):
    """Assessment question bank."""

    __tablename__ = "assessment_questions"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )

    assessment_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("assessments.id"), nullable=False, index=True
    )

    # Question details
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    question_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # multiple_choice, coding, essay, true_false

    # Options (for multiple choice)
    options: Mapped[list | None] = mapped_column(JSON)
    correct_answer: Mapped[str | None] = mapped_column(Text)

    # Scoring
    points: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class CandidateAssessment(Base):
    """Assigned assessments to candidates."""

    __tablename__ = "candidate_assessments"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )

    candidate_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("candidates.id"), nullable=False, index=True
    )
    assessment_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("assessments.id"), nullable=False, index=True
    )
    application_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("applicants.id"), index=True
    )

    # Status
    status: Mapped[str] = mapped_column(
        String(50), default="assigned", nullable=False, index=True
    )  # assigned, in_progress, completed, expired

    # Timing
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class AssessmentResponse(Base):
    """Candidate responses to assessment questions."""

    __tablename__ = "assessment_responses"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )

    candidate_assessment_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("candidate_assessments.id"), nullable=False, index=True
    )
    question_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("assessment_questions.id"), nullable=False, index=True
    )

    # Response
    response_text: Mapped[str | None] = mapped_column(Text)
    response_data: Mapped[dict | None] = mapped_column(JSON)  # For structured responses

    # Scoring
    is_correct: Mapped[bool | None] = mapped_column(Boolean)
    points_earned: Mapped[int | None] = mapped_column(Integer)

    # Timestamps
    answered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class AssessmentResult(Base):
    """Scored results with AI analysis."""

    __tablename__ = "assessment_results"

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

    # Scores
    total_score: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    max_score: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    percentage_score: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    passed: Mapped[bool] = mapped_column(Boolean, nullable=False)

    # AI analysis
    ai_analysis: Mapped[str | None] = mapped_column(Text)
    strengths: Mapped[list | None] = mapped_column(JSON)
    weaknesses: Mapped[list | None] = mapped_column(JSON)
    recommendations: Mapped[str | None] = mapped_column(Text)

    # Timestamps
    scored_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
