from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import (
    JSON,
    String,
    Boolean,
    ForeignKey,
    BigInteger,
    DateTime,
    func,
    Enum as SQLEnum,
    Integer,
)
from database.engine import Base
from enum import Enum as PyEnum
from datetime import datetime
from database.security import audit_changes
from typing import Any


# ==================== Enums ===================== #
class SubscriptionTier(str, PyEnum):
    """Subscription tier levels."""

    FREE = "free"
    BASIC = "basic"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"


class SubscriptionStatus(str, PyEnum):
    """Subscription status options."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    CANCELED = "canceled"
    EXPIRED = "expired"
    PAST_DUE = "past_due"
    TRIALING = "trialing"


class BillingStatus(str, PyEnum):
    """Billing payment status."""

    PAID = "paid"
    PENDING = "pending"
    FAILED = "failed"
    REFUNDED = "refunded"
    PARTIALLY_REFUNDED = "partially_refunded"


class PaymentMethod(str, PyEnum):
    """Payment methods supported."""

    CREDIT_CARD = "credit_card"
    DEBIT_CARD = "debit_card"
    BANK_TRANSFER = "bank_transfer"
    PAYPAL = "paypal"
    STRIPE = "stripe"
    WIRE = "wire"


class UsageMetricType(str, PyEnum):
    """Types of usage metrics tracked."""

    JOB_POSTINGS = "job_postings"
    AI_EVALUATIONS = "ai_evaluations"
    STORAGE_GB = "storage_gb"
    VIDEO_INTERVIEWS = "video_interviews"
    CANDIDATES_PROCESSED = "candidates_processed"
    API_CALLS = "api_calls"
    EMBEDDINGS_GENERATED = "embeddings_generated"


class InvoiceStatus(str, PyEnum):
    """Invoice status options."""

    DRAFT = "draft"
    SENT = "sent"
    PAID = "paid"
    OVERDUE = "overdue"
    VOID = "void"


# ==================== Subscription Model ===================== #
@audit_changes
class Subscription(Base):
    """Subscription plans for organizations."""

    __tablename__: str = "subscriptions"
    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id"), nullable=False, index=True
    )  # FK to users table; the subscriber, usually an organization admin
    plan: Mapped[SubscriptionTier] = mapped_column(
        SQLEnum(SubscriptionTier, native_enum=False, length=50),
        nullable=False,
        default=SubscriptionTier.FREE,
    )
    status: Mapped[SubscriptionStatus] = mapped_column(
        SQLEnum(SubscriptionStatus, native_enum=False, length=50),
        nullable=False,
        default=SubscriptionStatus.ACTIVE,
    )

    # AI feature limits
    job_postings_limit: Mapped[int | None] = mapped_column(Integer)
    ai_evaluations_limit: Mapped[int | None] = mapped_column(Integer)
    storage_limit_gb: Mapped[int | None] = mapped_column(Integer)
    video_interviews_limit: Mapped[int | None] = mapped_column(Integer)
    limit_reset_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )  # when the limits reset like at month start or year start
    no_of_organizations: Mapped[int | None] = mapped_column(
        Integer
    )  # number of organizations allowed under this subscription
    no_of_team_members: Mapped[int | None] = mapped_column(
        Integer
    )  # number of team members allowed per organization

    # Billing
    billing_cycle: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    price_per_month: Mapped[int | None] = mapped_column(
        BigInteger
    )  # in cents to avoid float precision issues
    currency: Mapped[str] = mapped_column(String(10), default="USD", nullable=False)

    # Metadata
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
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
    billing_history: Mapped[list["BillingHistory"]] = relationship(
        "BillingHistory", back_populates="subscription", cascade="all, delete-orphan"
    )
    invoices: Mapped[list["Invoices"]] = relationship(
        "Invoices", back_populates="subscription", cascade="all, delete-orphan"
    )
    usage_tracking: Mapped[list["UsageTracking"]] = relationship(
        "UsageTracking", back_populates="subscription", cascade="all, delete-orphan"
    )
    features: Mapped[list["SubscriptionFeature"]] = relationship(
        "SubscriptionFeature", back_populates="subscription", cascade="all, delete-orphan"
    )


@audit_changes
class SubscriptionFeature(Base):
    """
    Features associated with each subscription tier.
    """

    __tablename__: str = "subscription_features"
    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )
    subscription_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("subscriptions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tier: Mapped[SubscriptionTier] = mapped_column(
        SQLEnum(SubscriptionTier, native_enum=False, length=50),
        nullable=False,
        index=True,
    )
    feature_name: Mapped[str] = mapped_column(String(100), nullable=False)
    feature_value: Mapped[str | None] = mapped_column(String(500))
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # limits
    feature_limit: Mapped[int | None] = mapped_column(Integer)

    # created at
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    created_by: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id"), nullable=True
    )
    updated_by: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id"), nullable=True
    )

    # Relationships
    subscription: Mapped["Subscription"] = relationship(
        "Subscription", back_populates="features"
    )


@audit_changes
class BillingHistory(Base):
    """
    Billing and payment history for subscriptions.
    """

    __tablename__: str = "billing_history"
    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )
    subscription_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("subscriptions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Billing details
    amount: Mapped[int] = mapped_column(BigInteger, nullable=False)  # in cents
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    billed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    billing_period_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    billing_period_end: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    # Payment Info
    payment_method: Mapped[PaymentMethod | None] = mapped_column(
        SQLEnum(PaymentMethod, native_enum=False, length=50)
    )
    transaction_id: Mapped[str | None] = mapped_column(
        String(100), index=True
    )  # from payment gateway
    payment_status: Mapped[BillingStatus] = mapped_column(
        SQLEnum(BillingStatus, native_enum=False, length=50),
        nullable=False,
        default=BillingStatus.PENDING,
    )
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    invoice_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("invoices.id"), nullable=True
    )

    # created at
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
    subscription: Mapped["Subscription"] = relationship(
        "Subscription", back_populates="billing_history"
    )


@audit_changes
class Invoices(Base):
    """
    Invoices generated for subscriptions.
    """

    __tablename__: str = "invoices"
    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )
    subscription_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("subscriptions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    invoice_number: Mapped[str] = mapped_column(
        String(100), nullable=False, unique=True
    )
    amount: Mapped[int] = mapped_column(BigInteger, nullable=False)  # in cents
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    status: Mapped[InvoiceStatus] = mapped_column(
        SQLEnum(InvoiceStatus, native_enum=False, length=50),
        nullable=False,
        default=InvoiceStatus.DRAFT,
    )
    issued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    pdf_url: Mapped[str | None] = mapped_column(String(500))  # URL to the PDF invoice

    invoice_breakdown: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True
    )  # Structured invoice breakdown (items, taxes, discounts, etc.)

    # created at
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
    subscription: Mapped["Subscription"] = relationship(
        "Subscription", back_populates="invoices"
    )


@audit_changes
class UsageTracking(Base):
    """
    Tracks usage of features against subscription limits.
    """

    __tablename__: str = "usage_tracking"
    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )
    subscription_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("subscriptions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    organization_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # usage metrics - now type-safe
    metric_type: Mapped[UsageMetricType] = mapped_column(
        SQLEnum(UsageMetricType, native_enum=False, length=50),
        nullable=False,
        index=True,
    )
    usage_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Period
    period_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    period_end: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    # Timestamps
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Relationships
    subscription: Mapped["Subscription"] = relationship(
        "Subscription", back_populates="usage_tracking"
    )
