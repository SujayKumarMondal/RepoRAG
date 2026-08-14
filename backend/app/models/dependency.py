"""
RepoRAG Dependency model.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
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


class Dependency(Base):
    """
    Represents a dependency relationship inside a repository.
    """

    __tablename__ = "dependencies"

    __table_args__ = (
        UniqueConstraint(
            "repository_id",
            "source_file_id",
            "target_file_id",
            "dependency_type",
            name="uq_dependency_edge",
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
    # Source / Target
    # ========================================================

    source_file_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "repository_files.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    target_file_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "repository_files.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    # ========================================================
    # Dependency Information
    # ========================================================

    dependency_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )

    source_symbol: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    target_symbol: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
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

    # ========================================================
    # Relationships
    # ========================================================

    repository = relationship(
        "Repository",
        back_populates="dependencies",
    )

    source_file = relationship(
        "RepositoryFile",
        foreign_keys=[source_file_id],
    )

    target_file = relationship(
        "RepositoryFile",
        foreign_keys=[target_file_id],
    )

    def __repr__(self) -> str:
        return (
            f"<Dependency "
            f"source={self.source_file_id} "
            f"target={self.target_file_id} "
            f"type={self.dependency_type!r}>"
        )