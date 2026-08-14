"""
RepoRAG Embedding model.
"""

import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector

from sqlalchemy import (
    DateTime,
    ForeignKey,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Embedding(Base):
    """
    Vector embedding associated with a code chunk.
    """

    __tablename__ = "embeddings"

    # ========================================================
    # Primary Key
    # ========================================================

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # ========================================================
    # Code Chunk
    # ========================================================

    chunk_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "code_chunks.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        unique=True,
        index=True,
    )

    # ========================================================
    # Vector
    # ========================================================

    # 1536 is a common embedding dimension.
    #
    # IMPORTANT:
    # Change this value if the selected embedding model
    # produces a different vector dimension.

    vector: Mapped[list[float]] = mapped_column(
        Vector(1536),
        nullable=False,
    )

    # ========================================================
    # Provider Information
    # ========================================================

    provider: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    model: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    # ========================================================
    # Timestamp
    # ========================================================

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # ========================================================
    # Relationships
    # ========================================================

    chunk = relationship(
        "CodeChunk",
        back_populates="embedding",
    )

    def __repr__(self) -> str:
        return (
            f"<Embedding "
            f"id={self.id} "
            f"provider={self.provider!r} "
            f"model={self.model!r}>"
        )