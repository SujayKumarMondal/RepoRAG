"""
RepoRAG Analysis model.
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


class Analysis(Base):
    """
    AI/codebase analysis associated with a repository.
    """

    __tablename__ = "analyses"

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
    # Analysis
    # ========================================================

    analysis_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )

    status: Mapped[str] = mapped_column(
        String(50),
        default="pending",
        nullable=False,
        index=True,
    )

    # ========================================================
    # Commit
    # ========================================================

    commit_sha: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )

    # ========================================================
    # Results
    # ========================================================

    summary: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    result: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    findings_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    # ========================================================
    # Error
    # ========================================================

    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # ========================================================
    # Timing
    # ========================================================

    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

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
        back_populates="analyses",
    )

    def __repr__(self) -> str:
        return (
            f"<Analysis "
            f"id={self.id} "
            f"type={self.analysis_type!r} "
            f"status={self.status!r}>"
        )