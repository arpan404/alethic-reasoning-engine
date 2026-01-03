from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, ForeignKey, BigInteger, DateTime, func, JSON, Boolean
from database.engine import Base
from datetime import datetime


class Organization(Base):
    __tablename__: str = "organizations"
    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    workspace: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    logo: Mapped[str] = mapped_column(BigInteger, ForeignKey("file.id"))
    owner: Mapped[str] = mapped_column(BigInteger, ForeignKey("users.id"))
    subscription: Mapped[str] = mapped_column(BigInteger, ForeignKey("subscriptions.id"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    updated_by: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)


class OrganizationUsers(Base):
    __tablename__: str = "organization_users"
    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )
    organization_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("organizations.id"), nullable=False
    )
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)
    role: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    updated_by: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)


class OrganizationSettings(Base):
    """Organization-specific configurations and settings."""
    __tablename__ = "organization_settings"
    
    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )
    organization_id: Mapped[int] = mapped_column(
        BigInteger, unique=True, nullable=False, index=True
    )
    
    # Settings (stored as JSON for flexibility)
    general_settings: Mapped[dict | None] = mapped_column(JSON, default={})
    recruitment_settings: Mapped[dict | None] = mapped_column(JSON, default={})
    ai_settings: Mapped[dict | None] = mapped_column(JSON, default={})
    notification_settings: Mapped[dict | None] = mapped_column(JSON, default={})
    
    # Feature flags
    enable_ai_screening: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    enable_video_interviews: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    enable_chat: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
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
    updated_by: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)