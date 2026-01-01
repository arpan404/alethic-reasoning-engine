from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, ForeignKey
from database.engine import Base


class Organization(Base):
    __tablename__: str = "organizations"
    id: Mapped[int] = mapped_column(
        primary_key=True, nullable=False, autoincrement=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    workspace: Mapped[str] = mapped_column(String(255), nullable=False)
    logo: Mapped[str] = mapped_column(ForeignKey("file.id"))
    owner: Mapped[str] = mapped_column(ForeignKey("user.id"))
    subscription: Mapped[str] = mapped_column(ForeignKey("subscriptions.id"))
