from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, BigInteger, DateTime, func, Text, Boolean, ForeignKey, JSON, Enum as SQLEnum
from database.engine import Base
from datetime import datetime
from enum import Enum as PyEnum


class MessageStatus(str, PyEnum):
    """Message delivery status."""
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"


class EmailTemplate(Base):
    """Reusable email templates."""
    __tablename__ = "email_templates"
    
    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )
    
    organization_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("organizations.id"), nullable=False, index=True
    )
    
    # Template details
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    template_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # application_received, interview_invite, rejection, offer
    subject: Mapped[str] = mapped_column(String(500), nullable=False)
    body_html: Mapped[str] = mapped_column(Text, nullable=False)
    body_text: Mapped[str | None] = mapped_column(Text)
    
    # Variables (JSON list of available variables)
    available_variables: Mapped[list | None] = mapped_column(JSON)
    
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
    created_by: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)


class Message(Base):
    """Communication history between users and candidates."""
    __tablename__ = "messages"
    
    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )
    
    # Sender and recipient
    sender_type: Mapped[str] = mapped_column(String(20), nullable=False)  # user, candidate, system
    sender_id: Mapped[int | None] = mapped_column(BigInteger, index=True)
    recipient_type: Mapped[str] = mapped_column(String(20), nullable=False)
    recipient_id: Mapped[int | None] = mapped_column(BigInteger, index=True)
    
    # Message details
    message_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # email, sms, in_app, system
    subject: Mapped[str | None] = mapped_column(String(500))
    body: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Context
    application_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("applicants.id"), index=True
    )
    job_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("jobs.id"), index=True
    )
    
    # Status
    status: Mapped[MessageStatus] = mapped_column(
        SQLEnum(MessageStatus, name="message_status"),
        default=MessageStatus.PENDING,
        nullable=False,
        index=True
    )
    
    # Timestamps
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class EmailLog(Base):
    """Email delivery tracking."""
    __tablename__ = "email_logs"
    
    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )
    
    message_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("messages.id"), index=True
    )
    
    # Email details
    to_email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    from_email: Mapped[str] = mapped_column(String(255), nullable=False)
    subject: Mapped[str] = mapped_column(String(500), nullable=False)
    
    # Delivery info
    provider: Mapped[str | None] = mapped_column(String(50))  # sendgrid, ses, mailgun
    provider_message_id: Mapped[str | None] = mapped_column(String(255), index=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    error_message: Mapped[str | None] = mapped_column(Text)
    
    # Tracking
    opened_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    clicked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    
    # Timestamps
    sent_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class Notification(Base):
    """System notifications for users."""
    __tablename__ = "notifications"
    
    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )
    
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id"), nullable=False, index=True
    )
    
    # Notification details
    notification_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # new_application, interview_scheduled, assessment_completed
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Context
    entity_type: Mapped[str | None] = mapped_column(String(50))
    entity_id: Mapped[int | None] = mapped_column(BigInteger)
    action_url: Mapped[str | None] = mapped_column(String(500))
    
    # Status
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class NotificationPreference(Base):
    """User notification settings."""
    __tablename__ = "notification_preferences"
    
    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )
    
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id"), unique=True, nullable=False, index=True
    )
    
    # Channel preferences
    email_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    push_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sms_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    in_app_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    # Notification type preferences (JSON)
    notification_settings: Mapped[dict | None] = mapped_column(JSON)
    
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
