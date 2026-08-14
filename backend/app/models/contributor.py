"""
Repository contributor model.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Contributor(Base):
    __tablename__ = "contributors"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    repository_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False, index=True
    )

    login: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    contributions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    avatar_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    html_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    repository = relationship("Repository", back_populates="contributors")

    def __repr__(self) -> str:
        return f"<Contributor login={self.login!r} contributions={self.contributions}>"
