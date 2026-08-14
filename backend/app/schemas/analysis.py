"""
RepoRAG codebase analysis API schemas.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


# ============================================================
# Analysis Request
# ============================================================

class AnalysisRequest(BaseModel):
    """
    Request to analyze a repository.
    """

    repository_id: int

    analysis_type: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description=(
            "Type of analysis to perform, "
            "for example architecture, security, "
            "performance or code_quality"
        ),
    )

    commit_sha: str | None = Field(
        default=None,
        max_length=100,
    )

    force: bool = Field(
        default=False,
        description="Force a fresh analysis",
    )


# ============================================================
# Finding
# ============================================================

class AnalysisFinding(BaseModel):
    """
    Individual finding discovered during analysis.
    """

    severity: str = Field(
        ...,
        description="critical, high, medium, low or info",
    )

    category: str

    title: str

    description: str

    file_path: str | None = None

    start_line: int | None = Field(
        default=None,
        ge=1,
    )

    end_line: int | None = Field(
        default=None,
        ge=1,
    )

    recommendation: str | None = None

    evidence: str | None = None

    metadata: dict[str, Any] | None = None


# ============================================================
# Analysis Result
# ============================================================

class AnalysisResult(BaseModel):
    """
    Structured result of an AI/codebase analysis.
    """

    summary: str | None = None

    score: float | None = Field(
        default=None,
        ge=0.0,
        le=100.0,
    )

    findings: list[AnalysisFinding] = Field(
        default_factory=list,
    )

    metrics: dict[str, Any] = Field(
        default_factory=dict,
    )

    recommendations: list[str] = Field(
        default_factory=list,
    )


# ============================================================
# Analysis Response
# ============================================================

class AnalysisResponse(BaseModel):
    """
    Analysis API response.
    """

    id: UUID

    repository_id: int

    analysis_type: str

    status: str

    commit_sha: str | None = None

    summary: str | None = None

    result: AnalysisResult | None = None

    findings_count: int = Field(
        default=0,
        ge=0,
    )

    error_message: str | None = None

    started_at: datetime | None = None

    completed_at: datetime | None = None

    created_at: datetime

    updated_at: datetime


# ============================================================
# Analysis List Response
# ============================================================

class AnalysisListResponse(BaseModel):
    """
    List of analyses for a repository.
    """

    items: list[AnalysisResponse]

    total: int = Field(
        default=0,
        ge=0,
    )