from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import (
    String,
    BigInteger,
    DateTime,
    func,
    Text,
    ForeignKey,
    Numeric,
    JSON,
)
from database.engine import Base
from datetime import datetime


class AIEvaluation(Base):
    """AI-powered candidate evaluations and scoring."""

    __tablename__ = "ai_evaluations"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )

    # Relationships
    candidate_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("candidates.id"), nullable=False, index=True
    )
    application_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("applicants.id"), index=True
    )
    job_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("jobs.id"), index=True
    )

    # Evaluation details
    evaluation_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # resume_screening, skill_match, culture_fit, overall

    # Scores (0.00 to 1.00)
    overall_score: Mapped[float] = mapped_column(Numeric(5, 4), nullable=False)
    confidence_score: Mapped[float | None] = mapped_column(Numeric(5, 4))

    # AI model info
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    model_version: Mapped[str | None] = mapped_column(String(50))

    # Results
    summary: Mapped[str | None] = mapped_column(Text)
    strengths: Mapped[str | None] = mapped_column(Text)
    weaknesses: Mapped[str | None] = mapped_column(Text)
    recommendations: Mapped[str | None] = mapped_column(Text)

    # Metadata
    evaluation_metadata: Mapped[dict | None] = mapped_column(JSON)

    # Timestamps
    evaluated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class EvaluationCriteria(Base):
    """Configurable evaluation criteria for AI assessments."""

    __tablename__ = "evaluation_criteria"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )

    job_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("jobs.id"), index=True
    )
    organization_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("organizations.id"), nullable=False, index=True
    )

    # Criteria details
    criteria_name: Mapped[str] = mapped_column(String(200), nullable=False)
    criteria_description: Mapped[str | None] = mapped_column(Text)
    weight: Mapped[float] = mapped_column(Numeric(3, 2), nullable=False)  # 0.00 to 1.00

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


class EvaluationScore(Base):
    """Detailed scoring breakdown for evaluations."""

    __tablename__ = "evaluation_scores"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )

    evaluation_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("ai_evaluations.id"), nullable=False, index=True
    )
    criteria_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("evaluation_criteria.id"), nullable=False, index=True
    )

    # Score details
    score: Mapped[float] = mapped_column(Numeric(5, 4), nullable=False)
    reasoning: Mapped[str | None] = mapped_column(Text)
    evidence: Mapped[str | None] = mapped_column(Text)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class ResumeAnalysis(Base):
    """AI-parsed resume data and insights."""

    __tablename__ = "resume_analysis"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )

    candidate_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("candidates.id"), nullable=False, index=True
    )
    file_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("files.id"), nullable=False, index=True
    )

    # Parsed data (structured JSON)
    parsed_data: Mapped[dict] = mapped_column(JSON, nullable=False)

    # Extracted entities
    skills_extracted: Mapped[list | None] = mapped_column(JSON)
    experience_years: Mapped[int | None] = mapped_column(BigInteger)
    education_level: Mapped[str | None] = mapped_column(String(100))

    # AI insights
    key_highlights: Mapped[str | None] = mapped_column(Text)
    red_flags: Mapped[str | None] = mapped_column(Text)

    # Processing info
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    processing_time_ms: Mapped[int | None] = mapped_column(BigInteger)

    # Timestamps
    analyzed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class SkillMatching(Base):
    """AI-powered skill matching between candidates and jobs."""

    __tablename__ = "skill_matching"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )

    candidate_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("candidates.id"), nullable=False, index=True
    )
    job_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("jobs.id"), nullable=False, index=True
    )

    # Matching scores
    overall_match_score: Mapped[float] = mapped_column(Numeric(5, 4), nullable=False)
    skills_match_score: Mapped[float] = mapped_column(Numeric(5, 4), nullable=False)
    experience_match_score: Mapped[float] = mapped_column(Numeric(5, 4), nullable=False)

    # Detailed matching
    matched_skills: Mapped[list | None] = mapped_column(JSON)
    missing_skills: Mapped[list | None] = mapped_column(JSON)
    transferable_skills: Mapped[list | None] = mapped_column(JSON)

    # Timestamps
    matched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
