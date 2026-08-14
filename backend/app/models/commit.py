"""
Repository commit model.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Commit(Base):
    __tablename__ = "commits"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    repository_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False, index=True
    )

    sha: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    message: Mapped[str | None] = mapped_column(Text, nullable=True)

    author_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    author_email: Mapped[str | None] = mapped_column(String(255), nullable=True)

    authored_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    html_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    repository = relationship("Repository", back_populates="commits")

    def __repr__(self) -> str:
        return f"<Commit sha={self.sha!r} repo={self.repository_id}>"
