from sqlalchemy.orm import mapped_column, Mapped
from sqlalchemy import String, ForeignKey, JSON, DateTime, func, BigInteger, Numeric, Enum as SQLEnum
from database.engine import Base
from datetime import datetime
from enum import Enum as PyEnum


class ApplicationStatus(str, PyEnum):
    """Application status enum."""
    NEW = "new"
    SCREENING = "screening"
    INTERVIEW = "interview"
    OFFER = "offer"
    HIRED = "hired"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"


class Applications(Base):
    __tablename__: str = "applicants"
    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )
    job_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("jobs.id"), nullable=False)
    candidate_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("candidates.id"), nullable=False
    )
    status: Mapped[ApplicationStatus] = mapped_column(
        SQLEnum(ApplicationStatus, name="application_status"),
        default=ApplicationStatus.NEW,
        nullable=False,
        index=True
    )
    resume: Mapped[int] = mapped_column(BigInteger, ForeignKey("files.id"))
    cover_letter: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("files.id"))
    application_data: Mapped[dict] = mapped_column(JSON, nullable=True, default={})
    application_metadata: Mapped[dict] = mapped_column(JSON, nullable=True, default={})
    applied_at: Mapped[str] = mapped_column(String(100), nullable=False)
    
    # AI screening scores
    ai_screening_score: Mapped[float | None] = mapped_column(Numeric(5, 4))  # 0.00 to 1.00
    ai_screening_status: Mapped[str | None] = mapped_column(String(50))  # pending, completed, failed
    ai_recommendation: Mapped[str | None] = mapped_column(String(50))  # strong_match, match, weak_match, no_match
    
    # Source tracking
    source: Mapped[str | None] = mapped_column(String(100))  # job_board, referral, direct, linkedin
    applied_at: Mapped[str] = mapped_column(String(100), nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    updated_by: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)


class ApplicationNotes(Base):
    __tablename__: str = "application_notes"
    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )
    application_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("applicants.id"), nullable=False
    )
    note: Mapped[str] = mapped_column(String(2000), nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    created_by: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    updated_by: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)


class ApplicationTags(Base):
    __tablename__: str = "application_tags"
    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )
    application_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("applicants.id"), nullable=False
    )
    tag: Mapped[str] = mapped_column(String(100), nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    created_by: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    updated_by: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)


class ApplicationActivities(Base):
    __tablename__: str = "application_activities"
    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )
    application_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("applicants.id"), nullable=False
    )
    activity_type: Mapped[str] = mapped_column(String(100), nullable=False)
    activity_data: Mapped[dict] = mapped_column(JSON, nullable=True, default={})

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    created_by: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    updated_by: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)
