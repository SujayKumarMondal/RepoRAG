"""
Repository ingestion API routes.

Handles:
    - Starting repository ingestion
    - Checking ingestion status
    - Cancelling ingestion
    - Re-ingesting repositories
"""

import hashlib
from datetime import datetime, timezone
from typing import Any
import traceback
from uuid import UUID, uuid4
import asyncio

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi import Path
from sqlalchemy import select, delete

from app.core.database import AsyncSessionLocal
from app.core.security import get_current_user
from app.models.code_chunk import CodeChunk
from app.models.dependency import Dependency
from app.models.embedding import Embedding
from app.models.ingestion_job import IngestionJob
from app.models.repository import Repository
from app.models.repository_file import RepositoryFile
from app.models.symbol import Symbol
from app.schemas.ingestion import IngestionRequest, IngestionResponse
from app.services.embeddings.generator import EmbeddingGenerator
from app.services.embeddings.provider import DeterministicEmbeddingProvider
from app.services.github.client import GitHubClient
from app.services.github.files import GitHubFileService
from app.services.ingestion.pipeline import IngestionPipeline
from app.services.queue import enqueue_job, get_job_meta, set_job_meta

router = APIRouter()


async def _get_repo_or_404(db, repository_id: int) -> Repository:
    repo = (await db.execute(select(Repository).where(Repository.github_repo_id == repository_id))).scalar_one_or_none()
    if repo is None:
        raise HTTPException(status_code=404, detail="Repository not found.")
    return repo


async def _run_ingestion(repository_id: int, branch: str | None, force: bool, include_tests: bool, include_documentation: bool, access_token: str, job_id: UUID | None = None) -> IngestionJob:
        async with AsyncSessionLocal() as db:
            repo = await _get_repo_or_404(db, repository_id)

            if job_id is None:
                job = IngestionJob(
                    repository_id=repo.id,
                    status="processing",
                    stage="fetching",
                    progress=5,
                    files_total=0,
                    files_processed=0,
                    job_metadata={
                        "branch": branch or repo.default_branch,
                        "force": force,
                        "include_tests": include_tests,
                        "include_documentation": include_documentation,
                    },
                    started_at=datetime.now(timezone.utc),
                )
                db.add(job)
                await db.commit()
                await db.refresh(job)
            else:
                job = (await db.execute(select(IngestionJob).where(IngestionJob.id == job_id))).scalar_one_or_none()
                if job is None:
                    # Create a new job if provided id does not exist
                    job = IngestionJob(
                        repository_id=repo.id,
                        status="processing",
                        stage="fetching",
                        progress=5,
                        files_total=0,
                        files_processed=0,
                        job_metadata={
                            "branch": branch or repo.default_branch,
                            "force": force,
                            "include_tests": include_tests,
                            "include_documentation": include_documentation,
                        },
                        started_at=datetime.now(timezone.utc),
                    )
                    db.add(job)
                    await db.commit()
                    await db.refresh(job)
                else:
                    job.status = "processing"
                    job.stage = "fetching"
                    job.progress = 5
                    job.started_at = datetime.now(timezone.utc)
                    job.job_metadata = job.job_metadata or {}
                    job.job_metadata.update({
                        "branch": branch or repo.default_branch,
                        "force": force,
                        "include_tests": include_tests,
                        "include_documentation": include_documentation,
                    })
                    await db.commit()

        current_branch = branch or repo.default_branch
        github_client = GitHubClient()
        file_service = GitHubFileService(github_client, access_token)

        # Fetch repository tree (single request)
        tree = await file_service.get_tree(
            repo.full_name.split("/", 1)[0],
            repo.full_name.split("/", 1)[1],
            current_branch,
        )

        # Build list of candidate files
        supported = [
            {"path": item.get("path", ""), "sha": item.get("sha")}
            for item in tree
            if item.get("type") == "blob"
            and item.get("path")
            and not (item.get("path").startswith(".") and item.get("path") not in {".env.example"})
        ]

        # Clear existing repository files and dependencies in a single transaction
        await db.execute(delete(RepositoryFile).where(RepositoryFile.repository_id == repo.id))
        await db.execute(delete(Dependency).where(Dependency.repository_id == repo.id))
        await db.commit()

        # --------------------------------------------------
        # Concurrently fetch file contents with bounded concurrency
        # --------------------------------------------------
        sem = asyncio.Semaphore(10)

        async def _fetch(path, sha):
            async with sem:
                return {"path": path, "sha": sha, "content": await file_service.get_file_content(repo.full_name.split("/", 1)[0], repo.full_name.split("/", 1)[1], path, current_branch)}

        fetch_tasks = [
            _fetch(item["path"], item.get("sha")) for item in supported
        ]

        files_with_content = []
        for chunk in (await asyncio.gather(*fetch_tasks)):
            if chunk.get("content"):
                files_with_content.append(chunk)

        # Bulk-create RepositoryFile rows (no content stored in DB)
        for file_meta in files_with_content:
            path = file_meta["path"]
            file_content = file_meta["content"]
            file_record = RepositoryFile(
                repository_id=repo.id,
                path=path,
                filename=path.rsplit("/", 1)[-1],
                extension=("." + path.rsplit(".", 1)[-1]) if "." in path else None,
                language=path.rsplit(".", 1)[-1] if "." in path else None,
                size_bytes=len(file_content.encode("utf-8")),
                blob_sha=file_meta.get("sha"),
                commit_sha=current_branch,
                is_binary=False,
                is_ignored=False,
                processing_status="pending",
            )
            db.add(file_record)

        await db.commit()

        file_rows = (await db.execute(select(RepositoryFile).where(RepositoryFile.repository_id == repo.id))).scalars().all()
        job.files_total = len(file_rows)
        job.progress = 20
        job.stage = "filtering"
        await db.commit()

        pipeline = IngestionPipeline()
        embedding_generator = EmbeddingGenerator(DeterministicEmbeddingProvider())
        # Prepare for concurrent file processing. We'll process files in
        # parallel using a worker that uses its own DB session to avoid
        # session concurrency issues. The main session updates job progress
        # as workers finish.
        seen_edges: set[tuple[str, str, str, str]] = set()
        path_to_content = {f["path"]: f["content"] for f in files_with_content}

        concurrency = 6
        sem_proc = asyncio.Semaphore(concurrency)

        async def process_one(file_row_local):
            async with sem_proc:
                async with AsyncSessionLocal() as db_local:
                    # Re-run the pipeline parsing with content
                    content_local = path_to_content.get(file_row_local.path, "")
                    if not pipeline.file_filter.should_process(file_row_local.path):
                        # mark skipped in the main DB via a quick update
                        await db_local.execute(
                            select(RepositoryFile).where(RepositoryFile.id == file_row_local.id)
                        )
                        return {"file_id": file_row_local.id, "status": "skipped"}

                    processed_local = await pipeline.process_file(file_row_local.path, content_local)
                    if not processed_local.chunks:
                        return {"file_id": file_row_local.id, "status": "skipped"}

                    # Insert symbols
                    for symbol in processed_local.symbols:
                        db_local.add(
                            Symbol(
                                file_id=file_row_local.id,
                                name=symbol.get("name", ""),
                                qualified_name=symbol.get("qualified_name") or symbol.get("name"),
                                symbol_type=symbol.get("symbol_type", "unknown"),
                                start_line=symbol.get("start_line", 1),
                                end_line=symbol.get("end_line", 1),
                                start_column=symbol.get("start_column"),
                                end_column=symbol.get("end_column"),
                                signature=symbol.get("signature"),
                                docstring=symbol.get("docstring"),
                                extra_metadata=symbol,
                            )
                        )

                    # Create chunks and flush once
                    db_chunks_local = []
                    chunk_texts_local = []
                    for idx, chunk in enumerate(processed_local.chunks, start=1):
                        ch_hash = hashlib.sha256((file_row_local.path + "::" + str(idx) + "::" + chunk["content"]).encode("utf-8")).hexdigest()
                        dbch = CodeChunk(
                            file_id=file_row_local.id,
                            chunk_index=idx,
                            content=chunk["content"],
                            content_hash=ch_hash,
                            start_line=chunk.get("start_line"),
                            end_line=chunk.get("end_line"),
                            chunk_type=chunk.get("chunk_type"),
                            symbol_name=chunk.get("symbol_name"),
                            symbol_type=chunk.get("symbol_type"),
                            token_count=max(1, len(chunk["content"].split())),
                            extra_metadata={"language": chunk.get("language"), "path": file_row_local.path},
                        )
                        db_local.add(dbch)
                        db_chunks_local.append(dbch)
                        chunk_texts_local.append(chunk["content"])

                    await db_local.flush()

                    # Generate embeddings for this file's chunks
                    try:
                        vectors_local = await asyncio.gather(*(embedding_generator.generate(t) for t in chunk_texts_local))
                    except Exception:
                        vectors_local = [await embedding_generator.generate(t) for t in chunk_texts_local]

                    for dbch, vec in zip(db_chunks_local, vectors_local):
                        db_local.add(Embedding(chunk_id=dbch.id, vector=vec, provider="local", model="deterministic-embeddings"))

                    # Dependencies resolution
                    for dep in processed_local.imports:
                        if not dep.get("module"):
                            continue
                        res = await db_local.execute(
                            select(RepositoryFile).where(
                                RepositoryFile.repository_id == repo.id,
                                RepositoryFile.path.like(f"%{dep.get('module', '').replace('.', '/')}%"),
                            )
                        )
                        target = res.scalars().first()
                        if target is not None:
                            key = (str(repo.id), str(file_row_local.id), str(target.id), "import")
                            if key in seen_edges:
                                continue
                            seen_edges.add(key)
                            db_local.add(Dependency(
                                repository_id=repo.id,
                                source_file_id=file_row_local.id,
                                target_file_id=target.id,
                                dependency_type="import",
                                source_symbol=None,
                                target_symbol=dep.get("module"),
                            ))

                    await db_local.commit()
                    return {"file_id": file_row_local.id, "status": "processed"}

        # Launch tasks for all files and update job progress as they finish
        tasks = [asyncio.create_task(process_one(fr)) for fr in file_rows]
        completed = 0
        for coro in asyncio.as_completed(tasks):
            result = await coro
            completed += 1
            job.files_processed = completed
            job.progress = min(95, 20 + int((completed / max(len(file_rows), 1)) * 70))
            job.stage = "parsing"
            await db.commit()

        repo.ingestion_status = "completed"
        repo.ingestion_error = None
        repo.last_ingested_commit = current_branch
        job.status = "completed"
        job.stage = "completed"
        job.progress = 100
        job.completed_at = datetime.now(timezone.utc)
        await db.commit()

        return job


# ============================================================
# Start Ingestion
# ============================================================

@router.post(
    "/ingestion",
    response_model=IngestionResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def start_ingestion(
    request: IngestionRequest,
    current_user: dict[str, Any] = Depends(get_current_user),
):
    """Start repository ingestion and process it inline for local compatibility."""

    try:
        async with AsyncSessionLocal() as db:
            repo = await _get_repo_or_404(db, request.repository_id)
            if str(repo.owner_id) != str(current_user.get("sub")):
                raise HTTPException(status_code=403, detail="This repository is not owned by the current user.")

        access_token = current_user.get("github_access_token")
        # If token isn't present in the JWT payload, fall back to persisted token on the User record.
        if not access_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="GitHub access token not found. Please re-authenticate.",
            )

        job = await _run_ingestion(
            repository_id=request.repository_id,
            branch=request.branch,
            force=request.force,
            include_tests=request.include_tests,
            include_documentation=request.include_documentation,
            access_token=access_token,
        )

        return IngestionResponse(
            job_id=job.id,
            repository_id=request.repository_id,
            status=job.status,
            message="Repository ingestion completed.",
            created_at=job.created_at,
        )

    except Exception as exc:
        tb = traceback.format_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unable to start ingestion: {exc}\n\nTraceback:\n{tb}",
        ) from exc


# ============================================================
# Get Ingestion Status
# ============================================================

@router.get("/ingestion/{job_id}")
async def get_ingestion_status(job_id: UUID, current_user: dict[str, Any] = Depends(get_current_user)):
    """Return the current ingestion status from the database."""

    async with AsyncSessionLocal() as db:
        job = (await db.execute(select(IngestionJob).where(IngestionJob.id == job_id))).scalar_one_or_none()
        if job is None:
            raise HTTPException(status_code=404, detail="Ingestion job not found.")

        # verify ownership
        repo = (await db.execute(select(Repository).where(Repository.github_repo_id == job.repository_id))).scalar_one_or_none()
        if repo is None or str(repo.owner_id) != str(current_user.get("sub")):
            raise HTTPException(status_code=403, detail="This ingestion job is not accessible.")

        return {
            "job_id": str(job.id),
            "repository_id": str(job.repository_id),
            "status": job.status,
            "stage": job.stage,
            "progress": job.progress,
            "files_processed": job.files_processed,
            "files_total": job.files_total,
            "error": job.error_message,
            "created_at": job.created_at,
            "started_at": job.started_at,
            "completed_at": job.completed_at,
        }


# ============================================================
# Cancel Ingestion
# ============================================================

@router.post("/ingestion/{job_id}/cancel")
async def cancel_ingestion(job_id: UUID, current_user: dict[str, Any] = Depends(get_current_user)):
    """Cancel an ingestion job."""

    async with AsyncSessionLocal() as db:
        job = (await db.execute(select(IngestionJob).where(IngestionJob.id == job_id))).scalar_one_or_none()
        if job is None:
            raise HTTPException(status_code=404, detail="Ingestion job not found.")

        repo = (await db.execute(select(Repository).where(Repository.github_repo_id == job.repository_id))).scalar_one_or_none()
        if repo is None or str(repo.owner_id) != str(current_user.get("sub")):
            raise HTTPException(status_code=403, detail="This ingestion job is not accessible.")

        job.status = "cancelled"
        job.stage = "cancelled"
        job.error_message = "Ingestion cancelled by request."
        await db.commit()

    # remove job meta from redis if present
    try:
        await set_job_meta(str(job_id), {"cancelled": True})
    except Exception:
        pass

    return {"job_id": str(job_id), "status": "cancelled", "message": "Ingestion cancellation requested."}



@router.post("/ingestion/enqueue", status_code=status.HTTP_202_ACCEPTED)
async def enqueue_ingestion(request: IngestionRequest, current_user: dict[str, Any] = Depends(get_current_user)):
    """Enqueue a repository ingestion job to be processed by background workers."""

    access_token = current_user.get("github_access_token")
    if not access_token:
        # attempt to load from persisted User record
        async with AsyncSessionLocal() as db:
            from app.models.user import User as UserModel

            user = (await db.execute(select(UserModel).where(UserModel.id == current_user.get("sub")))).scalar_one_or_none()
            if user and getattr(user, "github_access_token", None):
                access_token = user.github_access_token

    if not access_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="GitHub access token not found. Please re-authenticate.")

    async with AsyncSessionLocal() as db:
        repo = await _get_repo_or_404(db, request.repository_id)
        if str(repo.owner_id) != str(current_user.get("sub")):
            raise HTTPException(status_code=403, detail="This repository is not owned by the current user.")

        job = IngestionJob(
            repository_id=repo.id,
            status="queued",
            stage="queued",
            progress=0,
            files_total=0,
            files_processed=0,
            job_metadata={
                "branch": request.branch or repo.default_branch,
                "force": request.force,
                "include_tests": request.include_tests,
                "include_documentation": request.include_documentation,
            },
        )
        db.add(job)
        await db.commit()
        await db.refresh(job)

    # Push to Redis queue with minimal metadata (worker will read token from DB)
    meta = {
        "job_type": "ingestion",
    }

    await enqueue_job(str(job.id), meta)

    return {"job_id": str(job.id), "repository_id": str(repo.id), "status": "queued", "created_at": job.created_at}


@router.get("/ingestion/jobs")
async def list_ingestion_jobs(current_user: dict[str, Any] = Depends(get_current_user)):
    async with AsyncSessionLocal() as db:
        user_id = current_user.get("sub")
        result = await db.execute(select(IngestionJob).join(Repository).where(Repository.owner_id == user_id).order_by(IngestionJob.created_at.desc()))
        jobs = result.scalars().all()
        return {"jobs": [{"id": str(j.id), "repository_id": str(j.repository_id), "status": j.status, "stage": j.stage, "progress": j.progress, "created_at": j.created_at} for j in jobs]}


# ============================================================
# Re-ingest Repository
# ============================================================

@router.post("/repositories/{repository_id}/reingest", status_code=status.HTTP_202_ACCEPTED)
async def reingest_repository(
    repository_id: int = Path(..., description="GitHub repository numeric id"),
    current_user: dict[str, Any] = Depends(get_current_user),
):
    """Re-ingest an existing repository."""

    try:
        async with AsyncSessionLocal() as db:
            repo = await _get_repo_or_404(db, repository_id)
            if str(repo.owner_id) != str(current_user.get("sub")):
                raise HTTPException(status_code=403, detail="This repository is not owned by the current user.")

        job = await _run_ingestion(
            repository_id=repository_id,
            branch=repo.default_branch,
            force=True,
            include_tests=True,
            include_documentation=True,
        ) if False else None

        existing = await _run_ingestion(
            repository_id=repository_id,
            branch=None,
            force=True,
            include_tests=True,
            include_documentation=True,
        )

        return {
            "repository_id": str(repository_id),
            "job_id": str(existing.id),
            "status": existing.status,
            "message": "Repository re-ingestion has been queued.",
            "created_at": existing.created_at,
        }

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unable to start repository re-ingestion: {exc}",
        ) from exc