from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Boolean, ForeignKey, BigInteger, DateTime, func
from database.engine import Base
from database.security import ComplianceMixin, audit_changes


@audit_changes
class User(Base, ComplianceMixin):
    pass
