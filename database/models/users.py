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
)
from database.engine import Base
from database.models.organizations import OrganizationUsers
from database.security import ComplianceMixin, audit_changes
from database.security import (
    compliance_column,
    DataSensitivity,
    EncryptionType,
    GDPRDataCategory,
    DataRetentionPeriod,
)
from datetime import datetime
from enum import Enum as PyEnum
from typing import Any


# ==================== User Type ===================== #
class UserType(str, PyEnum):
    DEVELOPER = "developer"  # platform user with dev access
    ADMIN = "admin"  # platform admin with full access
    CUSTOMER_SUPPORT = "customer_support"  # support staff
    ORG_ADMIN = "org_admin"  # organization admin who manages org and subscriptions
    RECRUITER = "recruiter"  # org user who manages hiring
    CANDIDATE = "candidate"  # job applicant


@audit_changes
class User(Base, ComplianceMixin):
    """
    Core user identity and authentication with GDPR/SOC2 compliance.
    """

    __tablename__: str = "users"
    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )
    workos_user_id: Mapped[str | None] = mapped_column(
        String(100), unique=True, nullable=True, index=True
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
        BigInteger, ForeignKey("files.id"), nullable=True
    )

    user_type: Mapped[UserType] = mapped_column(
        SQLEnum(UserType, native_enum=False, length=50),
        nullable=False,
        default=UserType.RECRUITER,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Timestamps
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
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
    profile: Mapped["UserProfile"] = relationship(
        "UserProfile",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
    sessions: Mapped[list["UserSession"]] = relationship(
        "UserSession", back_populates="user", cascade="all, delete-orphan"
    )
    preferences: Mapped["UserPreferences"] = relationship(
        "UserPreferences",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
    organization_memberships: Mapped[list["OrganizationUsers"]] = relationship(
        "OrganizationUsers", back_populates="user", cascade="all, delete-orphan"
    )
    # job_applications: Mapped[list["JobApplication"]] = relationship(
    #     "JobApplication", back_populates="candidate", cascade="all, delete-orphan"
    # )


@audit_changes
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


# ================== User Preferences Keys ================== #
class PreferenceKey(str, PyEnum):
    # Notifications
    NOTIFICATIONS_EMAIL = "notifications_email"
    NOTIFICATIONS_PUSH = "notifications_push"
    NOTIFICATIONS_SMS = "notifications_sms"
    NOTIFICATIONS_MARKETING = "notifications_marketing"
    NOTIFICATIONS_SECURITY_ALERTS = "notifications_security_alerts"

    # Theme and UI
    THEME_DARK_MODE = "theme_dark_mode"
    THEME_COLOR = "theme_color"
    UI_DENSITY = "ui_density"
    FONT_SIZE = "font_size"

    # Locale and time
    LANGUAGE_PREFERENCE = "language_preference"
    CONTENT_LOCALE = "content_locale"
    TIMEZONE = "timezone"
    DATE_FORMAT = "date_format"
    TIME_FORMAT_24H = "time_format_24h"

    # Accessibility
    ACCESSIBILITY_REDUCE_MOTION = "accessibility_reduce_motion"
    ACCESSIBILITY_HIGH_CONTRAST = "accessibility_high_contrast"
    ACCESSIBILITY_SCREEN_READER = "accessibility_screen_reader"

    # Privacy
    PRIVACY_PROFILE_VISIBILITY = "privacy_profile_visibility"
    PRIVACY_DATA_SHARING = "privacy_data_sharing"
    PRIVACY_AD_PERSONALIZATION = "privacy_ad_personalization"

    # General
    EMAIL_DIGEST_FREQUENCY = "email_digest_frequency"
    DEFAULT_ORGANIZATION_ID = "default_organization_id"
    ENABLE_BETA_FEATURES = "enable_beta_features"
    START_PAGE = "start_page"
    AUTOSAVE_INTERVAL = "autosave_interval"


# ================== User Preferences Model ================== #
@audit_changes
class UserPreferences(Base):
    """User preferences storage."""

    __tablename__ = "user_preferences"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    # Preferences stored as JSON
    preferences: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default={},
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


# ================== User Profile Model ==================== #
@audit_changes
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
