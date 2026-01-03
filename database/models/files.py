from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, BigInteger, DateTime, func, Integer, Boolean, ForeignKey
from database.engine import Base
from datetime import datetime


class File(Base):
    """File storage and metadata management."""
    __tablename__ = "files"
    
    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )
    
    # File identification
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    original_name: Mapped[str] = mapped_column(String(255), nullable=False)
    key: Mapped[str] = mapped_column(String(500), unique=True, nullable=False, index=True)
    
    # File metadata
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    storage_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    bucket_name: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # File type categorization
    file_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # resume, cover_letter, video, image, document
    
    # Video-specific metadata (nullable for non-video files)
    duration_seconds: Mapped[int | None] = mapped_column(Integer)
    video_codec: Mapped[str | None] = mapped_column(String(50))
    resolution: Mapped[str | None] = mapped_column(String(20))  # e.g., "1920x1080"
    
    # Processing status
    processing_status: Mapped[str] = mapped_column(
        String(50), default="pending", nullable=False
    )  # pending, processing, completed, failed
    processing_error: Mapped[str | None] = mapped_column(String(1000))
    
    # Soft delete
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    
    # Ownership and access
    uploaded_by: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False, index=True)
    organization_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("organizations.id"), index=True)
    
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
