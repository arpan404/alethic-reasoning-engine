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
    Enum as SQLEnum,
    Index,
)
from sqlalchemy.dialects.postgresql import VECTOR
from database.engine import Base
from datetime import datetime
from enum import Enum as PyEnum

# ================= Embedding Enums & Types ================== #
class EmbeddingEntityType(str, PyEnum):
    JOB = "job"
    CANDIDATE = "candidate"
    RESUME = "resume"
    TRANSCRIPT = "transcript"
    CHAT_MESSAGE = "chat_message"
    ASSESSMENT_RESPONSE = "assessment_response"

class EmbeddingMethod(str, PyEnum):
    COSINE = "cosine"
    EUCLIDEAN = "euclidean"
    DOT_PRODUCT = "dot_product"

# ==================== Embedding Table ===================== #
class Embedding(Base):
    """
    Generic embeddings table for all entity types using pgvector.
    """
    __tablename__ = "embeddings"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )

    # Polymorphic entity reference
    entity_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )
    entity_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)

    # Embedding vector (adjust dimension according to your model)
    embedding_vector = mapped_column(VECTOR(1024), nullable=False)

    # Embedding model info
    embedding_model_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("embedding_models.id"), nullable=False, index=True
    )

    # Source text & hash for deduplication
    source_text: Mapped[str | None] = mapped_column(Text)
    source_text_hash: Mapped[str | None] = mapped_column(
        String(64), index=True
    )

    # Chunking for long documents
    chunk_index: Mapped[int | None] = mapped_column(Integer)
    total_chunks: Mapped[int | None] = mapped_column(Integer)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Unique constraint: prevent duplicate embeddings per entity + model + chunk
    __table_args__ = (
        Index(
            "uq_embedding_entity_model_chunk",
            "entity_type",
            "entity_id",
            "embedding_model_id",
            "chunk_index",
            unique=True,
        ),
    )

# HNSW index for fast similarity search
Index(
    "idx_embeddings_vector_hnsw",
    Embedding.embedding_vector,
    postgresql_using="hnsw",
    postgresql_with={"m": 16, "ef_construction": 200},
    postgresql_ops={"embedding_vector": "vector_cosine_ops"},
)

# ==================== Embedding Models ===================== #
class EmbeddingModel(Base):
    """Track which embedding models are used."""
    __tablename__ = "embedding_models"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )

    model_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    model_version: Mapped[str | None] = mapped_column(String(50))
    model_provider: Mapped[str] = mapped_column(String(50), nullable=False)  # openai, cohere, huggingface
    embedding_dimensions: Mapped[int] = mapped_column(Integer, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

# ==================== Similarity Cache ===================== #
class SimilarityCache(Base):
    """
    Cache for similarity search results to optimize repeated queries.
    """
    __tablename__ = "similarity_cache"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )

    # Entity pairs
    entity_type_a: Mapped[EmbeddingEntityType] = mapped_column(
        SQLEnum(EmbeddingEntityType), nullable=False, index=True
    )
    entity_id_a: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    entity_type_b: Mapped[EmbeddingEntityType] = mapped_column(
        SQLEnum(EmbeddingEntityType), nullable=False, index=True
    )
    entity_id_b: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)

    # Similarity info
    similarity_score: Mapped[float] = mapped_column(Numeric(10, 8), nullable=False)
    similarity_method: Mapped[EmbeddingMethod] = mapped_column(
        SQLEnum(EmbeddingMethod), nullable=False
    )

    # Timestamps
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))