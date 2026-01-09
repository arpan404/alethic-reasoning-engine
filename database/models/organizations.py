from typing import Any, TypedDict
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import (
    String,
    Boolean,
    ForeignKey,
    BigInteger,
    DateTime,
    func,
    JSON,
    Enum as SQLEnum,
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
    TALENT_ACQUISITION_LEAD = "talent_acquisition_lead"
    COMPLIANCE_OFFICER = "compliance_officer"
    FINANCE_CONTROLLER = "finance_controller"
    HUMAN_RESOURCES_DIRECTOR = "human_resources_director"
    OPERATIONS_MANAGER = "operations_manager"
    VIEWER = "viewer"
    CONTRACTOR = "contractor"


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
        SQLEnum(OrganizationType), nullable=False, default=OrganizationType.OTHER
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
        BigInteger, ForeignKey("organizations.id"), nullable=False
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    role: Mapped[OrganizationRoles] = mapped_column(
        SQLEnum(OrganizationRoles), nullable=False, default=OrganizationRoles.MEMBER
    )
    token: Mapped[str] = mapped_column(String(500), nullable=False, unique=True)
    is_accepted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    sent_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
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
        BigInteger, ForeignKey("organizations.id"), nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id"), nullable=False
    )
    role: Mapped[OrganizationRoles] = mapped_column(
        SQLEnum(OrganizationRoles), nullable=False, default=OrganizationRoles.MEMBER
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


# ================== Organization Settings Model ==================== #
# TODO: Expand settings as needed
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
        BigInteger, ForeignKey("organizations.id"), nullable=False, index=True
    )
    settings: Mapped[dict[OrganizationSettingsKey, Any]] = mapped_column(
        JSON, default={}
    )
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
