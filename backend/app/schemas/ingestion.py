"""
RepoRAG repository ingestion API schemas.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# ============================================================
# Ingestion Request
# ============================================================

class IngestionRequest(BaseModel):
    """
    Request to start repository ingestion.
    """

    model_config = ConfigDict(
        extra="forbid",
    )

    repository_id: int = Field(
        ...,
        description="RepoRAG repository ID",
    )

    branch: str | None = Field(
        default=None,
        max_length=255,
        description="Branch to ingest. If omitted, the repository default branch is used.",
    )

    commit_sha: str | None = Field(
        default=None,
        max_length=100,
        description="Specific commit SHA to ingest. If omitted, the latest commit is used.",
    )

    force: bool = Field(
        default=False,
        description="Force complete re-ingestion even if the repository has already been ingested.",
    )

    include_tests: bool = Field(
        default=True,
        description="Whether test files should be included.",
    )

    include_documentation: bool = Field(
        default=True,
        description="Whether documentation files should be included.",
    )


# ============================================================
# Ingestion Response
# ============================================================

class IngestionResponse(BaseModel):
    """
    Response after an ingestion job is created.
    """

    model_config = ConfigDict(
        from_attributes=True,
    )

    job_id: UUID = Field(
        ...,
        description="Unique ingestion job ID.",
    )

    repository_id: int = Field(
        ...,
        description="RepoRAG repository ID.",
    )

    status: str = Field(
        ...,
        description="Current ingestion job status.",
        examples=["queued", "processing", "completed", "failed", "cancelled"],
    )

    message: str = Field(
        ...,
        description="Human-readable status message.",
    )

    created_at: datetime = Field(
        ...,
        description="UTC timestamp when the ingestion job was created.",
    )


# ============================================================
# Ingestion Progress
# ============================================================

class IngestionProgress(BaseModel):
    """
    Current ingestion progress.
    """

    model_config = ConfigDict(
        from_attributes=True,
    )

    current_stage: str = Field(
        ...,
        description="Current ingestion pipeline stage.",
        examples=[
            "fetching",
            "filtering",
            "parsing",
            "chunking",
            "embedding",
            "graph_building",
            "completed",
        ],
    )

    total_files: int = Field(
        default=0,
        ge=0,
        description="Total number of files selected for ingestion.",
    )

    processed_files: int = Field(
        default=0,
        ge=0,
        description="Number of files successfully processed.",
    )

    failed_files: int = Field(
        default=0,
        ge=0,
        description="Number of files that failed processing.",
    )

    total_chunks: int = Field(
        default=0,
        ge=0,
        description="Total number of code chunks expected.",
    )

    processed_chunks: int = Field(
        default=0,
        ge=0,
        description="Number of chunks processed.",
    )

    total_embeddings: int = Field(
        default=0,
        ge=0,
        description="Total embeddings expected.",
    )

    processed_embeddings: int = Field(
        default=0,
        ge=0,
        description="Number of embeddings generated.",
    )

    percentage: float = Field(
        default=0.0,
        ge=0.0,
        le=100.0,
        description="Overall ingestion progress percentage.",
    )


# ============================================================
# Ingestion Status
# ============================================================

class IngestionStatusResponse(BaseModel):
    """
    Complete ingestion status.
    """

    model_config = ConfigDict(
        from_attributes=True,
    )

    job_id: UUID = Field(
        ...,
        description="Unique ingestion job ID.",
    )

    repository_id: int = Field(
        ...,
        description="RepoRAG repository ID.",
    )

    status: str = Field(
        ...,
        description="Current ingestion status.",
        examples=[
            "queued",
            "processing",
            "completed",
            "failed",
            "cancelled",
        ],
    )

    stage: str = Field(
        ...,
        description="Current pipeline stage.",
    )

    progress: IngestionProgress = Field(
        ...,
        description="Detailed ingestion progress.",
    )

    error: str | None = Field(
        default=None,
        description="Error message if ingestion failed.",
    )

    started_at: datetime | None = Field(
        default=None,
        description="UTC timestamp when ingestion started.",
    )

    completed_at: datetime | None = Field(
        default=None,
        description="UTC timestamp when ingestion completed.",
    )

    created_at: datetime = Field(
        ...,
        description="UTC timestamp when the ingestion job was created.",
    )


# ============================================================
# File Processing Result
# ============================================================

class FileProcessingResult(BaseModel):
    """
    Result for processing a single repository file.
    """

    model_config = ConfigDict(
        from_attributes=True,
    )

    file_id: UUID = Field(
        ...,
        description="RepoRAG repository file ID.",
    )

    path: str = Field(
        ...,
        description="Repository-relative file path.",
    )

    status: str = Field(
        ...,
        description="File processing status.",
        examples=["processed", "skipped", "failed"],
    )

    chunks_created: int = Field(
        default=0,
        ge=0,
        description="Number of code chunks created from the file.",
    )

    symbols_found: int = Field(
        default=0,
        ge=0,
        description="Number of symbols discovered in the file.",
    )

    dependencies_found: int = Field(
        default=0,
        ge=0,
        description="Number of dependencies discovered in the file.",
    )

    error: str | None = Field(
        default=None,
        description="Error message if file processing failed.",
    )


# ============================================================
# Ingestion Summary
# ============================================================

class IngestionSummary(BaseModel):
    """
    Final ingestion summary.
    """

    model_config = ConfigDict(
        from_attributes=True,
    )

    repository_id: int = Field(
        ...,
        description="RepoRAG repository ID.",
    )

    status: str = Field(
        ...,
        description="Final ingestion status.",
        examples=["completed", "completed_with_errors", "failed"],
    )

    files_processed: int = Field(
        default=0,
        ge=0,
        description="Number of files successfully processed.",
    )

    files_failed: int = Field(
        default=0,
        ge=0,
        description="Number of files that failed.",
    )

    chunks_created: int = Field(
        default=0,
        ge=0,
        description="Total number of code chunks created.",
    )

    embeddings_created: int = Field(
        default=0,
        ge=0,
        description="Total number of embeddings created.",
    )

    symbols_created: int = Field(
        default=0,
        ge=0,
        description="Total number of symbols created.",
    )

    dependencies_created: int = Field(
        default=0,
        ge=0,
        description="Total number of dependency relationships created.",
    )

    duration_seconds: float = Field(
        default=0.0,
        ge=0.0,
        description="Total ingestion duration in seconds.",
    )

    metadata: dict[str, Any] | None = Field(
        default=None,
        description="Additional ingestion metadata.",
    )