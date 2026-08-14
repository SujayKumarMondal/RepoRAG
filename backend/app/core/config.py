"""
RepoRAG application configuration.
"""

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_DIR = Path(__file__).resolve().parents[2]
ENV_FILE = BACKEND_DIR / ".env"


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables
    and the backend/.env file.
    """

    # =========================================================
    # Application
    # =========================================================

    APP_NAME: str = "RepoRAG"
    APP_VERSION: str = "0.1.0"
    APP_ENV: str = "development"

    # =========================================================
    # FastAPI
    # =========================================================

    HOST: str = "0.0.0.0"
    PORT: int = 9001

    # =========================================================
    # Database
    # =========================================================

    DATABASE_URL: str = Field(
        default="",
        description="PostgreSQL database connection URL",
    )

    # =========================================================
    # Redis
    # =========================================================

    REDIS_URL: str = "redis://localhost:6379/0"

    # =========================================================
    # JWT
    # =========================================================

    SECRET_KEY: str = Field(
        default="",
        description="Secret key used for signing JWT tokens",
    )

    ALGORITHM: str = "HS256"

    ACCESS_TOKEN_EXPIRE_MINUTES: int = 43200

    # =========================================================
    # GitHub OAuth
    # =========================================================

    GITHUB_CLIENT_ID: str = ""

    GITHUB_CLIENT_SECRET: str = ""

    GITHUB_REDIRECT_URI: str = (
        "http://localhost:9001/api/v1/auth/github/callback"
    )

    GITHUB_API_URL: str = "https://api.github.com"

    # =========================================================
    # LLM
    # =========================================================

    LLM_PROVIDER: str = ""

    LLM_API_KEY: str = ""

    LLM_MODEL: str = ""

    # =========================================================
    # Embeddings
    # =========================================================

    EMBEDDING_PROVIDER: str = ""

    EMBEDDING_API_KEY: str = ""

    EMBEDDING_MODEL: str = ""

    # =========================================================
    # Pydantic Settings configuration
    # =========================================================

    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """
    Return a cached Settings instance.

    Using lru_cache ensures the .env configuration
    is loaded only once during application lifetime.
    """

    return Settings()


settings = get_settings()