"""
Embedding generation worker.

Responsible for converting repository code chunks into vector
embeddings and storing them for semantic retrieval.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.embeddings.generator import (
    EmbeddingGenerator,
)

logger = logging.getLogger(__name__)


@dataclass
class EmbeddingJob:
    """
    Represents an embedding generation job.
    """

    repository_id: str
    chunk_ids: list[str]


class EmbeddingWorker:
    """
    Generates embeddings for repository code chunks.

    Pipeline:

        Code Chunk
            ↓
        EmbeddingGenerator
            ↓
        Embedding Provider
            ↓
        pgvector
    """

    def __init__(
        self,
        embedding_generator: EmbeddingGenerator,
    ) -> None:

        self.embedding_generator = (
            embedding_generator
        )

    async def process(
        self,
        db: AsyncSession,
        job: EmbeddingJob,
    ) -> dict[str, Any]:

        started_at = datetime.now(
            timezone.utc
        )

        logger.info(
            "Starting embedding job repository=%s chunks=%d",
            job.repository_id,
            len(job.chunk_ids),
        )

        if not job.chunk_ids:

            return {
                "repository_id": job.repository_id,
                "processed": 0,
                "status": "completed",
                "started_at": started_at.isoformat(),
                "completed_at": datetime.now(
                    timezone.utc
                ).isoformat(),
            }

        try:

            query = text(
                """
                SELECT
                    id,
                    content
                FROM code_chunks
                WHERE id = ANY(
                    CAST(:chunk_ids AS uuid[])
                )
                """
            )

            result = await db.execute(
                query,
                {
                    "chunk_ids": job.chunk_ids
                },
            )

            chunks = result.mappings().all()

            processed = 0

            for chunk in chunks:

                chunk_id = str(
                    chunk["id"]
                )

                content = chunk["content"]

                if not content:
                    continue

                embedding = (
                    await self.embedding_generator
                    .generate(content)
                )

                await self._save_embedding(
                    db=db,
                    chunk_id=chunk_id,
                    embedding=embedding,
                )

                processed += 1

                logger.debug(
                    "Generated embedding chunk=%s",
                    chunk_id,
                )

            await db.commit()

            completed_at = datetime.now(
                timezone.utc
            )

            logger.info(
                "Embedding job completed repository=%s "
                "processed=%d",
                job.repository_id,
                processed,
            )

            return {
                "repository_id": job.repository_id,
                "processed": processed,
                "requested": len(
                    job.chunk_ids
                ),
                "status": "completed",
                "started_at": started_at.isoformat(),
                "completed_at": completed_at.isoformat(),
            }

        except Exception:

            await db.rollback()

            logger.exception(
                "Embedding job failed repository=%s",
                job.repository_id,
            )

            raise

    async def _save_embedding(
        self,
        db: AsyncSession,
        chunk_id: str,
        embedding: list[float],
    ) -> None:

        vector = str(embedding)

        query = text(
            """
            INSERT INTO embeddings (
                chunk_id,
                vector
            )
            VALUES (
                :chunk_id,
                CAST(:vector AS vector)
            )
            ON CONFLICT (chunk_id)
            DO UPDATE SET
                vector = EXCLUDED.vector
            """
        )

        await db.execute(
            query,
            {
                "chunk_id": chunk_id,
                "vector": vector,
            },
        )


async def run_embedding_job(
    db: AsyncSession,
    job: EmbeddingJob,
    embedding_generator: EmbeddingGenerator,
) -> dict[str, Any]:

    worker = EmbeddingWorker(
        embedding_generator=embedding_generator
    )

    return await worker.process(
        db=db,
        job=job,
    )