"""
Background queue worker that consumes ingestion jobs from Redis and runs them.

Run with: python -m app.workers.queue_worker
"""
import asyncio
import logging
from uuid import UUID
from sqlalchemy import select

from app.services.queue import dequeue_job, get_job_meta, delete_job_meta
from app.core.database import AsyncSessionLocal
from app.models.ingestion_job import IngestionJob
from app.api.v1.ingestion import _run_ingestion
from app.services.analysis.service import AnalysisService
from app.models.analysis import Analysis
from app.models.repository import Repository
from app.models.user import User

logger = logging.getLogger(__name__)


async def worker_loop():
    while True:
        try:
            job_id_str, meta = await dequeue_job(timeout=5)
            if not job_id_str:
                await asyncio.sleep(1)
                continue

            logger.info("Dequeued job %s", job_id_str)

            # Load job from DB
            async with AsyncSessionLocal() as db:
                job = (await db.execute(
                    select(IngestionJob).where(IngestionJob.id == UUID(job_id_str))
                )).scalar_one_or_none()

            # If job not found, skip
            if job is None:
                logger.warning("Job %s not found in DB, skipping", job_id_str)
                await delete_job_meta(job_id_str)
                continue

            # Read metadata from Redis only for routing.
            if not meta:
                meta = await get_job_meta(job_id_str)

            # Decide job type from Redis metadata (minimal)
            job_type = (meta or {}).get("job_type")

            # Read access token and other settings from the DB job row or repository owner
            job_meta = job.job_metadata or {}
            branch = job_meta.get("branch")
            force = job_meta.get("force", False)
            include_tests = job_meta.get("include_tests", True)
            include_docs = job_meta.get("include_documentation", True)

            # Resolve access token from repository owner (preferred)
            access_token = None
            try:
                async with AsyncSessionLocal() as db2:
                    repo = (await db2.execute(select(Repository).where(Repository.github_repo_id == job.repository_id))).scalar_one_or_none()
                    if repo:
                        user = (await db2.execute(select(User).where(User.id == repo.owner_id))).scalar_one_or_none()
                        if user:
                            access_token = user.github_access_token
            except Exception:
                access_token = None

            if job_type == "analysis":
                try:
                    service = AnalysisService(str(job.repository_id))
                    analysis = await service.run()
                    logger.info("Analysis completed for repo=%s analysis_id=%s", job.repository_id, analysis.id)
                except Exception:
                    logger.exception("Failed to run analysis for job %s", job_id_str)
            else:
                # Run ingestion using the shared _run_ingestion helper
                try:
                    await _run_ingestion(
                        repository_id=job.repository_id,
                        branch=branch,
                        force=force,
                        include_tests=include_tests,
                        include_documentation=include_docs,
                        access_token=access_token,
                        job_id=UUID(job_id_str),
                    )
                except Exception:
                    logger.exception("Failed to process job %s", job_id_str)

            # Cleanup metadata
            await delete_job_meta(job_id_str)

        except asyncio.CancelledError:
            break
        except Exception:
            logger.exception("Queue worker encountered an error")
            await asyncio.sleep(2)


if __name__ == "__main__":
    import uvloop
    uvloop.install()
    logging.basicConfig(level=logging.INFO)

    try:
        asyncio.run(worker_loop())
    except KeyboardInterrupt:
        pass
