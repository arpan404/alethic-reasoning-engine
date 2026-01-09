from sqlalchemy.orm import Mapped, mapped_column
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


# ==================== Enums ===================== #
class SubscriptionTier(str, PyEnum):
    FREE = "free"
    BASIC = "basic"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"


class SubscriptionStatus(str, PyEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    CANCELED = "canceled"
    EXPIRED = "expired"


class BillingStatus(str, PyEnum):
    PAID = "paid"
    PENDING = "pending"
    FAILED = "failed"
    REFUNDED = "refunded"


# ==================== Subscription Model ===================== #
@audit_changes
class Subscription(Base):
    __tablename__: str = "subscriptions"
    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, unique=True
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id"), nullable=False
    )  # FK to users table; the subscribe, usually an organization admin
    plan: Mapped[SubscriptionTier] = mapped_column(
        SQLEnum(SubscriptionTier, name="subscription_tier"),
        nullable=False,
        default=SubscriptionTier.FREE,
    )
    status: Mapped[SubscriptionStatus] = mapped_column(
        SQLEnum(SubscriptionStatus, name="subscription_status"),
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
    )  # when the limits reset like at month start or year start, customisable based on billing cycle or requirements
    no_of_organizations: Mapped[int | None] = mapped_column(
        Integer
    )  # number of organizations allowed under this subscription
    no_of_team_members: Mapped[int | None] = mapped_column(
        Integer
    )  # number of team members allowed under this subscription in each organization

    # Billing
    billing_cycle: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    price_per_month: Mapped[float | None] = mapped_column(
        BigInteger
    )  # in cents to avoid float precision issues
    currency: Mapped[str | None] = mapped_column(
        String(10), default="USD", nullable=False
    )  # USD, EUR, etc.

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


@audit_changes
class SubscriptionFeature(Base):
    """
    Features associated with each subscription tier.
    """

    __tablename__: str = "subscription_features"
    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )
    tier: Mapped[SubscriptionTier] = mapped_column(
        SQLEnum(SubscriptionTier, name="subscription_tier_features"),
        nullable=False,
        index=True,
    )
    feature_name: Mapped[str] = mapped_column(String(100), nullable=False)
    feature_value: Mapped[str | None] = mapped_column(String(500))
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # limits
    feature_limit: Mapped[int | None] = mapped_column(Integer, nullable=False)

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
    )  # FK to users table; the admin who created this feature entry

    updated_by: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id"), nullable=True
    )  # FK to users table; the admin who last updated this feature entry


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
        BigInteger, ForeignKey("subscriptions.id"), nullable=False, index=True
    )

    # Billing details
    amount: Mapped[float] = mapped_column(BigInteger, nullable=False)  # in cents
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
    payment_method: Mapped[str | None] = mapped_column(
        String(100)
    )  # e.g., credit card, PayPal
    transaction_id: Mapped[str | None] = mapped_column(
        String(100)
    )  # from payment gateway
    payment_status: Mapped[BillingStatus] = mapped_column(
        SQLEnum(BillingStatus, name="billing_status"),
        nullable=False,
        default=BillingStatus.PENDING,
    )
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    invoice_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("invoices.id"), nullable=True
    )  # FK to invoices table

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
        BigInteger, ForeignKey("subscriptions.id"), nullable=False, index=True
    )
    invoice_number: Mapped[str] = mapped_column(
        String(100), nullable=False, unique=True
    )
    amount: Mapped[float] = mapped_column(BigInteger, nullable=False)  # in cents
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    issued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    pdf_url: Mapped[str | None] = mapped_column(String(500))  # URL to the PDF invoice

    invoice_breakdown: Mapped[dict | None] = mapped_column(
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
        BigInteger, ForeignKey("subscriptions.id"), nullable=False, index=True
    )
    organization_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("organizations.id"),
        nullable=False,
        index=True,
    )

    # usage metrics
    metric_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # e.g., "job_postings", "ai_evaluations", "storage_gb", "video_interviews"
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
