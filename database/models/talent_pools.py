"""
Talent Pools Module

Candidate pools for sourcing and nurturing future hires.
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
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from database.models.candidates import Candidate
    from database.models.jobs import Job
    from database.models.organizations import Organization


# ==================== Enums ===================== #
class PoolType(str, PyEnum):
    """Type of talent pool."""

    GENERAL = "general"
    JOB_SPECIFIC = "job_specific"
    SILVER_MEDALIST = "silver_medalist"  # Good candidates who didn't get hired
    ALUMNI = "alumni"
    REFERRAL = "referral"
    SOURCED = "sourced"
    EVENT = "event"
    UNIVERSITY = "university"
    CUSTOM = "custom"


class MemberStatus(str, PyEnum):
    """Status of pool member."""

    ACTIVE = "active"
    ENGAGED = "engaged"
    UNRESPONSIVE = "unresponsive"
    OPTED_OUT = "opted_out"
    HIRED = "hired"
    ARCHIVED = "archived"


class PoolCampaignStatus(str, PyEnum):
    """Status of pool campaign."""

    DRAFT = "draft"
    SCHEDULED = "scheduled"
    SENDING = "sending"
    COMPLETED = "completed"
    PAUSED = "paused"
    CANCELLED = "cancelled"


class PoolCampaignType(str, PyEnum):
    """Type of pool campaign."""

    JOB_ALERT = "job_alert"
    NURTURE = "nurture"
    EVENT_INVITE = "event_invite"
    NEWSLETTER = "newsletter"
    RE_ENGAGEMENT = "re_engagement"
    SURVEY = "survey"


# ==================== TalentPool Model ===================== #
@audit_changes
class TalentPool(Base):
    """
    Saved candidate pool for future opportunities.
    """

    __tablename__ = "talent_pools"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )
    organization_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Pool info
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    pool_type: Mapped[PoolType] = mapped_column(
        SQLEnum(PoolType, native_enum=False, length=50),
        nullable=False,
        default=PoolType.GENERAL,
    )

    # Criteria (for auto-population)
    auto_populate: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    filter_criteria: Mapped[dict[str, Any] | None] = mapped_column(
        JSON
    )  # Skills, location, etc.
    job_ids: Mapped[list[int] | None] = mapped_column(JSON)  # Related jobs

    # Settings
    is_public: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    allow_self_add: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Stats (denormalized for performance)
    member_count: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    engaged_count: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)

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
    members: Mapped[list["TalentPoolMember"]] = relationship(
        "TalentPoolMember", back_populates="pool", cascade="all, delete-orphan"
    )
    campaigns: Mapped[list["TalentPoolCampaign"]] = relationship(
        "TalentPoolCampaign", back_populates="pool", cascade="all, delete-orphan"
    )
    organization: Mapped["Organization"] = relationship(
        "Organization", back_populates="talent_pools"
    )

    # Indexes
    __table_args__ = (
        Index("idx_talent_pool_org", "organization_id"),
        Index("idx_talent_pool_type", "pool_type"),
        Index("idx_talent_pool_active", "is_active"),
        # Indexes for counter-based sorting/filtering
        Index("idx_talent_pool_member_count", "member_count"),
        Index("idx_talent_pool_engaged_count", "engaged_count"),
        # Partial index for active pools
        Index(
            "idx_talent_pool_active_org",
            "organization_id",
            "created_at",
            postgresql_where="is_active = true"
        ),
        # GIN index for JSON filter criteria
        Index(
            "idx_talent_pool_filter_gin",
            "filter_criteria",
            postgresql_using="gin"
        ),
    )


# ==================== TalentPoolMember Model ===================== #
@audit_changes
class TalentPoolMember(Base):
    """
    Candidate membership in a talent pool.
    """

    __tablename__ = "talent_pool_members"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )
    pool_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("talent_pools.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    candidate_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("candidates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Status
    status: Mapped[MemberStatus] = mapped_column(
        SQLEnum(MemberStatus, native_enum=False, length=50),
        nullable=False,
        default=MemberStatus.ACTIVE,
    )

    # Source
    added_by: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.id"))
    source: Mapped[str | None] = mapped_column(String(100))  # How added
    source_application_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("applications.id")
    )

    # Tags and notes
    tags: Mapped[list[str] | None] = mapped_column(JSON)
    notes: Mapped[str | None] = mapped_column(Text)
    rating: Mapped[int | None] = mapped_column(BigInteger)  # 1-5

    # Engagement tracking
    last_contacted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    email_opens: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    email_clicks: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)

    # Opt-out
    opted_out_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    opt_out_reason: Mapped[str | None] = mapped_column(String(255))

    # Timestamps
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    pool: Mapped["TalentPool"] = relationship("TalentPool", back_populates="members")
    candidate: Mapped["Candidate"] = relationship(
        "Candidate", back_populates="talent_pool_memberships"
    )

    # Unique constraint
    __table_args__ = (
        UniqueConstraint("pool_id", "candidate_id", name="uq_pool_candidate"),
        Index("idx_pool_member_status", "pool_id", "status"),
    )


# ==================== TalentPoolCampaign Model ===================== #
@audit_changes
class TalentPoolCampaign(Base):
    """
    Outreach campaign to talent pool members.
    """

    __tablename__ = "talent_pool_campaigns"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )
    pool_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("talent_pools.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
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
    campaign_type: Mapped[PoolCampaignType] = mapped_column(
        SQLEnum(PoolCampaignType, native_enum=False, length=50),
        nullable=False,
    )
    status: Mapped[PoolCampaignStatus] = mapped_column(
        SQLEnum(PoolCampaignStatus, native_enum=False, length=50),
        nullable=False,
        default=PoolCampaignStatus.DRAFT,
    )

    # Content
    subject: Mapped[str] = mapped_column(String(500), nullable=False)
    email_template_id: Mapped[int | None] = mapped_column(BigInteger)
    email_content: Mapped[str | None] = mapped_column(Text)

    # Related job (for job alerts)
    job_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("jobs.id")
    )

    # Targeting
    target_filter: Mapped[dict[str, Any] | None] = mapped_column(
        JSON
    )  # Additional filters
    exclude_recently_contacted_days: Mapped[int | None] = mapped_column(BigInteger)

    # Schedule
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Stats
    total_recipients: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    sent_count: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    delivered_count: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    opened_count: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    clicked_count: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    applied_count: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)

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
    pool: Mapped["TalentPool"] = relationship(
        "TalentPool", back_populates="campaigns"
    )
    job: Mapped["Job | None"] = relationship(
        "Job", back_populates="talent_pool_campaigns"
    )
