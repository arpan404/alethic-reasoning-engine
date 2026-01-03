from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, BigInteger, DateTime, func, Text, Boolean, ForeignKey, JSON
from database.engine import Base
from datetime import datetime


class ChatSession(Base):
    """Chat session metadata for candidate-recruiter or AI conversations."""
    __tablename__ = "chat_sessions"
    
    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )
    
    # Session identification
    session_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    session_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # candidate_recruiter, ai_screening, ai_interview
    
    # Relationships
    candidate_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("candidates.id"), index=True
    )
    application_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("applicants.id"), index=True
    )
    job_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("jobs.id"), index=True
    )
    
    # Session metadata
    title: Mapped[str | None] = mapped_column(String(500))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    # AI agent info (if applicable)
    ai_agent_name: Mapped[str | None] = mapped_column(String(100))
    ai_agent_config: Mapped[dict | None] = mapped_column(JSON)
    
    # Timestamps
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_message_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class ChatMessage(Base):
    """Individual messages in chat conversations."""
    __tablename__ = "chat_messages"
    
    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )
    
    session_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("chat_sessions.id"), nullable=False, index=True
    )
    
    # Message content
    message_content: Mapped[str] = mapped_column(Text, nullable=False)
    message_type: Mapped[str] = mapped_column(
        String(50), default="text", nullable=False
    )  # text, system, attachment, action
    
    # Sender info
    sender_type: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # user, candidate, ai, system
    sender_id: Mapped[int | None] = mapped_column(BigInteger, index=True)
    sender_name: Mapped[str | None] = mapped_column(String(255))
    
    # AI-specific metadata
    ai_model: Mapped[str | None] = mapped_column(String(100))
    ai_confidence: Mapped[float | None] = mapped_column(JSON)
    ai_metadata: Mapped[dict | None] = mapped_column(JSON)
    
    # Message metadata
    is_edited: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Timestamps
    sent_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    edited_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class ChatParticipant(Base):
    """Session participants tracking."""
    __tablename__ = "chat_participants"
    
    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )
    
    session_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("chat_sessions.id"), nullable=False, index=True
    )
    
    # Participant info
    participant_type: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # user, candidate, ai
    participant_id: Mapped[int | None] = mapped_column(BigInteger, index=True)
    participant_name: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    
    # Timestamps
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    left_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ChatAttachment(Base):
    """Files shared in chat conversations."""
    __tablename__ = "chat_attachments"
    
    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )
    
    message_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("chat_messages.id"), nullable=False, index=True
    )
    file_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("files.id"), nullable=False, index=True
    )
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
