from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import (
    String,
    ForeignKey,
    Enum as SQLEnum,
    BigInteger,
    Integer,
    DateTime,
    func,
    Numeric,
    Boolean,
)
from database.engine import Base
from enum import Enum as PyEnum
from datetime import datetime


class SubcriptionTier(str, PyEnum):
    FREE = "free"
    BASIC = "basic"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"


class Subscription(Base):
    __tablename__: str = "subscriptions"
    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, unique=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    organization_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("organizations.id"), nullable=False
    )
    plan: Mapped[SubcriptionTier] = mapped_column(
        SQLEnum(SubcriptionTier, name="subscription_tier"),
        default=SubcriptionTier.FREE,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(100), nullable=False)

    # AI feature limits
    ai_evaluations_limit: Mapped[int | None] = mapped_column(Integer)  # per month
    video_interviews_limit: Mapped[int | None] = mapped_column(Integer)  # per month
    storage_limit_gb: Mapped[int | None] = mapped_column(Integer)

    # Billing
    billing_cycle: Mapped[str | None] = mapped_column(String(20))  # monthly, yearly
    price_per_month: Mapped[float | None] = mapped_column(Numeric(10, 2))

    # Timestamps
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


class SubscriptionFeature(Base):
    """Features included in subscription tiers."""

    __tablename__ = "subscription_features"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )

    tier: Mapped[SubcriptionTier] = mapped_column(
        SQLEnum(SubcriptionTier, name="subscription_tier_features"),
        nullable=False,
        index=True,
    )
    feature_name: Mapped[str] = mapped_column(String(100), nullable=False)
    feature_value: Mapped[str | None] = mapped_column(String(500))
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class BillingHistory(Base):
    """Billing and payment history."""

    __tablename__ = "billing_history"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )

    subscription_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("subscriptions.id"), nullable=False, index=True
    )

    # Billing details
    amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    billing_period_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    billing_period_end: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    # Payment
    payment_status: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # pending, paid, failed, refunded
    payment_method: Mapped[str | None] = mapped_column(String(50))
    transaction_id: Mapped[str | None] = mapped_column(String(255), index=True)

    # Timestamps
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class UsageTracking(Base):
    """Track usage of AI features and storage."""

    __tablename__ = "usage_tracking"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )

    organization_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("organizations.id"), nullable=False, index=True
    )

    # Usage metrics
    metric_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # ai_evaluations, video_interviews, storage_gb, api_calls
    metric_value: Mapped[int] = mapped_column(BigInteger, nullable=False)

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
