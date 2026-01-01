from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, ForeignKey, Enum as SQLEnum
from database.engine import Base
from enum import Enum as PyEnum


class SubcriptionTier(str, PyEnum):
    FREE = "free"
    BASIC = "basic"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"


class Subscription(Base):
    __tablename__: str = "subscriptions"
    id: Mapped[int] = mapped_column(primary_key=True, nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id"), nullable=False
    )
    plan: Mapped[SubcriptionTier] = mapped_column(
        SQLEnum(SubcriptionTier, name="subscription_tier"),
        default=SubcriptionTier.FREE,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(100), nullable=False)
