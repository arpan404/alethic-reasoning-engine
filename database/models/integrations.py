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
