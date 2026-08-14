"""
RepoRAG CodeChunk model.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class CodeChunk(Base):
    """
    A semantically meaningful section of source code.
    """

    __tablename__ = "code_chunks"

    # ========================================================
    # Primary Key
    # ========================================================

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # ========================================================
    # File
    # ========================================================

    file_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "repository_files.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    # ========================================================
    # Chunk Information
    # ========================================================

    chunk_index: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    content_hash: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        index=True,
    )

    # ========================================================
    # Source Location
    # ========================================================

    start_line: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    end_line: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    start_byte: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    end_byte: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    # ========================================================
    # AST Information
    # ========================================================

    chunk_type: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    symbol_name: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    symbol_type: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    # ========================================================
    # Token Information
    # ========================================================

    token_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    # ========================================================
    # Metadata
    # ========================================================

    extra_metadata: Mapped[dict | None] = mapped_column(
    "metadata",
    JSONB,
    nullable=True,
)

    # ========================================================
    # Timestamp
    # ========================================================

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # ========================================================
    # Relationships
    # ========================================================

    file = relationship(
        "RepositoryFile",
        back_populates="chunks",
    )

    embedding = relationship(
        "Embedding",
        back_populates="chunk",
        uselist=False,
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return (
            f"<CodeChunk "
            f"id={self.id} "
            f"chunk_index={self.chunk_index}>"
        )