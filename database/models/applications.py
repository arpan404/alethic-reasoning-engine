from sqlalchemy.orm import mapped_column, Mapped
from sqlalchemy import String, ForeignKey, JSON
from database.engine import Base


class Applications(Base):
    __tablename__: str = "applicants"
    id: Mapped[int] = mapped_column(
        primary_key=True, nullable=False, autoincrement=True
    )
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id"), nullable=False)
    candidate_id: Mapped[int | None] = mapped_column(
        ForeignKey("candidates.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(100), nullable=False)
    resume: Mapped[int] = mapped_column(ForeignKey("files.id"))
    cover_letter: Mapped[int | None] = mapped_column(ForeignKey("files.id"))
    application_data: Mapped[dict] = mapped_column(
        JSON, nullable=True, default={}
    )
    application_metadata : Mapped[dict] = mapped_column(
        JSON, nullable=True, default={}
    )
    applied_at: Mapped[str] = mapped_column(String(100), nullable=False)
    updated_at: Mapped[str] = mapped_column(String(100), nullable=False)
    updated_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    