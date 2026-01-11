"""
Calendar Module

Calendar integration with Google Calendar and Outlook.
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
from database.security import ComplianceMixin, audit_changes
from database.security import (
    compliance_column,
    DataSensitivity,
    EncryptionType,
)
from datetime import datetime
from enum import Enum as PyEnum
from typing import Any


# ==================== Enums ===================== #
class CalendarProvider(str, PyEnum):
    """Calendar providers."""

    GOOGLE = "google"
    OUTLOOK = "outlook"
    OFFICE365 = "office365"
    APPLE = "apple"
    CALDAV = "caldav"


class EventStatus(str, PyEnum):
    """Calendar event status."""

    CONFIRMED = "confirmed"
    TENTATIVE = "tentative"
    CANCELLED = "cancelled"


class EventType(str, PyEnum):
    """Type of calendar event."""

    INTERVIEW = "interview"
    MEETING = "meeting"
    AVAILABILITY = "availability"
    BLOCKED = "blocked"
    OUT_OF_OFFICE = "out_of_office"


class SyncStatus(str, PyEnum):
    """Calendar sync status."""

    SYNCED = "synced"
    PENDING = "pending"
    FAILED = "failed"
    CONFLICT = "conflict"


# ==================== CalendarCredential Model ===================== #
@audit_changes
class CalendarCredential(Base, ComplianceMixin):
    """
    OAuth credentials for Google Calendar/Outlook per user.
    """

    __tablename__ = "calendar_credentials"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    organization_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Provider
    provider: Mapped[CalendarProvider] = mapped_column(
        SQLEnum(CalendarProvider, native_enum=False, length=50),
        nullable=False,
    )

    # OAuth tokens (encrypted)
    access_token: Mapped[str | None] = mapped_column(
        Text,
        info=compliance_column(
            sensitivity=DataSensitivity.RESTRICTED,
            encryption=EncryptionType.AT_REST,
            mask_in_logs=True,
            soc2_critical=True,
        ),
    )
    refresh_token: Mapped[str | None] = mapped_column(
        Text,
        info=compliance_column(
            sensitivity=DataSensitivity.RESTRICTED,
            encryption=EncryptionType.AT_REST,
            mask_in_logs=True,
            soc2_critical=True,
        ),
    )
    token_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Account info
    account_email: Mapped[str | None] = mapped_column(String(255))
    account_id: Mapped[str | None] = mapped_column(String(255))
    scopes: Mapped[list[str] | None] = mapped_column(JSON)

    # Sync settings
    calendar_ids: Mapped[list[str] | None] = mapped_column(
        JSON
    )  # Which calendars to sync
    primary_calendar_id: Mapped[str | None] = mapped_column(String(255))
    sync_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    sync_token: Mapped[str | None] = mapped_column(String(500))

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_error: Mapped[str | None] = mapped_column(Text)
    error_count: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)

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
    events: Mapped[list["CalendarEvent"]] = relationship(
        "CalendarEvent", back_populates="credential", cascade="all, delete-orphan"
    )
    availability_blocks: Mapped[list["CalendarAvailability"]] = relationship(
        "CalendarAvailability", back_populates="credential", cascade="all, delete-orphan"
    )

    # Unique constraint
    __table_args__ = (
        UniqueConstraint("user_id", "provider", name="uq_user_calendar_provider"),
    )


# ==================== CalendarEvent Model ===================== #
@audit_changes
class CalendarEvent(Base):
    """
    Synced calendar events.
    """

    __tablename__ = "calendar_events"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )
    credential_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("calendar_credentials.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # External reference
    external_event_id: Mapped[str] = mapped_column(
        String(500), nullable=False, index=True
    )
    external_calendar_id: Mapped[str | None] = mapped_column(String(255))
    ical_uid: Mapped[str | None] = mapped_column(String(500))

    # Event info
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    location: Mapped[str | None] = mapped_column(String(500))
    event_type: Mapped[EventType] = mapped_column(
        SQLEnum(EventType, native_enum=False, length=50),
        nullable=False,
        default=EventType.MEETING,
    )
    status: Mapped[EventStatus] = mapped_column(
        SQLEnum(EventStatus, native_enum=False, length=50),
        nullable=False,
        default=EventStatus.CONFIRMED,
    )

    # Time
    start_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    end_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    timezone: Mapped[str] = mapped_column(String(50), nullable=False, default="UTC")
    is_all_day: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Recurrence
    is_recurring: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    recurrence_rule: Mapped[str | None] = mapped_column(String(500))
    recurring_event_id: Mapped[str | None] = mapped_column(String(500))

    # Meeting link
    meeting_url: Mapped[str | None] = mapped_column(String(1000))
    conference_data: Mapped[dict[str, Any] | None] = mapped_column(JSON)

    # Attendees
    attendees: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON)
    organizer_email: Mapped[str | None] = mapped_column(String(255))

    # Link to interview
    interview_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("interviews.id")
    )

    # Sync status
    sync_status: Mapped[SyncStatus] = mapped_column(
        SQLEnum(SyncStatus, native_enum=False, length=50),
        nullable=False,
        default=SyncStatus.SYNCED,
    )
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    external_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

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
    credential: Mapped["CalendarCredential"] = relationship(
        "CalendarCredential", back_populates="events"
    )

    # Indexes
    __table_args__ = (
        Index("idx_calendar_event_time", "user_id", "start_time", "end_time"),
        UniqueConstraint(
            "credential_id", "external_event_id", name="uq_credential_event"
        ),
    )


# ==================== CalendarAvailability Model ===================== #
@audit_changes
class CalendarAvailability(Base):
    """
    User availability blocks derived from calendar.
    """

    __tablename__ = "calendar_availability"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )
    credential_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("calendar_credentials.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Time block
    start_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    end_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    timezone: Mapped[str] = mapped_column(String(50), nullable=False, default="UTC")

    # Availability type
    is_available: Mapped[bool] = mapped_column(Boolean, nullable=False)
    availability_type: Mapped[str | None] = mapped_column(
        String(50)
    )  # free, busy, tentative

    # Source
    source_event_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("calendar_events.id")
    )
    is_manual: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )  # Manually set

    # Recurrence
    recurrence_rule: Mapped[str | None] = mapped_column(String(500))
    parent_availability_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("calendar_availability.id")
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
    credential: Mapped["CalendarCredential"] = relationship(
        "CalendarCredential", back_populates="availability_blocks"
    )

    # Indexes
    __table_args__ = (
        Index("idx_availability_time", "user_id", "start_time", "is_available"),
    )
