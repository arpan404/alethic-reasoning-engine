from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, BigInteger, DateTime, func, Text, Boolean, ForeignKey, Numeric, Enum as SQLEnum
from database.engine import Base
from datetime import datetime
from enum import Enum as PyEnum


class JobStatus(str, PyEnum):
    """Job posting status."""
    DRAFT = "draft"
    OPEN = "open"
    CLOSED = "closed"
    ON_HOLD = "on_hold"
    CANCELLED = "cancelled"


class JobType(str, PyEnum):
    """Job employment type."""
    FULL_TIME = "full_time"
    PART_TIME = "part_time"
    CONTRACT = "contract"
    INTERNSHIP = "internship"
    TEMPORARY = "temporary"


class Job(Base):
    """Job postings with vector embeddings for semantic search."""
    __tablename__ = "jobs"
    
    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )
    
    # Basic info
    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    requirements: Mapped[str | None] = mapped_column(Text)
    responsibilities: Mapped[str | None] = mapped_column(Text)
    benefits: Mapped[str | None] = mapped_column(Text)
    
    # Job details
    job_type: Mapped[JobType] = mapped_column(
        SQLEnum(JobType, name="job_type"),
        nullable=False
    )
    status: Mapped[JobStatus] = mapped_column(
        SQLEnum(JobStatus, name="job_status"),
        default=JobStatus.DRAFT,
        nullable=False,
        index=True
    )
    
    # Compensation
    salary_min: Mapped[int | None] = mapped_column(BigInteger)
    salary_max: Mapped[int | None] = mapped_column(BigInteger)
    salary_currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    
    # Organization
    organization_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("organizations.id"), nullable=False, index=True
    )
    department_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("job_departments.id"), index=True
    )
    hiring_manager_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id"), index=True
    )
    
    # Posting details
    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    closes_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    
    # AI features
    enable_ai_screening: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    ai_screening_threshold: Mapped[float | None] = mapped_column(Numeric(3, 2))  # 0.00 to 1.00
    
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
    created_by: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)
    updated_by: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)


class JobDepartment(Base):
    """Department information for job organization."""
    __tablename__ = "job_departments"
    
    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )
    organization_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("organizations.id"), nullable=False, index=True
    )
    
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    
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


class JobRequirement(Base):
    """Specific job requirements (skills, experience, education)."""
    __tablename__ = "job_requirements"
    
    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )
    job_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("jobs.id"), nullable=False, index=True
    )
    
    requirement_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # skill, experience, education, certification
    requirement_value: Mapped[str] = mapped_column(String(500), nullable=False)
    is_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class JobLocation(Base):
    """Job location details supporting remote/hybrid/onsite."""
    __tablename__ = "job_locations"
    
    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )
    job_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("jobs.id"), nullable=False, index=True
    )
    
    location_type: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # remote, onsite, hybrid
    
    # Address (nullable for remote positions)
    city: Mapped[str | None] = mapped_column(String(100))
    state: Mapped[str | None] = mapped_column(String(100))
    country: Mapped[str] = mapped_column(String(100), nullable=False)
    postal_code: Mapped[str | None] = mapped_column(String(20))
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
