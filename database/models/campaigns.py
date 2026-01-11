"""
Campaigns Module

Email campaigns for candidate outreach and engagement.
"""

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
    Enum as SQLEnum,
    Index,
    UniqueConstraint,
)
from database.engine import Base
from database.security import audit_changes
from datetime import datetime
from enum import Enum as PyEnum
from typing import Any


# ==================== Enums ===================== #
class CampaignStatus(str, PyEnum):
    """Status of email campaign."""

    DRAFT = "draft"
    SCHEDULED = "scheduled"
    SENDING = "sending"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"


class CampaignType(str, PyEnum):
    """Type of campaign."""

    JOB_ALERT = "job_alert"
    NURTURE = "nurture"
    RE_ENGAGEMENT = "re_engagement"
    EVENT_INVITE = "event_invite"
    NEWSLETTER = "newsletter"
    SURVEY = "survey"
    ANNOUNCEMENT = "announcement"
    CUSTOM = "custom"


class RecipientStatus(str, PyEnum):
    """Status of campaign recipient."""

    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    OPENED = "opened"
    CLICKED = "clicked"
    BOUNCED = "bounced"
    UNSUBSCRIBED = "unsubscribed"
    COMPLAINED = "complained"
    FAILED = "failed"


# ==================== CampaignTemplate Model ===================== #
@audit_changes
class CampaignTemplate(Base):
    """
    Reusable email templates for campaigns.
    """

    __tablename__ = "campaign_templates"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )
    organization_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Template info
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    campaign_type: Mapped[CampaignType] = mapped_column(
        SQLEnum(CampaignType, native_enum=False, length=50),
        nullable=False,
    )

    # Content
    subject: Mapped[str] = mapped_column(String(500), nullable=False)
    preview_text: Mapped[str | None] = mapped_column(String(255))
    html_content: Mapped[str] = mapped_column(Text, nullable=False)
    text_content: Mapped[str | None] = mapped_column(Text)

    # Variables
    available_variables: Mapped[list[str] | None] = mapped_column(
        JSON
    )  # {{first_name}}, {{job_title}}, etc.

    # Settings
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
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


# ==================== EmailCampaign Model ===================== #
@audit_changes
class EmailCampaign(Base):
    """
    Email campaign for candidate outreach.
    """

    __tablename__ = "email_campaigns"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )
    organization_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Campaign info
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    campaign_type: Mapped[CampaignType] = mapped_column(
        SQLEnum(CampaignType, native_enum=False, length=50),
        nullable=False,
    )
    status: Mapped[CampaignStatus] = mapped_column(
        SQLEnum(CampaignStatus, native_enum=False, length=50),
        nullable=False,
        default=CampaignStatus.DRAFT,
        index=True,
    )

    # Template
    template_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("campaign_templates.id")
    )

    # Content (can override template)
    subject: Mapped[str] = mapped_column(String(500), nullable=False)
    preview_text: Mapped[str | None] = mapped_column(String(255))
    html_content: Mapped[str] = mapped_column(Text, nullable=False)
    text_content: Mapped[str | None] = mapped_column(Text)

    # Sender
    from_name: Mapped[str | None] = mapped_column(String(255))
    from_email: Mapped[str | None] = mapped_column(String(255))
    reply_to: Mapped[str | None] = mapped_column(String(255))

    # Targeting
    talent_pool_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("talent_pools.id")
    )
    job_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("jobs.id")
    )
    target_criteria: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    exclude_recently_emailed_days: Mapped[int | None] = mapped_column(BigInteger)

    # Schedule
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    send_timezone: Mapped[str | None] = mapped_column(String(50))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Stats
    total_recipients: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    sent_count: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    delivered_count: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    opened_count: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    unique_opens: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    clicked_count: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    unique_clicks: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    bounced_count: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    unsubscribed_count: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    complained_count: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)

    # Conversion tracking
    applied_count: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    hired_count: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)

    # A/B testing
    is_ab_test: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    ab_test_variants: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON)
    winning_variant: Mapped[str | None] = mapped_column(String(50))

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

    # Relationships
    recipients: Mapped[list["CampaignRecipient"]] = relationship(
        "CampaignRecipient", back_populates="campaign", cascade="all, delete-orphan"
    )

    # Indexes
    __table_args__ = (
        Index("idx_campaign_status", "organization_id", "status"),
    )


# ==================== CampaignRecipient Model ===================== #
@audit_changes
class CampaignRecipient(Base):
    """
    Individual recipient of a campaign.
    """

    __tablename__ = "campaign_recipients"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )
    campaign_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("email_campaigns.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    candidate_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("candidates.id", ondelete="SET NULL"),
        index=True,
    )

    # Recipient info
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    first_name: Mapped[str | None] = mapped_column(String(100))
    last_name: Mapped[str | None] = mapped_column(String(100))

    # Personalization data
    merge_data: Mapped[dict[str, Any] | None] = mapped_column(JSON)

    # A/B test variant
    variant: Mapped[str | None] = mapped_column(String(50))

    # Status
    status: Mapped[RecipientStatus] = mapped_column(
        SQLEnum(RecipientStatus, native_enum=False, length=50),
        nullable=False,
        default=RecipientStatus.PENDING,
        index=True,
    )

    # Delivery
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    message_id: Mapped[str | None] = mapped_column(String(255))

    # Engagement
    opened_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    open_count: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    clicked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    click_count: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    clicked_links: Mapped[list[str] | None] = mapped_column(JSON)

    # Issues
    bounced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    bounce_type: Mapped[str | None] = mapped_column(String(50))
    bounce_reason: Mapped[str | None] = mapped_column(Text)
    unsubscribed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    complained_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Error
    error_message: Mapped[str | None] = mapped_column(Text)
    retry_count: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)

    # Conversion
    applied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    application_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("applications.id")
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

    # Relationships
    campaign: Mapped["EmailCampaign"] = relationship(
        "EmailCampaign", back_populates="recipients"
    )

    # Unique constraint
    __table_args__ = (
        UniqueConstraint("campaign_id", "email", name="uq_campaign_recipient"),
        Index("idx_recipient_status", "campaign_id", "status"),
    )
