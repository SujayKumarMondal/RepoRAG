"""
RepoRAG repository API schemas.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# ============================================================
# Base Repository Schema
# ============================================================

class RepositoryBase(BaseModel):
    """
    Common repository fields.
    """

    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Repository name",
    )

    full_name: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="GitHub full repository name",
    )

    description: str | None = Field(
        default=None,
        description="Repository description",
    )

    html_url: str = Field(
        ...,
        description="GitHub repository URL",
    )

    default_branch: str = Field(
        default="main",
        max_length=255,
        description="Default repository branch",
    )

    language: str | None = Field(
        default=None,
        max_length=100,
        description="Primary repository language",
    )

    is_private: bool = Field(
        default=False,
        description="Whether the repository is private",
    )


# ============================================================
# Repository Create
# ============================================================

class RepositoryCreate(BaseModel):
    """
    Request body for registering a GitHub repository.
    """

    github_repo_id: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="GitHub repository ID",
    )

    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
    )

    full_name: str = Field(
        ...,
        min_length=1,
        max_length=500,
    )

    description: str | None = None

    html_url: str

    clone_url: str | None = None

    default_branch: str = Field(
        default="main",
        max_length=255,
    )

    language: str | None = None

    stars: int = Field(
        default=0,
        ge=0,
    )

    forks: int = Field(
        default=0,
        ge=0,
    )

    size_kb: int = Field(
        default=0,
        ge=0,
    )

    is_private: bool = False

    extra_metadata: dict[str, Any] | None = None


# ============================================================
# Repository Response
# ============================================================

class RepositoryResponse(RepositoryBase):
    """
    Repository API response.
    """

    model_config = ConfigDict(
        from_attributes=True,
    )

    id: UUID

    owner_id: UUID

    github_repo_id: str

    clone_url: str | None = None

    stars: int

    forks: int

    size_kb: int

    ingestion_status: str

    ingestion_error: str | None = None

    last_ingested_commit: str | None = None

    created_at: datetime

    updated_at: datetime


# ============================================================
# Repository List Item
# ============================================================

class RepositoryListItem(BaseModel):
    """
    Lightweight repository representation for list APIs.
    """

    model_config = ConfigDict(
        from_attributes=True,
    )

    id: UUID

    github_repo_id: str

    name: str

    full_name: str

    description: str | None = None

    html_url: str

    default_branch: str

    language: str | None = None

    stars: int

    forks: int

    is_private: bool

    ingestion_status: str

    created_at: datetime

    updated_at: datetime


# ============================================================
# Repository List Response
# ============================================================

class RepositoryListResponse(BaseModel):
    """
    Paginated repository response.
    """

    items: list[RepositoryListItem]

    total: int = Field(
        ...,
        ge=0,
    )

    page: int = Field(
        default=1,
        ge=1,
    )

    page_size: int = Field(
        default=20,
        ge=1,
        le=100,
    )

    pages: int = Field(
        default=0,
        ge=0,
    )


# ============================================================
# Repository Statistics
# ============================================================

class RepositoryStatistics(BaseModel):
    """
    Codebase statistics.
    """

    total_files: int = Field(
        default=0,
        ge=0,
    )

    total_chunks: int = Field(
        default=0,
        ge=0,
    )

    total_symbols: int = Field(
        default=0,
        ge=0,
    )

    total_dependencies: int = Field(
        default=0,
        ge=0,
    )

    total_lines: int = Field(
        default=0,
        ge=0,
    )

    total_size_bytes: int = Field(
        default=0,
        ge=0,
    )

    languages: dict[str, int] = Field(
        default_factory=dict,
    )


# ============================================================
# Repository Detail Response
# ============================================================

class RepositoryDetailResponse(RepositoryResponse):
    """
    Detailed repository response.
    """

    statistics: RepositoryStatistics | None = None