from typing import Literal, TypedDict, Union, Any
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import (
    String,
    Boolean,
    ForeignKey,
    BigInteger,
    DateTime,
    Text,
    func,
    JSON,
    Enum as SQLEnum,
)
from database.engine import Base
from datetime import datetime
from enum import Enum as PyEnum
from sqlalchemy.dialects.postgresql import ARRAY
from database.security import audit_changes


# ============ Message Enum & Types =============== #
class MessageStatus(str, PyEnum):
    """Message delivery status."""

    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    VIEWED = "viewed"
    FAILED = "failed"


class MessageSender(str, PyEnum):
    """Message sender type."""

    RECRUITER = "recruiter"
    SYSTEM = "system"
    CANDIDATE = "candidate"


class MessageType(str, PyEnum):
    """Message type."""

    EMAIL = "email"
    SMS = "sms"
    IN_APP = "in_app"


class MessageContent(TypedDict):
    """Structure for message content."""

    subject: str
    body_text: str
    body_html: str


# ============ Template Enums & Types =============== #
class EmailTemplateType(str, PyEnum):
    """Types of email templates."""

    APPLICATION_RECEIVED = "application_received"
    INTERVIEW_INVITE = "interview_invite"
    INTERVIEW_REMINDER = "interview_reminder"
    REJECTION = "rejection"
    OFFER = "offer"
    WELCOME = "welcome"
    PASSWORD_RESET = "password_reset"
    VERIFICATION = "verification"
    CUSTOM = "custom"


class EmailProvider(str, PyEnum):
    """Email service providers."""

    SENDGRID = "sendgrid"
    SES = "ses"
    MAILGUN = "mailgun"
    POSTMARK = "postmark"
    RESEND = "resend"


class TemplateConfigType(TypedDict):
    """Configuration for email templates."""

    type: Union[Literal["subject"], Literal["body_html"], Literal["body_text"]]
    placeholder_variables: list[str]  # List of placeholder variable names
    description: str  # Description of the template purpose
    template_string: str  # The actual template string with placeholders


# ============ Email Template Model =============== #
@audit_changes
class EmailTemplate(Base):
    """
    Reusable email templates.
    Created templated can be used for various communcation purposes.
    Organizations can create and manage their own templates too.
    """

    __tablename__ = "email_templates"
    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )
    organization_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("organizations.id"), nullable=True, index=True
    )  # if null, template is global and can be used by any organization in the alethic system

    # Template details
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    template_type: Mapped[EmailTemplateType] = mapped_column(
        SQLEnum(EmailTemplateType, native_enum=False, length=50),
        nullable=False,
        index=True,
    )
    template_data: Mapped[list[TemplateConfigType]] = mapped_column(
        JSON
    )  # JSON field storing subject, body_html, body_text with placeholders

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # audit metadata
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
    updated_by: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id"), nullable=False
    )


# ============ Message Model =============== #
@audit_changes
class Message(Base):
    """
    Communication history between recruiters/users and candidates.
    """

    __tablename__ = "messages"
    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )

    sender_type: Mapped[MessageSender] = mapped_column(
        SQLEnum(MessageSender, native_enum=False, length=50), nullable=False
    )
    sender_id: Mapped[int | None] = mapped_column(BigInteger, index=True)
    recipient_type: Mapped[MessageSender] = mapped_column(
        SQLEnum(MessageSender, native_enum=False, length=50), nullable=False
    )
    recipient_id: Mapped[int | None] = mapped_column(BigInteger, index=True)

    # Message details
    message_type: Mapped[MessageType] = mapped_column(
        SQLEnum(MessageType, native_enum=False, length=50), nullable=False
    )

    # Context
    application_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("applications.id"), index=True
    )
    job_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("jobs.id"), index=True
    )
    message_content: Mapped[MessageContent] = mapped_column(JSON, nullable=False)

    # Status
    status: Mapped[MessageStatus] = mapped_column(
        SQLEnum(MessageStatus, native_enum=False, length=50),
        nullable=False,
        default=MessageStatus.PENDING,
    )

    # timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Relationships
    delivery_logs: Mapped[list["EmailDeliverLog"]] = relationship(
        "EmailDeliverLog", back_populates="message", cascade="all, delete-orphan"
    )


# ============ Email Deliver Log =============== #
@audit_changes
class EmailDeliverLog(Base):
    """
    Logs for email delivery status and errors.
    """

    __tablename__ = "email_delivery_logs"
    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )
    message_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("messages.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Delivery status
    delivery_status: Mapped[MessageStatus] = mapped_column(
        SQLEnum(MessageStatus, native_enum=False, length=50), nullable=False
    )
    error_code: Mapped[str | None] = mapped_column(String(100))
    error_message: Mapped[str | None] = mapped_column(Text)

    # Email details
    to_email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    from_email: Mapped[str] = mapped_column(String(255), nullable=False)
    subject: Mapped[str] = mapped_column(String(500), nullable=False)
    cc_email: Mapped[list[str] | None] = mapped_column(ARRAY(String(255)))
    bcc_email: Mapped[list[str] | None] = mapped_column(ARRAY(String(255)))

    # Provider info
    provider: Mapped[EmailProvider | None] = mapped_column(
        SQLEnum(EmailProvider, native_enum=False, length=50)
    )
    provider_message_id: Mapped[str | None] = mapped_column(String(255), index=True)

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
    message: Mapped["Message"] = relationship("Message", back_populates="delivery_logs")


# ============ Notification Model =============== #
class NotificationType(str, PyEnum):
    """Types of notifications."""

    SYSTEM = "system"
    APPLICATION = "application"
    INTERVIEW = "interview"
    OFFER = "offer"
    MESSAGE = "message"
    REMINDER = "reminder"


@audit_changes
class Notification(Base):
    """System notifications for users."""

    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Notification details
    notification_type: Mapped[NotificationType] = mapped_column(
        SQLEnum(NotificationType, native_enum=False, length=50),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)

    # Context
    entity_type: Mapped[str | None] = mapped_column(String(50))
    entity_id: Mapped[int | None] = mapped_column(BigInteger)
    action_url: Mapped[str | None] = mapped_column(String(500))

    # Status - single definition (removed duplicate)
    is_read: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, index=True
    )

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


@audit_changes
class NotificationPreference(Base):
    """User notification settings."""

    __tablename__ = "notification_preferences"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )

    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    # Preferences
    email_notifications: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    sms_notifications: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    in_app_notifications: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    push_notifications: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )

    # Notification types preferences (JSON)
    notification_settings: Mapped[dict[str, Any] | None] = mapped_column(JSON)

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
