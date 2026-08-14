"""
RepoRAG Repository model.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Repository(Base):
    """
    GitHub repository registered with RepoRAG.
    """

    __tablename__ = "repositories"

    __table_args__ = (
        UniqueConstraint(
            "owner_id",
            "github_repo_id",
            name="uq_repository_owner_github_repo",
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
    # Owner
    # ========================================================

    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "users.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    # ========================================================
    # GitHub Information
    # ========================================================

    github_repo_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    full_name: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        index=True,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    html_url: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    clone_url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    default_branch: Mapped[str] = mapped_column(
        String(255),
        default="main",
        nullable=False,
    )

    # ========================================================
    # Repository Metadata
    # ========================================================

    language: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    stars: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    forks: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    size_kb: Mapped[int] = mapped_column(
        BigInteger,
        default=0,
        nullable=False,
    )

    is_private: Mapped[bool] = mapped_column(
        default=False,
        nullable=False,
    )

    # ========================================================
    # Ingestion State
    # ========================================================

    ingestion_status: Mapped[str] = mapped_column(
        String(50),
        default="pending",
        nullable=False,
        index=True,
    )

    ingestion_error: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    last_ingested_commit: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    # ========================================================
    # Additional GitHub Metadata
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

    owner = relationship(
        "User",
        back_populates="repositories",
    )

    files = relationship(
        "RepositoryFile",
        back_populates="repository",
        cascade="all, delete-orphan",
    )


    analyses = relationship(
        "Analysis",
        back_populates="repository",
        cascade="all, delete-orphan",
    )

    dependencies = relationship(
        "Dependency",
        back_populates="repository",
        cascade="all, delete-orphan",
    )
    ingestion_jobs = relationship(
        "IngestionJob",
        back_populates="repository",
        cascade="all, delete-orphan",
    )

    branches = relationship(
        "Branch",
        back_populates="repository",
        cascade="all, delete-orphan",
    )

    commits = relationship(
        "Commit",
        back_populates="repository",
        cascade="all, delete-orphan",
    )

    contributors = relationship(
        "Contributor",
        back_populates="repository",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return (
            f"<Repository "
            f"id={self.id} "
            f"full_name={self.full_name!r}>"
        )