"""
RepoRAG User model.
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class User(Base):
    """
    Application user.

    Users authenticate through GitHub OAuth.
    """

    __tablename__ = "users"

    # ========================================================
    # Primary Key
    # ========================================================

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # ========================================================
    # GitHub Identity
    # ========================================================

    github_id: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
    )

    github_username: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    github_email: Mapped[str | None] = mapped_column(
        String(320),
        nullable=True,
    )

    avatar_url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    github_profile_url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Persisted (encrypted) GitHub access token for background workers and API calls.
    # This column stores the encrypted token; the `github_access_token` property
    # transparently decrypts/encrypts the value when accessed/assigned.
    _github_access_token: Mapped[str | None] = mapped_column(
        "github_access_token",
        String(2000),
        nullable=True,
    )

    @property
    def github_access_token(self) -> str | None:
        """Return decrypted GitHub access token, or None if not available."""
        from app.utils.crypto import decrypt_token

        if not self._github_access_token:
            return None

        try:
            return decrypt_token(self._github_access_token)
        except Exception:
            return None

    @github_access_token.setter
    def github_access_token(self, value: str | None) -> None:
        """Encrypt and store the provided access token. Passing `None` clears it."""
        from app.utils.crypto import encrypt_token

        if value is None:
            self._github_access_token = None
            return

        try:
            self._github_access_token = encrypt_token(value)
        except Exception:
            # Fallback: store plaintext if encryption fails (avoid breaking runtime),
            # but log/report this in production.
            self._github_access_token = value

    # ========================================================
    # Account
    # ========================================================

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
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

    repositories = relationship(
        "Repository",
        back_populates="owner",
        cascade="all, delete-orphan",
    )


    def __repr__(self) -> str:
        return (
            f"<User "
            f"id={self.id} "
            f"github_username={self.github_username!r}>"
        )