from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import (
    String,
    BigInteger,
    DateTime,
    func,
    Text,
    ForeignKey,
    Integer,
    Boolean,
    Numeric,
)
from sqlalchemy.dialects.postgresql import VECTOR
from database.engine import Base
from datetime import datetime


class Embedding(Base):
    """Generic embeddings table for all entity types using pgvector."""

    __tablename__ = "embeddings"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )

    # Entity reference (polymorphic)
    entity_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # job, candidate, resume, transcript, chat_message, assessment_response
    entity_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)

    # Embedding vector (1536 dimensions for OpenAI ada-002, adjust as needed)
    embedding_vector = mapped_column(VECTOR(1536), nullable=False)

    # Model info
    embedding_model_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("embedding_models.id"), nullable=False, index=True
    )

    # Source text (for reference)
    source_text: Mapped[str | None] = mapped_column(Text)
    source_text_hash: Mapped[str | None] = mapped_column(
        String(64), index=True
    )  # SHA-256 hash

    # Metadata
    chunk_index: Mapped[int | None] = mapped_column(Integer)  # For chunked embeddings
    total_chunks: Mapped[int | None] = mapped_column(Integer)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class EmbeddingModel(Base):
    """Track which embedding models are used."""

    __tablename__ = "embedding_models"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )

    # Model details
    model_name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    model_provider: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # openai, cohere, huggingface
    model_version: Mapped[str | None] = mapped_column(String(50))
    embedding_dimensions: Mapped[int] = mapped_column(Integer, nullable=False)

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class SimilarityCache(Base):
    """Cache for frequently computed similarities."""

    __tablename__ = "similarity_cache"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )

    # Entity pairs
    entity_type_a: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    entity_id_a: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    entity_type_b: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    entity_id_b: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)

    # Similarity score
    similarity_score: Mapped[float] = mapped_column(Numeric(10, 8), nullable=False)
    similarity_method: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # cosine, euclidean, dot_product

    # Timestamps
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
