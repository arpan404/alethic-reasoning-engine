from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import (
    String,
    BigInteger,
    DateTime,
    func,
    Text,
    ForeignKey,
    JSON,
    Enum as SQLEnum,
)
from database.engine import Base
from datetime import datetime
from enum import Enum as PyEnum


class AuditAction(str, PyEnum):
    """Audit action types."""

    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    VIEW = "view"
    EXPORT = "export"


class AuditLog(Base):
    """Complete audit trail for all system actions."""

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
        SQLEnum(AuditAction, name="audit_action"), nullable=False, index=True
    )
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    entity_id: Mapped[int | None] = mapped_column(BigInteger, index=True)

    # Details
    description: Mapped[str | None] = mapped_column(Text)
    changes: Mapped[dict | None] = mapped_column(JSON)  # Before/after values
    metadata: Mapped[dict | None] = mapped_column(JSON)

    # Request context
    ip_address: Mapped[str | None] = mapped_column(String(45))
    user_agent: Mapped[str | None] = mapped_column(Text)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )


class StatusHistory(Base):
    """Application status change history."""

    __tablename__ = "status_history"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )

    application_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("applicants.id"), nullable=False, index=True
    )

    # Status change
    from_status: Mapped[str | None] = mapped_column(String(100))
    to_status: Mapped[str] = mapped_column(String(100), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text)

    # Actor
    changed_by: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id"), index=True
    )

    # Timestamps
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class AIDecisionLog(Base):
    """Track AI-made decisions for transparency and compliance."""

    __tablename__ = "ai_decision_logs"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )

    # Decision context
    decision_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # screening, scoring, recommendation, rejection
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)

    # AI model info
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    model_version: Mapped[str | None] = mapped_column(String(50))

    # Decision details
    decision: Mapped[str] = mapped_column(Text, nullable=False)
    confidence_score: Mapped[float | None] = mapped_column(JSON)
    reasoning: Mapped[str | None] = mapped_column(Text)
    input_data: Mapped[dict | None] = mapped_column(JSON)
    output_data: Mapped[dict | None] = mapped_column(JSON)

    # Human review
    reviewed_by: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id"), index=True
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    review_outcome: Mapped[str | None] = mapped_column(
        String(50)
    )  # approved, rejected, modified

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class DataRetentionPolicy(Base):
    """Compliance policies for data retention."""

    __tablename__ = "data_retention_policies"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )

    organization_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("organizations.id"), nullable=False, index=True
    )

    # Policy details
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    retention_days: Mapped[int] = mapped_column(BigInteger, nullable=False)
    auto_delete: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

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


class GDPRRequest(Base):
    """Data privacy requests (GDPR, CCPA compliance)."""

    __tablename__ = "gdpr_requests"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )

    # Requester
    candidate_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("candidates.id"), index=True
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    # Request details
    request_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # access, deletion, portability, rectification
    status: Mapped[str] = mapped_column(
        String(50), default="pending", nullable=False, index=True
    )  # pending, in_progress, completed, rejected

    # Processing
    processed_by: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id"), index=True
    )
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    notes: Mapped[str | None] = mapped_column(Text)

    # Timestamps
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
