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
)
from database.engine import Base
from database.security import ComplianceMixin, audit_changes
from database.security import (
    compliance_column,
    DataSensitivity,
    EncryptionType,
    GDPRDataCategory,
    DataRetentionPeriod,
)
from datetime import datetime
from enum import Enum as PyEnum
from typing import Any


# =================== Enums for Type Safety ===================
class ChatSessionType(str, PyEnum):
    """Types of chat sessions."""

    CANDIDATE_RECRUITER = "candidate_recruiter"
    AI_SCREENING = "ai_screening"
    AI_INTERVIEW = "ai_interview"
    AI_ASSISTANT = "ai_assistant"


class ChatMessageType(str, PyEnum):
    """Types of chat messages."""

    TEXT = "text"
    SYSTEM = "system"
    ATTACHMENT = "attachment"
    ACTION = "action"
    JSON = "json"  # For structured AI responses


class ChatParticipantType(str, PyEnum):
    """Types of chat participants."""

    USER = "user"
    CANDIDATE = "candidate"
    AI = "ai"


class ChatMessageStatus(str, PyEnum):
    """Status of a chat message."""

    PENDING = "pending"
    DELIVERED = "delivered"
    READ = "read"
    DELETED = "deleted"
    EDITED = "edited"


class ChatAttachmentType(str, PyEnum):
    """Types of chat attachments."""

    FILE = "file"
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    DOCUMENT = "document"
    LINK = "link"


class ChatSenderType(str, PyEnum):
    """Types of message senders."""

    USER = "user"
    CANDIDATE = "candidate"
    AI = "ai"
    SYSTEM = "system"


class AIResponseType(str, PyEnum):
    """Types of AI responses - for structured JSON data."""

    PLAIN_TEXT = "plain_text"
    STRUCTURED_DATA = "structured_data"
    CODE_BLOCK = "code_block"
    EVALUATION = "evaluation"
    QUESTION = "question"
    SUGGESTION = "suggestion"
    SUMMARY = "summary"


# ==================== Chat Session Model===================
@audit_changes
class ChatSession(Base, ComplianceMixin):
    """
    Chat session metadata for candidate-recruiter or AI conversations.
    """

    __tablename__ = "chat_sessions"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )

    # Session identification
    session_id: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, index=True
    )  # will be uuid
    session_type: Mapped[ChatSessionType] = mapped_column(
        SQLEnum(ChatSessionType, native_enum=False, length=50),
        nullable=False,
        index=True,
    )

    # relationships
    candidate_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("candidates.id"), index=True
    )
    application_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("applications.id"), index=True
    )
    job_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("jobs.id"), index=True
    )

    # AI evaluation sync
    ai_evaluation_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("ai_evaluations.id"), index=True
    )
    interview_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("interviews.id"), index=True
    )

    # session metadata
    title: Mapped[str | None] = mapped_column(String(500))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # ai agent info (if applicable)
    ai_agent_name: Mapped[str | None] = mapped_column(String(100))
    ai_agent_config: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    ai_agent_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSON)

    # timestamps
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_message_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Relationships
    messages: Mapped[list["ChatMessage"]] = relationship(
        "ChatMessage", back_populates="session", cascade="all, delete-orphan"
    )
    participants: Mapped[list["ChatParticipant"]] = relationship(
        "ChatParticipant", back_populates="session", cascade="all, delete-orphan"
    )


# ==================== Chat Message Model ===================
@audit_changes
class ChatMessage(Base, ComplianceMixin):
    """
    Individual messages in chat conversations.
    Supports both human text and AI JSON responses.
    """

    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )

    session_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("chat_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Message content - text or JSON stringified
    message_content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        info=compliance_column(
            sensitivity=DataSensitivity.CONFIDENTIAL,
            gdpr_relevant=True,
            gdpr_category=GDPRDataCategory.COMMUNICATIONS,
            retention_period=DataRetentionPeriod.YEARS_2,
            anonymize_on_delete=True,
        ),
    )
    message_type: Mapped[ChatMessageType] = mapped_column(
        SQLEnum(ChatMessageType, native_enum=False, length=50),
        default=ChatMessageType.TEXT,
        nullable=False,
    )

    # Sender info
    sender_type: Mapped[ChatSenderType] = mapped_column(
        SQLEnum(ChatSenderType, native_enum=False, length=50),
        nullable=False,
    )
    sender_id: Mapped[int | None] = mapped_column(BigInteger, index=True)
    sender_name: Mapped[str | None] = mapped_column(String(255))

    # AI-specific fields
    ai_model: Mapped[str | None] = mapped_column(String(100))  # e.g., "gpt-4", "claude"
    ai_confidence: Mapped[float | None] = mapped_column(Float)
    ai_response_type: Mapped[AIResponseType | None] = mapped_column(
        SQLEnum(AIResponseType, native_enum=False, length=50)
    )
    ai_structured_data: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        info=compliance_column(
            sensitivity=DataSensitivity.CONFIDENTIAL,
            gdpr_relevant=True,
            retention_period=DataRetentionPeriod.YEARS_2,
        ),
    )  # For AI JSON responses
    ai_metadata: Mapped[dict[str, Any] | None] = mapped_column(
        JSON
    )  # tokens used, latency, etc.

    # Reply threading
    reply_to_message_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("chat_messages.id"), index=True
    )

    # Message status
    status: Mapped[ChatMessageStatus] = mapped_column(
        SQLEnum(ChatMessageStatus, native_enum=False, length=50),
        default=ChatMessageStatus.DELIVERED,
        nullable=False,
    )
    is_edited: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Timestamps
    sent_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    edited_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Relationships
    session: Mapped["ChatSession"] = relationship(
        "ChatSession", back_populates="messages"
    )
    attachments: Mapped[list["ChatAttachment"]] = relationship(
        "ChatAttachment", back_populates="message", cascade="all, delete-orphan"
    )
    reply_to: Mapped["ChatMessage | None"] = relationship(
        "ChatMessage", remote_side=[id], foreign_keys=[reply_to_message_id]
    )


# ==================== Chat Participant Model ===================
@audit_changes
class ChatParticipant(Base, ComplianceMixin):
    """
    Session participants tracking.
    """

    __tablename__ = "chat_participants"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )

    session_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("chat_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Participant info - now type-safe
    participant_type: Mapped[ChatParticipantType] = mapped_column(
        SQLEnum(ChatParticipantType, native_enum=False, length=50),
        nullable=False,
    )
    participant_id: Mapped[int | None] = mapped_column(BigInteger, index=True)
    participant_name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_read_message_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("chat_messages.id")
    )

    # Timestamps
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    left_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Relationships
    session: Mapped["ChatSession"] = relationship(
        "ChatSession", back_populates="participants"
    )


# ==================== Chat Attachment Model ===================
class ChatAttachment(Base):
    """
    Files shared in chat conversations.
    """

    __tablename__ = "chat_attachments"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )

    message_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("chat_messages.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    file_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("files.id"), nullable=False, index=True
    )

    attachment_type: Mapped[ChatAttachmentType] = mapped_column(
        SQLEnum(ChatAttachmentType, native_enum=False, length=50),
        default=ChatAttachmentType.FILE,
        nullable=False,
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Relationships
    message: Mapped["ChatMessage"] = relationship(
        "ChatMessage", back_populates="attachments"
    )
