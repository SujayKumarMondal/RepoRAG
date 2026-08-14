"""
Repository ingestion worker.

Responsible for taking a GitHub repository through the initial
source-code ingestion and parsing pipeline.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from app.core.database import AsyncSessionLocal
from app.services.github.client import GitHubClient
from app.services.ingestion.repository import (
    RepositoryIngestionService,
)
from app.services.ingestion.pipeline import (
    IngestionPipeline,
)

logger = logging.getLogger(__name__)


@dataclass
class IngestionJob:
    """
    Represents an ingestion job.
    """

    repository_id: str
    owner: str
    repository_name: str
    branch: str | None = None


class IngestionWorker:
    """
    Background worker responsible for repository ingestion.

    Pipeline:

        GitHub
          ↓
        Repository metadata
          ↓
        File tree
          ↓
        File filtering
          ↓
        File contents
          ↓
        AST parsing
          ↓
        Symbols / imports / routes
          ↓
        Code chunks
    """

    def __init__(
        self,
        github_token: str,
    ) -> None:

        self.github_token = github_token

    async def process(
        self,
        job: IngestionJob,
    ) -> dict[str, Any]:

        started_at = datetime.now(
            timezone.utc
        )

        logger.info(
            "Starting ingestion for repository=%s",
            job.repository_id,
        )

        github_client = GitHubClient()

        ingestion_service = (
            RepositoryIngestionService(
                github_client=github_client,
                access_token=self.github_token,
            )
        )

        pipeline = IngestionPipeline()

        try:

            repository_data = (
                await ingestion_service.fetch_repository(
                    owner=job.owner,
                    repo=job.repository_name,
                    branch=job.branch,
                )
            )

            branch = repository_data["branch"]

            logger.info(
                "Repository branch resolved: %s",
                branch,
            )

            files = (
                await ingestion_service.fetch_files(
                    owner=job.owner,
                    repo=job.repository_name,
                    branch=branch,
                )
            )

            logger.info(
                "Found %d supported files",
                len(files),
            )

            files_with_content = (
                await ingestion_service
                .fetch_file_contents(
                    owner=job.owner,
                    repo=job.repository_name,
                    branch=branch,
                    files=files,
                )
            )

            logger.info(
                "Downloaded %d files",
                len(files_with_content),
            )

            processed_files = (
                await pipeline.process_repository(
                    files_with_content
                )
            )

            total_chunks = sum(
                len(file.chunks)
                for file in processed_files
            )

            total_symbols = sum(
                len(file.symbols)
                for file in processed_files
            )

            total_imports = sum(
                len(file.imports)
                for file in processed_files
            )

            total_routes = sum(
                len(file.routes)
                for file in processed_files
            )

            result = {
                "repository_id": job.repository_id,
                "branch": branch,
                "files": processed_files,
                "file_count": len(processed_files),
                "chunk_count": total_chunks,
                "symbol_count": total_symbols,
                "import_count": total_imports,
                "route_count": total_routes,
                "started_at": started_at.isoformat(),
                "completed_at": datetime.now(
                    timezone.utc
                ).isoformat(),
                "status": "completed",
            }

            logger.info(
                "Ingestion completed for repository=%s "
                "files=%d chunks=%d symbols=%d",
                job.repository_id,
                len(processed_files),
                total_chunks,
                total_symbols,
            )

            return result

        except Exception:

            logger.exception(
                "Repository ingestion failed: %s",
                job.repository_id,
            )

            raise

        finally:

            await github_client.close()


async def run_ingestion_job(
    job: IngestionJob,
    github_token: str,
) -> dict[str, Any]:
    """
    Convenience function for executing an ingestion job.
    """

    worker = IngestionWorker(
        github_token=github_token
    )

    return await worker.process(job)