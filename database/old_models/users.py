from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Boolean, DateTime, func, BigInteger, Text, ForeignKey
from database.engine import Base
from database.security import (
    ComplianceMixin,
    compliance_column,
    DataSensitivity,
    GDPRDataCategory,
    DataRetentionPeriod,
    EncryptionType,
)
from datetime import datetime


class User(Base, ComplianceMixin):
    """Core user identity and authentication with GDPR/SOC 2 compliance."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
        info=compliance_column(
            sensitivity=DataSensitivity.RESTRICTED,
            encryption=EncryptionType.AT_REST,
            pii=True,
            gdpr_relevant=True,
            gdpr_category=GDPRDataCategory.IDENTITY,
            soc2_critical=True,
            requires_consent=False,  # Email is required for account
            retention_period=DataRetentionPeriod.YEARS_2,
            anonymize_on_delete=True,
        ),
    )
    username: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
        info=compliance_column(
            sensitivity=DataSensitivity.INTERNAL,
            pii=False,
            gdpr_relevant=True,
            retention_period=DataRetentionPeriod.YEARS_2,
            anonymize_on_delete=True,
        ),
    )
    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        info=compliance_column(
            sensitivity=DataSensitivity.RESTRICTED,
            encryption=EncryptionType.END_TO_END,
            soc2_critical=True,
            mask_in_logs=True,
            retention_period=DataRetentionPeriod.INDEFINITE,
        ),
    )

    # Profile (PII with GDPR categories)
    first_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        info=compliance_column(
            sensitivity=DataSensitivity.RESTRICTED,
            pii=True,
            gdpr_relevant=True,
            gdpr_category=GDPRDataCategory.IDENTITY,
            retention_period=DataRetentionPeriod.YEARS_2,
            anonymize_on_delete=True,
        ),
    )
    last_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        info=compliance_column(
            sensitivity=DataSensitivity.RESTRICTED,
            pii=True,
            gdpr_relevant=True,
            gdpr_category=GDPRDataCategory.IDENTITY,
            retention_period=DataRetentionPeriod.YEARS_2,
            anonymize_on_delete=True,
        ),
    )
    phone: Mapped[str | None] = mapped_column(
        String(20),
        info=compliance_column(
            sensitivity=DataSensitivity.RESTRICTED,
            encryption=EncryptionType.AT_REST,
            pii=True,
            gdpr_relevant=True,
            gdpr_category=GDPRDataCategory.CONTACT,
            requires_consent=True,
            retention_period=DataRetentionPeriod.YEARS_2,
            anonymize_on_delete=True,
        ),
    )
    avatar_file_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("files.id", ondelete="SET NULL"), index=True
    )

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Timestamps
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    email_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
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
    profile: Mapped["UserProfile"] = relationship(
        "UserProfile",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
    sessions: Mapped[list["UserSession"]] = relationship(
        "UserSession", back_populates="user", cascade="all, delete-orphan"
    )
    preferences: Mapped["UserPreference"] = relationship(
        "UserPreference",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
    organization_memberships: Mapped[list["OrganizationUsers"]] = relationship(
        "OrganizationUsers",
        foreign_keys="OrganizationUsers.user_id",
        back_populates="user",
    )


class UserProfile(Base, ComplianceMixin):
    """Extended user profile information with GDPR compliance."""

    __tablename__ = "user_profiles"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )

    # Professional info
    title: Mapped[str | None] = mapped_column(String(200))
    company: Mapped[str | None] = mapped_column(String(200))
    bio: Mapped[str | None] = mapped_column(Text)
    linkedin_url: Mapped[str | None] = mapped_column(String(500))
    website_url: Mapped[str | None] = mapped_column(String(500))

    # Location (PII - GDPR Contact category)
    city: Mapped[str | None] = mapped_column(
        String(100),
        info=compliance_column(
            sensitivity=DataSensitivity.CONFIDENTIAL,
            pii=True,
            gdpr_relevant=True,
            gdpr_category=GDPRDataCategory.CONTACT,
            retention_period=DataRetentionPeriod.YEARS_2,
            anonymize_on_delete=True,
        ),
    )
    state: Mapped[str | None] = mapped_column(
        String(100),
        info=compliance_column(
            sensitivity=DataSensitivity.CONFIDENTIAL,
            pii=True,
            gdpr_relevant=True,
            gdpr_category=GDPRDataCategory.CONTACT,
            retention_period=DataRetentionPeriod.YEARS_2,
            anonymize_on_delete=True,
        ),
    )
    country: Mapped[str | None] = mapped_column(String(100))
    timezone: Mapped[str | None] = mapped_column(String(50))

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
    user: Mapped["User"] = relationship("User", back_populates="profile")


class UserSession(Base, ComplianceMixin):
    """Active user sessions for security tracking with SOC 2 compliance."""

    __tablename__ = "user_sessions"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Session data (sensitive - SOC 2 critical)
    session_token: Mapped[str] = mapped_column(
        String(500),
        unique=True,
        nullable=False,
        index=True,
        info=compliance_column(
            sensitivity=DataSensitivity.RESTRICTED,
            encryption=EncryptionType.END_TO_END,
            soc2_critical=True,
            mask_in_logs=True,
            retention_period=DataRetentionPeriod.DAYS_90,
        ),
    )
    refresh_token: Mapped[str | None] = mapped_column(
        String(500),
        unique=True,
        index=True,
        info=compliance_column(
            sensitivity=DataSensitivity.RESTRICTED,
            encryption=EncryptionType.END_TO_END,
            soc2_critical=True,
            mask_in_logs=True,
            retention_period=DataRetentionPeriod.DAYS_90,
        ),
    )
    ip_address: Mapped[str | None] = mapped_column(
        String(45),
        info=compliance_column(
            sensitivity=DataSensitivity.RESTRICTED,
            pii=True,
            gdpr_relevant=True,
            gdpr_category=GDPRDataCategory.TECHNICAL,
            soc2_critical=True,
            retention_period=DataRetentionPeriod.DAYS_90,
            anonymize_on_delete=True,
        ),
    )
    user_agent: Mapped[str | None] = mapped_column(
        Text,
        info=compliance_column(
            sensitivity=DataSensitivity.INTERNAL,
            gdpr_relevant=True,
            gdpr_category=GDPRDataCategory.TECHNICAL,
            retention_period=DataRetentionPeriod.DAYS_90,
        ),
    )

    # Timestamps
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    last_activity_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="sessions")


class UserPreference(Base):
    """User-specific settings and preferences."""

    __tablename__ = "user_preferences"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )

    # Preferences (GDPR - Behavioral data)
    theme: Mapped[str] = mapped_column(
        String(20),
        default="light",
        nullable=False,
        info=compliance_column(
            sensitivity=DataSensitivity.INTERNAL,
            gdpr_relevant=True,
            gdpr_category=GDPRDataCategory.BEHAVIORAL,
            retention_period=DataRetentionPeriod.YEARS_2,
        ),
    )
    language: Mapped[str] = mapped_column(
        String(10),
        default="en",
        nullable=False,
        info=compliance_column(
            sensitivity=DataSensitivity.INTERNAL,
            gdpr_relevant=True,
            gdpr_category=GDPRDataCategory.BEHAVIORAL,
            retention_period=DataRetentionPeriod.YEARS_2,
        ),
    )
    email_notifications: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    push_notifications: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    sms_notifications: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
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
    user: Mapped["User"] = relationship("User", back_populates="preferences")
