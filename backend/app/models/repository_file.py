"""
RepoRAG RepositoryFile model.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class RepositoryFile(Base):
    """
    A source file belonging to a repository.
    """

    __tablename__ = "repository_files"

    __table_args__ = (
        UniqueConstraint(
            "repository_id",
            "path",
            name="uq_repository_file_path",
        ),
    )

    # ========================================================
    # Primary Key
    # ========================================================

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # ========================================================
    # Repository
    # ========================================================

    repository_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "repositories.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    # ========================================================
    # File Information
    # ========================================================

    path: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    filename: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )

    extension: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    language: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    size_bytes: Mapped[int] = mapped_column(
        BigInteger,
        default=0,
        nullable=False,
    )

    # ========================================================
    # Git Information
    # ========================================================

    blob_sha: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    commit_sha: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    # ========================================================
    # Processing
    # ========================================================

    is_binary: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    is_ignored: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    processing_status: Mapped[str] = mapped_column(
        String(50),
        default="pending",
        nullable=False,
        index=True,
    )

    processing_error: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # ========================================================
    # File Metadata
    # ========================================================

    extra_metadata: Mapped[dict | None] = mapped_column(
    "metadata",
    JSONB,
    nullable=True,
)

    # ========================================================
    # Timestamps
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

    repository = relationship(
        "Repository",
        back_populates="files",
    )

    chunks = relationship(
        "CodeChunk",
        back_populates="file",
        cascade="all, delete-orphan",
    )

    symbols = relationship(
        "Symbol",
        back_populates="file",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return (
            f"<RepositoryFile "
            f"id={self.id} "
            f"path={self.path!r}>"
        )