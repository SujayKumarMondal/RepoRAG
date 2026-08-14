"""
RepoRAG Symbol model.
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


class Symbol(Base):
    """
    A symbol extracted from source code using AST / Tree-sitter.
    """

    __tablename__ = "symbols"

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
    # Symbol
    # ========================================================

    name: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        index=True,
    )

    qualified_name: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        index=True,
    )

    symbol_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )

    # ========================================================
    # Source Location
    # ========================================================

    start_line: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    end_line: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    start_column: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    end_column: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    # ========================================================
    # Code Signature
    # ========================================================

    signature: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    docstring: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # ========================================================
    # AST Metadata
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
        back_populates="symbols",
    )

    def __repr__(self) -> str:
        return (
            f"<Symbol "
            f"name={self.name!r} "
            f"type={self.symbol_type!r}>"
        )