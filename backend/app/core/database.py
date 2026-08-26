"""
RepoRAG PostgreSQL database configuration.

Uses SQLAlchemy asynchronous engine with asyncpg.
"""

from collections.abc import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings


# ============================================================
# DATABASE URL
# ============================================================

DATABASE_URL = settings.DATABASE_URL

if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL is not configured. "
        "Please add DATABASE_URL to backend/.env"
    )


# ============================================================
# Normalize PostgreSQL driver
# ============================================================

if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace(
        "postgresql://",
        "postgresql+asyncpg://",
        1,
    )

elif DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace(
        "postgres://",
        "postgresql+asyncpg://",
        1,
    )


# ============================================================
# Remove unsupported asyncpg URL parameters
# ============================================================

if "?" in DATABASE_URL:

    base_url, query_string = DATABASE_URL.split("?", 1)

    allowed_params = []

    for parameter in query_string.split("&"):

        if not parameter:
            continue

        key = parameter.split("=", 1)[0].lower()

        # asyncpg does NOT accept these libpq parameters
        if key in {
            "sslmode",
            "channel_binding",
        }:
            continue

        allowed_params.append(parameter)

    if allowed_params:
        DATABASE_URL = (
            base_url
            + "?"
            + "&".join(allowed_params)
        )
    else:
        DATABASE_URL = base_url


# ============================================================
# SQLAlchemy Async Engine
# ============================================================

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    pool_recycle=1800,

    # IMPORTANT:
    # asyncpg uses "ssl", NOT "sslmode".
    connect_args={
        "ssl": "require",
    },
)


# ============================================================
# Async Session Factory
# ============================================================

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


# ============================================================
# SQLAlchemy Base
# ============================================================

class Base(DeclarativeBase):
    """
    Base class for all RepoRAG SQLAlchemy models.
    """

    pass


async def ensure_database_ready() -> None:
    """Create all missing tables before any DB writes."""
    async with engine.begin() as connection:
        await connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await connection.run_sync(Base.metadata.create_all)

        # Ensure application-level columns that may have been added
        # after the initial schema are present. This handles the
        # `users.github_access_token` column used to persist encrypted
        # GitHub tokens without requiring a full migration step here.
        await connection.execute(
            text(
                """
                ALTER TABLE IF EXISTS users
                ADD COLUMN IF NOT EXISTS github_access_token VARCHAR(2000)
                """
            )
        )


# ============================================================
# Database Dependency
# ============================================================

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that provides an AsyncSession.
    """

    async with AsyncSessionLocal() as session:

        try:
            yield session

        except Exception:
            await session.rollback()
            raise

        finally:
            await session.close()


# ============================================================
# Database Connection Test
# ============================================================

async def check_database_connection() -> None:
    """
    Check whether PostgreSQL is reachable.
    """

    async with engine.connect() as connection:

        await connection.execute(
            text("SELECT 1")
        )


# ============================================================
# Database Shutdown
# ============================================================

async def close_database() -> None:
    """
    Dispose the SQLAlchemy connection pool.
    """

    await engine.dispose()