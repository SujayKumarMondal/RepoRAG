"""
Repository analysis API routes.
"""

from datetime import datetime, timezone
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException, status, Depends, Path
from sqlalchemy import func, select
from app.services.queue import enqueue_job
from app.core.security import get_current_user

from app.core.database import AsyncSessionLocal
from app.models.analysis import Analysis
from app.models.code_chunk import CodeChunk
from app.models.dependency import Dependency
from app.models.repository import Repository
from app.models.repository_file import RepositoryFile
from app.models.symbol import Symbol

from typing import Any
router = APIRouter()


# ============================================================
# Start analysis
# ============================================================

@router.post("/analysis/{repository_id}", status_code=status.HTTP_202_ACCEPTED)
async def start_analysis(repository_id: int = Path(..., description="GitHub repository numeric id"), current_user: dict[str, Any] = Depends(get_current_user)):
    """Queue repository analysis to be processed by background workers."""

    async with AsyncSessionLocal() as db:
        repo = (await db.execute(select(Repository).where(Repository.github_repo_id == repository_id))).scalar_one_or_none()
        if repo is None:
            raise HTTPException(status_code=404, detail="Repository not found.")
        if str(repo.owner_id) != str(current_user.get("sub")):
            raise HTTPException(status_code=403, detail="This repository is not owned by the current user.")

        analysis = Analysis(
            repository_id=repo.id,
            analysis_type="repository_health",
            status="queued",
            started_at=None,
        )
        db.add(analysis)
        await db.commit()
        await db.refresh(analysis)

    # Enqueue analysis job in Redis
    meta = {
        "job_type": "analysis",
        "repository_id": str(repository_id),
    }

    await enqueue_job(str(analysis.id), meta)

    return {"analysis_id": str(analysis.id), "repository_id": str(repository_id), "status": "queued"}


# ============================================================
# Get analysis
# ============================================================

@router.get("/analysis/{repository_id}")
async def get_analysis(repository_id: int = Path(..., description="GitHub repository numeric id")):
    """Return the latest analysis for a repository."""

    async with AsyncSessionLocal() as db:
        # Resolve repository by GitHub numeric id and use internal UUID
        repo = (await db.execute(select(Repository).where(Repository.github_repo_id == repository_id))).scalar_one_or_none()
        if repo is None:
            raise HTTPException(status_code=404, detail="Repository not found.")

        analysis = (await db.execute(
            select(Analysis)
            .where(Analysis.repository_id == repo.id)
            .order_by(Analysis.created_at.desc())
        )).scalars().first()

        if analysis is None:
            return {"repository_id": str(repository_id), "status": "not_started", "analysis": None}

        return {
            "repository_id": str(repository_id),
            "status": analysis.status,
            "analysis": {
                "id": str(analysis.id),
                "type": analysis.analysis_type,
                "summary": analysis.summary,
                "result": analysis.result,
                "findings_count": analysis.findings_count,
                "started_at": analysis.started_at,
                "completed_at": analysis.completed_at,
            },
        }


# ============================================================
# Analysis findings
# ============================================================

@router.get("/analysis/{repository_id}/findings")
async def get_analysis_findings(repository_id: int = Path(..., description="GitHub repository numeric id")):
    """Return detected findings."""

    async with AsyncSessionLocal() as db:
        repo = (await db.execute(select(Repository).where(Repository.github_repo_id == repository_id))).scalar_one_or_none()
        if repo is None:
            raise HTTPException(status_code=404, detail="Repository not found.")

        analysis = (await db.execute(
            select(Analysis)
            .where(Analysis.repository_id == repo.id)
            .order_by(Analysis.created_at.desc())
        )).scalars().first()

        findings = []
        if analysis and analysis.result:
            findings = [{"category": "summary", "message": analysis.summary, "severity": "info"}]

        return {"repository_id": str(repository_id), "count": len(findings), "findings": findings}


# ============================================================
# Repository statistics
# ============================================================

@router.get("/analysis/{repository_id}/statistics")
async def get_repository_statistics(repository_id: int = Path(..., description="GitHub repository numeric id")):
    """Return repository statistics."""

    async with AsyncSessionLocal() as db:
        repo = (await db.execute(select(Repository).where(Repository.github_repo_id == repository_id))).scalar_one_or_none()
        if repo is None:
            raise HTTPException(status_code=404, detail="Repository not found.")

        file_count = (await db.execute(select(func.count()).select_from(RepositoryFile).where(RepositoryFile.repository_id == repo.id))).scalar_one()
        chunk_count = (await db.execute(select(func.count()).select_from(CodeChunk).join(RepositoryFile, RepositoryFile.id == CodeChunk.file_id).where(RepositoryFile.repository_id == repo.id))).scalar_one()
        symbol_count = (await db.execute(select(func.count()).select_from(Symbol).join(RepositoryFile, RepositoryFile.id == Symbol.file_id).where(RepositoryFile.repository_id == repo.id))).scalar_one()
        dependency_count = (await db.execute(select(func.count()).select_from(Dependency).where(Dependency.repository_id == repo.id))).scalar_one()
        languages = await db.execute(
            select(RepositoryFile.language, func.count(RepositoryFile.language))
            .where(RepositoryFile.repository_id == repo.id)
            .group_by(RepositoryFile.language)
        )

        return {
            "repository_id": str(repository_id),
            "files": int(file_count or 0),
            "code_chunks": int(chunk_count or 0),
            "symbols": int(symbol_count or 0),
            "dependencies": int(dependency_count or 0),
            "languages": {key: int(value) for key, value in languages.all() if key is not None},
        }