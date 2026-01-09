from typing import Literal, TypedDict, Union
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import (
    String,
    Boolean,
    ForeignKey,
    BigInteger,
    DateTime,
    Text,
    func,
    JSON,
    Enum as SQLEnum,
)
from database.engine import Base
from datetime import datetime
from enum import Enum as PyEnum


# ================== Message Enum ====================
class MessageStatus(str, PyEnum):
    """Message delivery status."""

    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    VIEWED = "viewed"
    FAILED = "failed"


# ================== Template Config Type ====================
class TemplateConfigType(TypedDict):
    """Configuration for email templates."""

    type: Union[Literal["subject"], Literal["body_html"], Literal["body_text"]]
    placeholder_variables: list[str]  # List of placeholder variable names
    description: str  # Description of the template purpose
    template_string: str  # The actual template string with placeholders


# ================== Email Template Model ====================
class EmailTemplate(Base):
    """
    Reusable email templates.
    Created templated can be used for various communcation purposes.
    Organizations can create and manage their own templates too.
    """

    __tablename__ = "email_templates"
    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )
    organization_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("organizations.id"), nullable=True, index=True
    )  # if null, template is global and can be used by any organization in the alethic system

    # Template details
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    template_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # application_received, interview_invite, rejection, offer
    template_data: Mapped[list[TemplateConfigType]] = mapped_column(
        JSON
    )  # JSON field storing subject, body_html, body_text with placeholders

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # audit metadata
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
