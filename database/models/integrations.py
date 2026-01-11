"""
Organization Integration Models

Secure storage for third-party integration credentials and webhook configurations.
Includes GDPR/SOC2 compliance markers for sensitive credential data.
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
)
from database.engine import Base
from database.security import ComplianceMixin, audit_changes
from database.security import (
    compliance_column,
    DataSensitivity,
    EncryptionType,
    DataRetentionPeriod,
)
from datetime import datetime
from enum import Enum as PyEnum
from typing import Any


# ==================== Integration Enums ===================== #
class IntegrationType(str, PyEnum):
    """Types of third-party integrations."""

    # Job Boards
    LINKEDIN = "linkedin"
    INDEED = "indeed"
    GLASSDOOR = "glassdoor"
    ZIPRECRUITER = "ziprecruiter"
    MONSTER = "monster"

    # ATS Systems
    GREENHOUSE = "greenhouse"
    LEVER = "lever"
    WORKDAY = "workday"
    BAMBOOHR = "bamboohr"
    ICIMS = "icims"
    TALEO = "taleo"
    JOBVITE = "jobvite"

    # Email Providers
    GMAIL = "gmail"
    OUTLOOK = "outlook"
    MICROSOFT_365 = "microsoft_365"

    # Calendar
    GOOGLE_CALENDAR = "google_calendar"
    OUTLOOK_CALENDAR = "outlook_calendar"

    # Communication
    SLACK = "slack"
    TEAMS = "teams"
    ZOOM = "zoom"

    # Background Check
    CHECKR = "checkr"
    STERLING = "sterling"

    # HRIS
    GUSTO = "gusto"
    RIPPLING = "rippling"

    # Custom
    CUSTOM = "custom"


class IntegrationStatus(str, PyEnum):
    """Status of an integration."""

    PENDING = "pending"
    ACTIVE = "active"
    INACTIVE = "inactive"
    EXPIRED = "expired"
    REVOKED = "revoked"
    ERROR = "error"


class IntegrationAuthType(str, PyEnum):
    """Authentication methods for integrations."""

    OAUTH2 = "oauth2"
    API_KEY = "api_key"
    BASIC_AUTH = "basic_auth"
    JWT = "jwt"
    WEBHOOK_SECRET = "webhook_secret"
    SAML = "saml"


class WebhookEventType(str, PyEnum):
    """Types of webhook events."""

    # Job Events
    JOB_CREATED = "job.created"
    JOB_UPDATED = "job.updated"
    JOB_CLOSED = "job.closed"
    JOB_DELETED = "job.deleted"

    # Application Events
    APPLICATION_RECEIVED = "application.received"
    APPLICATION_UPDATED = "application.updated"
    APPLICATION_STATUS_CHANGED = "application.status_changed"

    # Candidate Events
    CANDIDATE_CREATED = "candidate.created"
    CANDIDATE_UPDATED = "candidate.updated"

    # Interview Events
    INTERVIEW_SCHEDULED = "interview.scheduled"
    INTERVIEW_COMPLETED = "interview.completed"
    INTERVIEW_CANCELLED = "interview.cancelled"

    # Offer Events
    OFFER_CREATED = "offer.created"
    OFFER_ACCEPTED = "offer.accepted"
    OFFER_DECLINED = "offer.declined"

    # System Events
    SYNC_COMPLETED = "sync.completed"
    ERROR_OCCURRED = "error.occurred"


class WebhookStatus(str, PyEnum):
    """Status of a webhook endpoint."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"  # Too many failures


class WebhookDeliveryStatus(str, PyEnum):
    """Delivery status of a webhook call."""

    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    RETRYING = "retrying"


class SyncType(str, PyEnum):
    """Types of integration sync operations."""

    FULL = "full"
    INCREMENTAL = "incremental"
    MANUAL = "manual"
    SCHEDULED = "scheduled"


class SyncDirection(str, PyEnum):
    """Direction of data sync."""

    INBOUND = "inbound"
    OUTBOUND = "outbound"
    BIDIRECTIONAL = "bidirectional"


class SyncStatus(str, PyEnum):
    """Status of a sync operation."""

    STARTED = "started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SignatureAlgorithm(str, PyEnum):
    """Algorithms for webhook signature verification."""

    SHA256 = "sha256"
    SHA512 = "sha512"
    HMAC_SHA256 = "hmac_sha256"
    HMAC_SHA512 = "hmac_sha512"


class OutboundRequestStatus(str, PyEnum):
    """Status of outbound API requests to integrations."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILED = "failed"
    RETRYING = "retrying"
    CANCELLED = "cancelled"


class HttpMethod(str, PyEnum):
    """HTTP methods for API requests."""

    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"


class OutboundOperationType(str, PyEnum):
    """Types of outbound operations."""

    # Job operations
    CREATE_JOB = "create_job"
    UPDATE_JOB = "update_job"
    DELETE_JOB = "delete_job"
    SYNC_JOB = "sync_job"

    # Candidate operations
    CREATE_CANDIDATE = "create_candidate"
    UPDATE_CANDIDATE = "update_candidate"
    SYNC_CANDIDATE = "sync_candidate"

    # Application operations
    CREATE_APPLICATION = "create_application"
    UPDATE_APPLICATION = "update_application"
    UPDATE_APPLICATION_STATUS = "update_application_status"
    SYNC_APPLICATION = "sync_application"

    # Interview operations
    SCHEDULE_INTERVIEW = "schedule_interview"
    UPDATE_INTERVIEW = "update_interview"
    CANCEL_INTERVIEW = "cancel_interview"

    # Offer operations
    CREATE_OFFER = "create_offer"
    UPDATE_OFFER = "update_offer"

    # Generic
    CUSTOM = "custom"
    WEBHOOK_TEST = "webhook_test"


class IntegrationEntityType(str, PyEnum):
    """Entity types for integration operations."""

    JOB = "job"
    CANDIDATE = "candidate"
    APPLICATION = "application"
    INTERVIEW = "interview"
    OFFER = "offer"
    USER = "user"
    ORGANIZATION = "organization"


# ==================== Organization Integration Model ===================== #
@audit_changes
class OrganizationIntegration(Base, ComplianceMixin):
    """
    Stores third-party integration credentials for organizations.
    All sensitive credentials are encrypted at rest.
    """

    __tablename__ = "organization_integrations"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )
    organization_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Integration identification
    integration_type: Mapped[IntegrationType] = mapped_column(
        SQLEnum(IntegrationType, native_enum=False, length=50),
        nullable=False,
        index=True,
    )
    integration_name: Mapped[str] = mapped_column(
        String(255), nullable=False
    )  # Custom display name
    external_account_id: Mapped[str | None] = mapped_column(
        String(255), index=True
    )  # Account ID on external platform

    # Status
    status: Mapped[IntegrationStatus] = mapped_column(
        SQLEnum(IntegrationStatus, native_enum=False, length=50),
        nullable=False,
        default=IntegrationStatus.PENDING,
        index=True,
    )
    auth_type: Mapped[IntegrationAuthType] = mapped_column(
        SQLEnum(IntegrationAuthType, native_enum=False, length=50),
        nullable=False,
    )

    # OAuth2 Credentials (encrypted - SOC2 critical)
    access_token: Mapped[str | None] = mapped_column(
        Text,
        info=compliance_column(
            sensitivity=DataSensitivity.RESTRICTED,
            encryption=EncryptionType.AT_REST,
            soc2_critical=True,
            mask_in_logs=True,
            retention_period=DataRetentionPeriod.YEARS_2,
        ),
    )
    refresh_token: Mapped[str | None] = mapped_column(
        Text,
        info=compliance_column(
            sensitivity=DataSensitivity.RESTRICTED,
            encryption=EncryptionType.AT_REST,
            soc2_critical=True,
            mask_in_logs=True,
            retention_period=DataRetentionPeriod.YEARS_2,
        ),
    )
    token_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # API Key Credentials (encrypted - SOC2 critical)
    api_key: Mapped[str | None] = mapped_column(
        Text,
        info=compliance_column(
            sensitivity=DataSensitivity.RESTRICTED,
            encryption=EncryptionType.AT_REST,
            soc2_critical=True,
            mask_in_logs=True,
            retention_period=DataRetentionPeriod.YEARS_2,
        ),
    )
    api_secret: Mapped[str | None] = mapped_column(
        Text,
        info=compliance_column(
            sensitivity=DataSensitivity.RESTRICTED,
            encryption=EncryptionType.AT_REST,
            soc2_critical=True,
            mask_in_logs=True,
            retention_period=DataRetentionPeriod.YEARS_2,
        ),
    )

    # Webhook secret for incoming webhooks from this integration
    webhook_secret: Mapped[str | None] = mapped_column(
        String(500),
        info=compliance_column(
            sensitivity=DataSensitivity.RESTRICTED,
            encryption=EncryptionType.AT_REST,
            soc2_critical=True,
            mask_in_logs=True,
        ),
    )

    # Integration configuration
    config: Mapped[dict[str, Any] | None] = mapped_column(JSON)  # Platform-specific settings
    scopes: Mapped[list[str] | None] = mapped_column(JSON)  # OAuth scopes granted
    metadata: Mapped[dict[str, Any] | None] = mapped_column(JSON)  # Additional metadata

    # Error tracking
    last_error: Mapped[str | None] = mapped_column(Text)
    last_error_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    consecutive_failures: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=0
    )

    # Sync tracking
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    next_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Audit fields
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

    # Relationships
    webhooks: Mapped[list["IntegrationWebhook"]] = relationship(
        "IntegrationWebhook",
        back_populates="integration",
        cascade="all, delete-orphan",
    )
    sync_logs: Mapped[list["IntegrationSyncLog"]] = relationship(
        "IntegrationSyncLog",
        back_populates="integration",
        cascade="all, delete-orphan",
    )
    outbound_requests: Mapped[list["IntegrationOutboundRequest"]] = relationship(
        "IntegrationOutboundRequest",
        back_populates="integration",
        cascade="all, delete-orphan",
    )

    # Unique constraint: one integration type per organization
    __table_args__ = (
        Index(
            "uq_org_integration_type",
            "organization_id",
            "integration_type",
            unique=True,
        ),
    )


# ==================== Integration Webhook Model ===================== #
@audit_changes
class IntegrationWebhook(Base, ComplianceMixin):
    """
    Webhook endpoints for receiving data from integrations.
    Each integration can have multiple webhooks for different event types.
    """

    __tablename__ = "integration_webhooks"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )
    integration_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("organization_integrations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Webhook identification
    webhook_id: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False, index=True
    )  # UUID for URL routing
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

    # Endpoint configuration
    endpoint_url: Mapped[str] = mapped_column(
        String(1000), nullable=False
    )  # Our endpoint URL
    external_webhook_id: Mapped[str | None] = mapped_column(
        String(255), index=True
    )  # Webhook ID on external platform

    # Event subscriptions
    subscribed_events: Mapped[list[str]] = mapped_column(
        JSON, nullable=False, default=[]
    )  # List of WebhookEventType values

    # Security
    secret_key: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        info=compliance_column(
            sensitivity=DataSensitivity.RESTRICTED,
            encryption=EncryptionType.AT_REST,
            soc2_critical=True,
            mask_in_logs=True,
        ),
    )
    signature_header: Mapped[str] = mapped_column(
        String(100), nullable=False, default="X-Webhook-Signature"
    )
    signature_algorithm: Mapped[SignatureAlgorithm] = mapped_column(
        SQLEnum(SignatureAlgorithm, native_enum=False, length=50),
        nullable=False,
        default=SignatureAlgorithm.SHA256,
    )

    # Status
    status: Mapped[WebhookStatus] = mapped_column(
        SQLEnum(WebhookStatus, native_enum=False, length=50),
        nullable=False,
        default=WebhookStatus.ACTIVE,
        index=True,
    )
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Error tracking
    last_error: Mapped[str | None] = mapped_column(Text)
    last_error_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    consecutive_failures: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=0
    )

    # Statistics
    total_received: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    total_processed: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    total_failed: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    last_received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

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
    integration: Mapped["OrganizationIntegration"] = relationship(
        "OrganizationIntegration", back_populates="webhooks"
    )
    deliveries: Mapped[list["WebhookDelivery"]] = relationship(
        "WebhookDelivery",
        back_populates="webhook",
        cascade="all, delete-orphan",
    )


# ==================== Webhook Delivery Log Model ===================== #
@audit_changes
class WebhookDelivery(Base):
    """
    Log of webhook deliveries for debugging and retry purposes.
    Stores incoming webhook payloads and processing results.
    """

    __tablename__ = "webhook_deliveries"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )
    webhook_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("integration_webhooks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Delivery identification
    delivery_id: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False, index=True
    )  # UUID
    event_type: Mapped[WebhookEventType] = mapped_column(
        SQLEnum(WebhookEventType, native_enum=False, length=100),
        nullable=False,
        index=True,
    )
    idempotency_key: Mapped[str | None] = mapped_column(
        String(255), index=True
    )  # Prevent duplicate processing

    # Request data
    request_headers: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    request_payload: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        info=compliance_column(
            sensitivity=DataSensitivity.CONFIDENTIAL,
            retention_period=DataRetentionPeriod.DAYS_90,
        ),
    )
    request_signature: Mapped[str | None] = mapped_column(String(500))
    signature_valid: Mapped[bool | None] = mapped_column(Boolean)

    # Processing
    status: Mapped[WebhookDeliveryStatus] = mapped_column(
        SQLEnum(WebhookDeliveryStatus, native_enum=False, length=50),
        nullable=False,
        default=WebhookDeliveryStatus.PENDING,
        index=True,
    )
    processing_started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    processing_completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    processing_duration_ms: Mapped[int | None] = mapped_column(BigInteger)

    # Response/Result
    response_status_code: Mapped[int | None] = mapped_column(BigInteger)
    response_body: Mapped[str | None] = mapped_column(Text)
    error_message: Mapped[str | None] = mapped_column(Text)

    # Retry tracking
    attempt_count: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    max_attempts: Mapped[int] = mapped_column(BigInteger, nullable=False, default=5)
    next_retry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Timestamps
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Relationships
    webhook: Mapped["IntegrationWebhook"] = relationship(
        "IntegrationWebhook", back_populates="deliveries"
    )

    # Index for cleanup of old deliveries
    __table_args__ = (
        Index("idx_webhook_delivery_cleanup", "received_at", "status"),
    )


# ==================== Integration Sync Log Model ===================== #
@audit_changes
class IntegrationSyncLog(Base):
    """
    Log of integration sync operations for auditing.
    """

    __tablename__ = "integration_sync_logs"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )
    integration_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("organization_integrations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Sync details
    sync_type: Mapped[SyncType] = mapped_column(
        SQLEnum(SyncType, native_enum=False, length=50),
        nullable=False,
    )
    direction: Mapped[SyncDirection] = mapped_column(
        SQLEnum(SyncDirection, native_enum=False, length=50),
        nullable=False,
    )

    # Status
    status: Mapped[SyncStatus] = mapped_column(
        SQLEnum(SyncStatus, native_enum=False, length=50),
        nullable=False,
        index=True,
    )
    error_message: Mapped[str | None] = mapped_column(Text)

    # Statistics
    records_processed: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    records_created: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    records_updated: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    records_failed: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)

    # Timestamps
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_seconds: Mapped[int | None] = mapped_column(BigInteger)

    # Relationships
    integration: Mapped["OrganizationIntegration"] = relationship(
        "OrganizationIntegration", back_populates="sync_logs"
    )


# ==================== Outbound Request Model ===================== #
@audit_changes
class IntegrationOutboundRequest(Base):
    """
    Log of outbound API requests to external integrations.
    Tracks all data we SEND to external platforms for auditing and debugging.
    """

    __tablename__ = "integration_outbound_requests"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )
    integration_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("organization_integrations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Request identification
    request_id: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False, index=True
    )  # UUID for tracking
    idempotency_key: Mapped[str | None] = mapped_column(
        String(255), index=True
    )  # Prevent duplicate sends

    # Request context
    operation_type: Mapped[OutboundOperationType] = mapped_column(
        SQLEnum(OutboundOperationType, native_enum=False, length=100),
        nullable=False,
        index=True,
    )
    entity_type: Mapped[IntegrationEntityType | None] = mapped_column(
        SQLEnum(IntegrationEntityType, native_enum=False, length=50)
    )
    entity_id: Mapped[int | None] = mapped_column(BigInteger, index=True)

    # HTTP request details
    http_method: Mapped[HttpMethod] = mapped_column(
        SQLEnum(HttpMethod, native_enum=False, length=10),
        nullable=False,
    )
    endpoint_url: Mapped[str] = mapped_column(String(1000), nullable=False)
    request_headers: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    request_body: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        info=compliance_column(
            sensitivity=DataSensitivity.CONFIDENTIAL,
            retention_period=DataRetentionPeriod.DAYS_90,
        ),
    )

    # Response details
    response_status_code: Mapped[int | None] = mapped_column(BigInteger)
    response_headers: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    response_body: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        info=compliance_column(
            sensitivity=DataSensitivity.CONFIDENTIAL,
            retention_period=DataRetentionPeriod.DAYS_90,
        ),
    )

    # Status tracking
    status: Mapped[OutboundRequestStatus] = mapped_column(
        SQLEnum(OutboundRequestStatus, native_enum=False, length=50),
        nullable=False,
        default=OutboundRequestStatus.PENDING,
        index=True,
    )
    error_message: Mapped[str | None] = mapped_column(Text)
    error_code: Mapped[str | None] = mapped_column(String(100))

    # Retry tracking
    attempt_count: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    max_attempts: Mapped[int] = mapped_column(BigInteger, nullable=False, default=3)
    next_retry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Timing
    request_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    request_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_ms: Mapped[int | None] = mapped_column(BigInteger)

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

    # Who triggered this request
    triggered_by: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id")
    )

    # Relationships
    integration: Mapped["OrganizationIntegration"] = relationship(
        "OrganizationIntegration", back_populates="outbound_requests"
    )

    # Index for cleanup
    __table_args__ = (
        Index("idx_outbound_request_cleanup", "created_at", "status"),
    )


# ==================== ATS Provider Enums ===================== #
class ATSProviderType(str, PyEnum):
    """External ATS providers we integrate with."""

    GREENHOUSE = "greenhouse"
    LEVER = "lever"
    WORKDAY = "workday"
    ICIMS = "icims"
    TALEO = "taleo"
    SUCCESSFACTORS = "successfactors"
    SMARTRECRUITERS = "smartrecruiters"
    JOBVITE = "jobvite"
    BAMBOOHR = "bamboohr"
    ASHBY = "ashby"
    RECRUITERFLOW = "recruiterflow"
    BREEZY = "breezy"
    JAZZ = "jazz"
    WORKABLE = "workable"
    CUSTOM = "custom"


class SyncEntityType(str, PyEnum):
    """Types of entities that can be synced."""

    CANDIDATE = "candidate"
    JOB = "job"
    APPLICATION = "application"
    INTERVIEW = "interview"
    OFFER = "offer"
    USER = "user"
    DEPARTMENT = "department"
    STAGE = "stage"


class SyncAction(str, PyEnum):
    """Actions performed during sync."""

    CREATED = "created"
    UPDATED = "updated"
    DELETED = "deleted"
    SKIPPED = "skipped"
    FAILED = "failed"
    CONFLICT = "conflict"


class JobBoardType(str, PyEnum):
    """Job board platforms."""

    LINKEDIN = "linkedin"
    INDEED = "indeed"
    GLASSDOOR = "glassdoor"
    ZIPRECRUITER = "ziprecruiter"
    MONSTER = "monster"
    CAREERBUILDER = "careerbuilder"
    DICE = "dice"
    ANGELLIST = "angellist"
    WELLFOUND = "wellfound"
    HACKER_NEWS = "hacker_news"
    STACKOVERFLOW = "stackoverflow"
    BUILTIN = "builtin"
    CUSTOM = "custom"


class PostingStatus(str, PyEnum):
    """Status of job board posting."""

    DRAFT = "draft"
    PENDING = "pending"
    ACTIVE = "active"
    PAUSED = "paused"
    EXPIRED = "expired"
    CLOSED = "closed"
    REJECTED = "rejected"
    ERROR = "error"


# ==================== ATS Provider Model ===================== #
@audit_changes
class ATSProvider(Base, ComplianceMixin):
    """
    Configuration for external ATS providers (Greenhouse, Lever, Workday, etc.)
    """

    __tablename__ = "ats_providers"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )
    organization_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Provider info
    provider_type: Mapped[ATSProviderType] = mapped_column(
        SQLEnum(ATSProviderType, native_enum=False, length=50),
        nullable=False,
    )
    provider_name: Mapped[str] = mapped_column(String(255), nullable=False)
    provider_url: Mapped[str | None] = mapped_column(String(500))

    # API credentials (encrypted)
    api_key: Mapped[str | None] = mapped_column(
        Text,
        info=compliance_column(
            sensitivity=DataSensitivity.RESTRICTED,
            encryption=EncryptionType.AT_REST,
            mask_in_logs=True,
            soc2_critical=True,
        ),
    )
    api_secret: Mapped[str | None] = mapped_column(
        Text,
        info=compliance_column(
            sensitivity=DataSensitivity.RESTRICTED,
            encryption=EncryptionType.AT_REST,
            mask_in_logs=True,
            soc2_critical=True,
        ),
    )
    access_token: Mapped[str | None] = mapped_column(
        Text,
        info=compliance_column(
            sensitivity=DataSensitivity.RESTRICTED,
            encryption=EncryptionType.AT_REST,
            mask_in_logs=True,
        ),
    )
    refresh_token: Mapped[str | None] = mapped_column(
        Text,
        info=compliance_column(
            sensitivity=DataSensitivity.RESTRICTED,
            encryption=EncryptionType.AT_REST,
            mask_in_logs=True,
        ),
    )
    token_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Account info
    account_id: Mapped[str | None] = mapped_column(String(255))
    subdomain: Mapped[str | None] = mapped_column(String(255))  # For Greenhouse, etc.

    # Webhook configuration
    webhook_url: Mapped[str | None] = mapped_column(String(1000))
    webhook_secret: Mapped[str | None] = mapped_column(
        String(255),
        info=compliance_column(
            sensitivity=DataSensitivity.RESTRICTED,
            encryption=EncryptionType.AT_REST,
            mask_in_logs=True,
        ),
    )

    # Sync settings
    sync_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sync_direction: Mapped[SyncDirection] = mapped_column(
        SQLEnum(SyncDirection, native_enum=False, length=50),
        nullable=False,
        default=SyncDirection.BIDIRECTIONAL,
    )
    sync_interval_minutes: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=60
    )
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    next_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Entity sync preferences
    sync_candidates: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sync_jobs: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sync_applications: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    sync_interviews: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sync_offers: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Field mappings
    field_mappings: Mapped[dict[str, Any] | None] = mapped_column(
        JSON
    )  # {local_field: external_field}
    custom_fields: Mapped[dict[str, Any] | None] = mapped_column(JSON)

    # Status
    status: Mapped[IntegrationStatus] = mapped_column(
        SQLEnum(IntegrationStatus, native_enum=False, length=50),
        nullable=False,
        default=IntegrationStatus.PENDING,
    )
    is_primary: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )  # Primary ATS
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
    connected_by: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id"), nullable=False
    )

    # Relationships
    entity_syncs: Mapped[list["ATSEntitySync"]] = relationship(
        "ATSEntitySync", back_populates="provider", cascade="all, delete-orphan"
    )
    sync_logs: Mapped[list["ATSSyncLog"]] = relationship(
        "ATSSyncLog", back_populates="provider", cascade="all, delete-orphan"
    )

    # Unique constraint
    __table_args__ = (
        UniqueConstraint(
            "organization_id", "provider_type", name="uq_org_ats_provider"
        ),
    )


# ==================== ATS Entity Sync Model ===================== #
@audit_changes
class ATSEntitySync(Base):
    """
    Maps external ATS entities to internal entities.
    Tracks sync state for candidates, jobs, applications, etc.
    """

    __tablename__ = "ats_entity_syncs"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )
    provider_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("ats_providers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    organization_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Entity mapping
    entity_type: Mapped[SyncEntityType] = mapped_column(
        SQLEnum(SyncEntityType, native_enum=False, length=50),
        nullable=False,
        index=True,
    )
    external_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    internal_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)

    # External data
    external_data: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    external_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Sync state
    sync_status: Mapped[SyncStatus] = mapped_column(
        SQLEnum(SyncStatus, native_enum=False, length=50),
        nullable=False,
        default=SyncStatus.COMPLETED,
    )
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    sync_hash: Mapped[str | None] = mapped_column(String(64))  # For change detection
    conflict_data: Mapped[dict[str, Any] | None] = mapped_column(JSON)

    # Flags
    is_primary: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )  # Source of truth
    sync_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Error tracking
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
    provider: Mapped["ATSProvider"] = relationship(
        "ATSProvider", back_populates="entity_syncs"
    )

    # Unique constraint and indexes
    __table_args__ = (
        UniqueConstraint(
            "provider_id", "entity_type", "external_id", name="uq_ats_entity_external"
        ),
        UniqueConstraint(
            "provider_id", "entity_type", "internal_id", name="uq_ats_entity_internal"
        ),
        Index("idx_ats_entity_lookup", "entity_type", "external_id"),
    )


# ==================== ATS Sync Log Model ===================== #
@audit_changes
class ATSSyncLog(Base):
    """
    Audit log for ATS sync operations.
    """

    __tablename__ = "ats_sync_logs"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )
    provider_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("ats_providers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    organization_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Sync info
    sync_type: Mapped[SyncType] = mapped_column(
        SQLEnum(SyncType, native_enum=False, length=50),
        nullable=False,
    )
    sync_direction: Mapped[SyncDirection] = mapped_column(
        SQLEnum(SyncDirection, native_enum=False, length=50),
        nullable=False,
    )
    entity_type: Mapped[SyncEntityType | None] = mapped_column(
        SQLEnum(SyncEntityType, native_enum=False, length=50)
    )

    # Status
    status: Mapped[SyncStatus] = mapped_column(
        SQLEnum(SyncStatus, native_enum=False, length=50),
        nullable=False,
        index=True,
    )

    # Counts
    total_records: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    created_count: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    updated_count: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    deleted_count: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    skipped_count: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    failed_count: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    conflict_count: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)

    # Details
    sync_details: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    errors: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON)

    # Timing
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_seconds: Mapped[int | None] = mapped_column(BigInteger)

    # Triggered by
    triggered_by: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.id"))
    trigger_type: Mapped[str | None] = mapped_column(String(50))  # manual, scheduled, webhook

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Relationships
    provider: Mapped["ATSProvider"] = relationship(
        "ATSProvider", back_populates="sync_logs"
    )

    # Index for cleanup
    __table_args__ = (Index("idx_ats_sync_log_cleanup", "created_at", "status"),)


# ==================== Job Board Provider Model ===================== #
@audit_changes
class JobBoardProvider(Base, ComplianceMixin):
    """
    Configuration for job board platforms (LinkedIn, Indeed, etc.)
    """

    __tablename__ = "job_board_providers"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )
    organization_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Provider info
    board_type: Mapped[JobBoardType] = mapped_column(
        SQLEnum(JobBoardType, native_enum=False, length=50),
        nullable=False,
    )
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)

    # API credentials (encrypted)
    api_key: Mapped[str | None] = mapped_column(
        Text,
        info=compliance_column(
            sensitivity=DataSensitivity.RESTRICTED,
            encryption=EncryptionType.AT_REST,
            mask_in_logs=True,
            soc2_critical=True,
        ),
    )
    api_secret: Mapped[str | None] = mapped_column(
        Text,
        info=compliance_column(
            sensitivity=DataSensitivity.RESTRICTED,
            encryption=EncryptionType.AT_REST,
            mask_in_logs=True,
            soc2_critical=True,
        ),
    )
    access_token: Mapped[str | None] = mapped_column(
        Text,
        info=compliance_column(
            sensitivity=DataSensitivity.RESTRICTED,
            encryption=EncryptionType.AT_REST,
            mask_in_logs=True,
        ),
    )
    token_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Account info
    account_id: Mapped[str | None] = mapped_column(String(255))
    company_page_url: Mapped[str | None] = mapped_column(String(500))
    employer_id: Mapped[str | None] = mapped_column(String(255))

    # Posting settings
    auto_post: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    default_budget_daily: Mapped[int | None] = mapped_column(BigInteger)  # In cents
    default_duration_days: Mapped[int | None] = mapped_column(BigInteger)

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)

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
    connected_by: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id"), nullable=False
    )

    # Relationships
    postings: Mapped[list["JobBoardPosting"]] = relationship(
        "JobBoardPosting", back_populates="provider", cascade="all, delete-orphan"
    )

    # Unique constraint
    __table_args__ = (
        UniqueConstraint("organization_id", "board_type", name="uq_org_job_board"),
    )


# ==================== Job Board Posting Model ===================== #
@audit_changes
class JobBoardPosting(Base):
    """
    Tracks job postings on external job boards.
    """

    __tablename__ = "job_board_postings"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )
    provider_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("job_board_providers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    job_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    organization_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # External reference
    external_posting_id: Mapped[str | None] = mapped_column(String(255), index=True)
    external_url: Mapped[str | None] = mapped_column(String(1000))
    apply_url: Mapped[str | None] = mapped_column(String(1000))

    # Status
    status: Mapped[PostingStatus] = mapped_column(
        SQLEnum(PostingStatus, native_enum=False, length=50),
        nullable=False,
        default=PostingStatus.DRAFT,
        index=True,
    )

    # Posting content (may differ from job)
    posted_title: Mapped[str | None] = mapped_column(String(255))
    posted_description: Mapped[str | None] = mapped_column(Text)
    posted_salary_min: Mapped[int | None] = mapped_column(BigInteger)
    posted_salary_max: Mapped[int | None] = mapped_column(BigInteger)

    # Scheduling
    scheduled_post_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Budget
    budget_daily: Mapped[int | None] = mapped_column(BigInteger)  # In cents
    budget_total: Mapped[int | None] = mapped_column(BigInteger)
    spent_total: Mapped[int | None] = mapped_column(BigInteger)

    # Stats
    views_count: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    clicks_count: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    applications_count: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)

    # Error tracking
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
    posted_by: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.id"))

    # Relationships
    provider: Mapped["JobBoardProvider"] = relationship(
        "JobBoardProvider", back_populates="postings"
    )
    applications: Mapped[list["JobBoardApplication"]] = relationship(
        "JobBoardApplication", back_populates="posting", cascade="all, delete-orphan"
    )

    # Unique constraint
    __table_args__ = (
        UniqueConstraint("provider_id", "job_id", name="uq_provider_job_posting"),
        Index("idx_posting_status", "organization_id", "status"),
    )


# ==================== Job Board Application Model ===================== #
@audit_changes
class JobBoardApplication(Base, ComplianceMixin):
    """
    Inbound applications from job boards.
    """

    __tablename__ = "job_board_applications"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )
    posting_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("job_board_postings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    job_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    organization_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # External reference
    external_application_id: Mapped[str | None] = mapped_column(
        String(255), index=True
    )
    source_platform: Mapped[JobBoardType] = mapped_column(
        SQLEnum(JobBoardType, native_enum=False, length=50),
        nullable=False,
    )

    # Candidate info (before matching/creation)
    candidate_email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        info=compliance_column(
            sensitivity=DataSensitivity.CONFIDENTIAL,
            pii=True,
        ),
    )
    candidate_first_name: Mapped[str | None] = mapped_column(
        String(100),
        info=compliance_column(pii=True),
    )
    candidate_last_name: Mapped[str | None] = mapped_column(
        String(100),
        info=compliance_column(pii=True),
    )
    candidate_phone: Mapped[str | None] = mapped_column(
        String(50),
        info=compliance_column(pii=True),
    )
    candidate_linkedin: Mapped[str | None] = mapped_column(String(500))
    candidate_location: Mapped[str | None] = mapped_column(String(255))

    # Resume
    resume_url: Mapped[str | None] = mapped_column(String(1000))
    resume_file_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("files.id")
    )

    # Raw data
    raw_data: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    cover_letter: Mapped[str | None] = mapped_column(Text)
    answers: Mapped[dict[str, Any] | None] = mapped_column(JSON)

    # Processing status
    is_processed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Linked entities (after processing)
    candidate_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("candidates.id"), index=True
    )
    application_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("applications.id"), index=True
    )

    # Duplicate detection
    is_duplicate: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    duplicate_of_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("job_board_applications.id")
    )

    # Timestamps
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Relationships
    posting: Mapped["JobBoardPosting"] = relationship(
        "JobBoardPosting", back_populates="applications"
    )

    # Indexes
    __table_args__ = (
        Index("idx_jb_app_email", "candidate_email", "job_id"),
        Index("idx_jb_app_processed", "is_processed", "received_at"),
    )
