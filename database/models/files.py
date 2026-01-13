from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import (
    String,
    Boolean,
    ForeignKey,
    BigInteger,
    DateTime,
    func,
    Enum as SQLEnum,
    Integer,
    Index,
)
from database.engine import Base
from datetime import datetime
from enum import Enum as PyEnum
from sqlalchemy.dialects.postgresql import ARRAY
from typing import List, TypedDict


# ================== File Enums ====================
class FileType(str, PyEnum):
    """Types of files that can be uploaded."""

    RESUME = "resume"
    COVER_LETTER = "cover_letter"
    VIDEO = "video"
    IMAGE = "image"
    DOCUMENT = "document"
    TRANSCRIPT = "transcript"
    AVATAR = "avatar"
    LOGO = "logo"


class VideoCodec(str, PyEnum):
    """Video codecs supported."""

    H264 = "H.264"
    VP9 = "VP9"
    AV1 = "AV1"
    HEVC = "HEVC"


class VideoResolution(str, PyEnum):
    """Video resolutions supported."""

    P360 = "640x360"
    P480 = "854x480"
    P720 = "1280x720"
    P1080 = "1920x1080"
    P1440 = "2560x1440"
    P4K = "3840x2160"


class FileProcessingStatus(str, PyEnum):
    """File processing status."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class FileCompressionStatus(str, PyEnum):
    """File compression status."""

    NOT_COMPRESSED = "not_compressed"
    COMPRESSING = "compressing"
    COMPRESSED = "compressed"
    FAILED = "failed"


class FileAccessLevel(str, PyEnum):
    """Access levels for files."""

    PRIVATE = "private"  # only accessible to uploader and shared users
    PUBLIC = "public"  # accessible to public links
    ORGANIZATION = "organization"  # accessible to entire organization
    ALETHICS = "alethics"  # accessible to Alethics admins and AI systems


class FileAccessPermission(str, PyEnum):
    """Permissions for file access."""

    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    UPDATE = "update"


# ================== File TypedDicts ====================
class FileAccessSettings(TypedDict):
    """
    Settings for file access by a user or role with specific permissions.
    """

    accessible_by: int | str  # user id or role name or role uid
    permissions: List[FileAccessPermission]


class FileAccessibleBy(TypedDict):
    """Who can access a file."""

    users: List[FileAccessSettings]
    roles: List[FileAccessSettings]


# ================== File Model ====================
class File(Base):
    """
    File storage and metadata management.
    """

    __tablename__ = "files"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )

    # File identification
    name: Mapped[str] = mapped_column(
        String(255), nullable=False, index=True, unique=True
    )
    original_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    key: Mapped[str] = mapped_column(
        String(500), unique=True, nullable=False, index=True
    )
    # File metadata
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    storage_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    bucket_name: Mapped[str] = mapped_column(String(255), nullable=False)

    # File type categorization
    file_type: Mapped[FileType] = mapped_column(
        SQLEnum(FileType, native_enum=False, length=50), nullable=False, index=True
    )

    # Video-specific metadata (nullable for non-video files)
    duration_seconds: Mapped[int | None] = mapped_column(Integer)
    video_codec: Mapped[VideoCodec | None] = mapped_column(
        SQLEnum(VideoCodec, native_enum=False, length=50)
    )
    resolution: Mapped[VideoResolution | None] = mapped_column(
        SQLEnum(VideoResolution, native_enum=False, length=50)
    )

    # Processing status
    processing_status: Mapped[FileProcessingStatus] = mapped_column(
        SQLEnum(FileProcessingStatus, native_enum=False, length=50),
        default=FileProcessingStatus.PENDING,
        nullable=False,
    )
    processing_error: Mapped[str | None] = mapped_column(String(1000))
    compression_status: Mapped[FileCompressionStatus] = mapped_column(
        SQLEnum(FileCompressionStatus, native_enum=False, length=50),
        default=FileCompressionStatus.NOT_COMPRESSED,
        nullable=False,
    )
    compression_error: Mapped[str | None] = mapped_column(String(1000))

    # Soft delete
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Ownership and access
    uploaded_by: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id"), nullable=True, index=True
    )
    organization_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("organizations.id"), nullable=True, index=True
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
    access_controls: Mapped[list["FileAccessControl"]] = relationship(
        "FileAccessControl", back_populates="file", cascade="all, delete-orphan"
    )
    share_configs: Mapped[list["FileShareConfig"]] = relationship(
        "FileShareConfig", back_populates="file", cascade="all, delete-orphan"
    )
    tags: Mapped[list["FileTag"]] = relationship(
        "FileTag", back_populates="file", cascade="all, delete-orphan"
    )

    # Indexes
    __table_args__ = (
        Index("idx_file_processing", "processing_status"),
        Index("idx_file_compression", "compression_status"),
        Index("idx_file_deleted", "is_deleted", "deleted_at"),
        Index("idx_file_created", "created_at"),
        # Composite index for file queries
        Index("idx_file_org_type", "organization_id", "file_type"),
        Index("idx_file_uploader", "uploaded_by", "created_at"),
        # Partial index for active files
        Index(
            "idx_file_active",
            "organization_id",
            "file_type",
            "created_at",
            postgresql_where="is_deleted = false"
        ),
    )


# ================== File Access Control Model ====================
class FileAccessControl(Base):
    """
    Access control settings for files.
    """

    __tablename__ = "file_access_controls"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )
    file_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("files.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # access levels
    access_level: Mapped[FileAccessLevel] = mapped_column(
        SQLEnum(FileAccessLevel, native_enum=False, length=50),
        default=FileAccessLevel.PRIVATE,
        nullable=False,
    )

    users_with_access: Mapped[list[str]] = mapped_column(
        ARRAY(String), nullable=False, default=[]
    )
    roles_with_access: Mapped[list[str]] = mapped_column(
        ARRAY(String), nullable=False, default=[]
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

    # Relationships
    file: Mapped["File"] = relationship("File", back_populates="access_controls")


# ================== File Share Config Model ====================
class FileShareConfig(Base):
    """
    Configuration for sharing files with external entities.
    """

    __tablename__ = "file_share_configs"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )
    file_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("files.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    shareable_link: Mapped[str] = mapped_column(
        String(500), unique=True, nullable=False
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
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
    file: Mapped["File"] = relationship("File", back_populates="share_configs")


# ================== File Tag Model ====================
class FileTag(Base):
    """
    Tags associated with files for categorization and searchability.
    """

    __tablename__ = "file_tags"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )
    file_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("files.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tag: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

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
    file: Mapped["File"] = relationship("File", back_populates="tags")
