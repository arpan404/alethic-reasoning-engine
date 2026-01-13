from typing import Any, TypedDict, TYPE_CHECKING

if TYPE_CHECKING:
    from database.models.applications import Application
    from database.models.talent_pools import TalentPool
    from database.models.pipelines import HiringPipeline
    from database.models.compliance import EEOCReport
    from database.models.referrals import ReferralProgram
    from database.models.background_checks import BackgroundCheckProvider
    from database.models.integrations import OrganizationIntegration
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import (
    String,
    Boolean,
    ForeignKey,
    BigInteger,
    DateTime,
    func,
    JSON,
    Enum as SQLEnum,
    Index,
)
from database.engine import Base
from datetime import datetime
from enum import Enum as PyEnum
from database.security import audit_changes


# ==================== Enums ===================== #
class OrganizationType(str, PyEnum):
    """
    Types of organizations.
    """

    NON_PROFIT = "non_profit"
    FOR_PROFIT = "for_profit"
    GOVERNMENT = "government"
    EDUCATIONAL = "educational"
    TECHNOLOGY = "technology"
    HEALTHCARE = "healthcare"
    FINANCE = "finance"
    RETAIL = "retail"
    MANUFACTURING = "manufacturing"
    FOOD_SERVICE = "food_service"
    ENTERTAINMENT = "entertainment"
    TRANSPORTATION = "transportation"
    ENERGY = "energy"
    TELECOMMUNICATIONS = "telecommunications"
    REAL_ESTATE = "real_estate"
    OTHER = "other"


class OrganizationRoles(str, PyEnum):
    """
    Roles within an organization.
    """

    OWNER = "owner"
    ADMIN = "admin"
    DIRECTOR = "director"
    MANAGER = "manager"
    MEMBER = "member"
    HEAD_OF_TALENT = "head_of_talent"
    RECRUITER = "recruiter"
    HIRING_MANAGER = "hiring_manager"
    INTERVIEWER = "interviewer"
    TALENT_ACQUISITION_LEAD = "talent_acquisition_lead"
    COMPLIANCE_OFFICER = "compliance_officer"
    FINANCE_CONTROLLER = "finance_controller"
    HUMAN_RESOURCES_DIRECTOR = "human_resources_director"
    OPERATIONS_MANAGER = "operations_manager"
    VIEWER = "viewer"
    CONTRACTOR = "contractor"


class InviteStatus(str, PyEnum):
    """Status of organization invites."""

    PENDING = "pending"
    ACCEPTED = "accepted"
    EXPIRED = "expired"
    REVOKED = "revoked"


@audit_changes
class Organization(Base):
    """
    Organization model representing companies or groups using the platform.
    """

    __tablename__: str = "organizations"
    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )
    workos_organization_id: Mapped[str | None] = mapped_column(
        String(100), unique=True, nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    workspace: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    logo: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("files.id"))
    owner: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))
    subscription: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("subscriptions.id")
    )
    organization_type: Mapped[OrganizationType] = mapped_column(
        SQLEnum(OrganizationType, native_enum=False, length=50),
        nullable=False,
        default=OrganizationType.OTHER,
    )
    # Timestamps and audit fields
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    updated_by: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id"), nullable=False
    )

    # Relationships
    members: Mapped[list["OrganizationUsers"]] = relationship(
        "OrganizationUsers", back_populates="organization", cascade="all, delete-orphan"
    )
    invites: Mapped[list["OrganizationUserInvite"]] = relationship(
        "OrganizationUserInvite",
        back_populates="organization",
        cascade="all, delete-orphan",
    )
    settings: Mapped["OrganizationSettings | None"] = relationship(
        "OrganizationSettings",
        back_populates="organization",
        uselist=False,
        cascade="all, delete-orphan",
    )
    departments: Mapped[list["JobDepartment"]] = relationship(
        "JobDepartment",
        back_populates="organization",
        cascade="all, delete-orphan",
    )
    job_settings: Mapped["OrganizationJobSettings | None"] = relationship(
        "OrganizationJobSettings",
        back_populates="organization",
        uselist=False,
        cascade="all, delete-orphan",
    )
    jobs: Mapped[list["Job"]] = relationship(
        "Job",
        back_populates="organization",
        cascade="all, delete-orphan",
    )
    applications: Mapped[list["Application"]] = relationship(
        "Application", back_populates="organization", cascade="all, delete-orphan"
    )
    offers: Mapped[list["Offer"]] = relationship(
        "Offer", back_populates="organization", cascade="all, delete-orphan"
    )
    talent_pools: Mapped[list["TalentPool"]] = relationship(
        "TalentPool", back_populates="organization", cascade="all, delete-orphan"
    )
    pipelines: Mapped[list["HiringPipeline"]] = relationship(
        "HiringPipeline", back_populates="organization", cascade="all, delete-orphan"
    )
    eoc_reports: Mapped[list["EEOCReport"]] = relationship(
        "EEOCReport", back_populates="organization", cascade="all, delete-orphan"
    )
    referral_program: Mapped["ReferralProgram | None"] = relationship(
        "ReferralProgram",
        back_populates="organization",
        uselist=False,
        cascade="all, delete-orphan",
    )
    background_check_providers: Mapped[list["BackgroundCheckProvider"]] = relationship(
        "BackgroundCheckProvider",
        back_populates="organization",
        cascade="all, delete-orphan",
    )
    integrations: Mapped[list["OrganizationIntegration"]] = relationship(
        "OrganizationIntegration",
        back_populates="organization",
        cascade="all, delete-orphan",
    )

    # Indexes
    __table_args__ = (
        Index("idx_organization_workspace", "workspace"),
        Index("idx_organization_workos", "workos_organization_id"),
        Index("idx_organization_owner", "owner"),
        Index("idx_organization_created_at", "created_at"),
    )


@audit_changes
class OrganizationUserInvite(Base):
    """
    Invitations sent to users to join an organization.
    """

    __tablename__: str = "organization_user_invites"
    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )
    organization_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    role: Mapped[OrganizationRoles] = mapped_column(
        SQLEnum(OrganizationRoles, native_enum=False, length=50),
        nullable=False,
        default=OrganizationRoles.MEMBER,
    )
    token: Mapped[str] = mapped_column(String(500), nullable=False, unique=True)
    is_accepted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    sent_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
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
    updated_by: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id"), nullable=False
    )

    # Relationships
    organization: Mapped["Organization"] = relationship(
        "Organization", back_populates="invites"
    )

    # Indexes
    __table_args__ = (
        Index("idx_org_invite_organization", "organization_id"),
        Index("idx_org_invite_email", "email"),
        Index("idx_org_invite_token", "token"),
        Index("idx_org_invite_expires", "expires_at"),
    )


@audit_changes
class OrganizationUsers(Base):
    """
    Association table for users belonging to organizations.
    """

    __tablename__: str = "organization_users"
    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )
    organization_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[OrganizationRoles] = mapped_column(
        SQLEnum(OrganizationRoles, native_enum=False, length=50),
        nullable=False,
        default=OrganizationRoles.MEMBER,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    updated_by: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id"), nullable=False
    )
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Relationships
    organization: Mapped["Organization"] = relationship(
        "Organization", back_populates="members"
    )
    user: Mapped["User"] = relationship("User", back_populates="organization_memberships", foreign_keys=[user_id])

    # Indexes
    __table_args__ = (
        Index("idx_org_users_organization", "organization_id"),
        Index("idx_org_users_user", "user_id"),
        Index("idx_org_users_role", "role"),
        Index("idx_org_users_org_role", "organization_id", "role"),
    )


# Forward reference for User type
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from database.models.users import User


# ================== Organization Settings Model ==================== #
class OrganizationSettingsKey(str, PyEnum):
    """
    Keys for organization settings.
    """

    NOTIFICATION_PREFERENCES = "notification_preferences"
    DATA_RETENTION_POLICY = "data_retention_policy"
    CUSTOM_BRANDING = "custom_branding"
    SECURITY_SETTINGS = "security_settings"
    INTEGRATIONS = "integrations"
    USER_MANAGEMENT_POLICIES = "user_management_policies"


class OrganizationAISettings(TypedDict):
    """
    AI-related settings for an organization.
    """

    enable_ai_features: bool
    ai_model_preference: str
    data_sharing_consent: bool
    custom_ai_prompts: dict[str, str]


@audit_changes
class OrganizationSettings(Base):
    """
    Organization specific configurations and settings.
    """

    __tablename__ = "organization_settings"
    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )
    organization_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    settings: Mapped[dict[str, Any]] = mapped_column(JSON, default={})
    ai_settings: Mapped[OrganizationAISettings | None] = mapped_column(JSON, default={})
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
    updated_by: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id"), nullable=False
    )

    # Relationships
    organization: Mapped["Organization"] = relationship(
        "Organization", back_populates="settings"
    )

    # Indexes
    __table_args__ = (
        Index("idx_org_settings_org", "organization_id"),
        # GIN indexes for JSON settings (PostgreSQL)
        Index(
            "idx_org_settings_json_gin",
            "settings",
            postgresql_using="gin"
        ),
        Index(
            "idx_org_settings_ai_json_gin",
            "ai_settings",
            postgresql_using="gin"
        ),
    )
