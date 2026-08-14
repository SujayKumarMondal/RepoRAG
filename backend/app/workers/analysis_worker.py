"""
Repository analysis worker.

Responsible for higher-level repository analysis after ingestion
and embedding generation.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.graph.dependency_graph import (
    DependencyGraph,
    GraphEdge,
)

logger = logging.getLogger(__name__)


@dataclass
class AnalysisJob:
    """
    Represents a repository analysis job.
    """

    repository_id: str


class AnalysisWorker:
    """
    Performs structural analysis of a repository.

    Pipeline:

        Repository files
              ↓
        Symbols / imports
              ↓
        Dependency extraction
              ↓
        Dependency graph
              ↓
        Repository-level metrics
    """

    async def process(
        self,
        db: AsyncSession,
        job: AnalysisJob,
    ) -> dict[str, Any]:

        started_at = datetime.now(
            timezone.utc
        )

        logger.info(
            "Starting repository analysis=%s",
            job.repository_id,
        )

        graph = DependencyGraph()

        try:

            files = await self._load_files(
                db=db,
                repository_id=job.repository_id,
            )

            chunks = await self._load_chunks(
                db=db,
                repository_id=job.repository_id,
            )

            symbols = await self._load_symbols(
                db=db,
                repository_id=job.repository_id,
            )

            imports = await self._load_imports(
                db=db,
                repository_id=job.repository_id,
            )

            for item in imports:

                source = item.get(
                    "source_file"
                )

                target = item.get(
                    "module"
                )

                if not source or not target:
                    continue

                graph.add_edge(
                    source=source,
                    target=target,
                    dependency_type="import",
                )

            metrics = self._calculate_metrics(
                files=files,
                chunks=chunks,
                symbols=symbols,
                imports=imports,
                graph=graph,
            )

            await self._persist_graph(
                db=db,
                repository_id=job.repository_id,
                graph=graph,
            )

            await db.commit()

            result = {
                "repository_id": job.repository_id,
                "status": "completed",
                "metrics": metrics,
                "graph": graph.to_dict(),
                "started_at": started_at.isoformat(),
                "completed_at": datetime.now(
                    timezone.utc
                ).isoformat(),
            }

            logger.info(
                "Repository analysis completed=%s",
                job.repository_id,
            )

            return result

        except Exception:

            await db.rollback()

            logger.exception(
                "Repository analysis failed=%s",
                job.repository_id,
            )

            raise

    async def _load_files(
        self,
        db: AsyncSession,
        repository_id: str,
    ) -> list[dict[str, Any]]:

        query = text(
            """
            SELECT
                id,
                path
            FROM repository_files
            WHERE repository_id = :repository_id
            """
        )

        result = await db.execute(
            query,
            {
                "repository_id": repository_id
            },
        )

        return [
            dict(row)
            for row in result.mappings().all()
        ]

    async def _load_chunks(
        self,
        db: AsyncSession,
        repository_id: str,
    ) -> list[dict[str, Any]]:

        query = text(
            """
            SELECT
                cc.id,
                cc.file_id,
                cc.content,
                cc.start_line,
                cc.end_line
            FROM code_chunks cc
            JOIN repository_files rf
                ON rf.id = cc.file_id
            WHERE rf.repository_id = :repository_id
            """
        )

        result = await db.execute(
            query,
            {
                "repository_id": repository_id
            },
        )

        return [
            dict(row)
            for row in result.mappings().all()
        ]

    async def _load_symbols(
        self,
        db: AsyncSession,
        repository_id: str,
    ) -> list[dict[str, Any]]:

        query = text(
            """
            SELECT
                s.id,
                s.file_id,
                s.name,
                s.symbol_type
            FROM symbols s
            JOIN repository_files rf
                ON rf.id = s.file_id
            WHERE rf.repository_id = :repository_id
            """
        )

        result = await db.execute(
            query,
            {
                "repository_id": repository_id
            },
        )

        return [
            dict(row)
            for row in result.mappings().all()
        ]

    async def _load_imports(
        self,
        db: AsyncSession,
        repository_id: str,
    ) -> list[dict[str, Any]]:

        """
        Loads import information.

        This assumes imports are eventually persisted in the
        dependency table. The query can be adjusted to your
        final schema.
        """

        query = text(
            """
            SELECT
                d.id,
                source_file.path AS source_file,
                d.target AS module,
                d.dependency_type
            FROM dependencies d
            JOIN repository_files source_file
                ON source_file.id = d.source_file_id
            WHERE source_file.repository_id = :repository_id
            """
        )

        try:

            result = await db.execute(
                query,
                {
                    "repository_id": repository_id
                },
            )

            return [
                dict(row)
                for row in result.mappings().all()
            ]

        except Exception:

            # Dependency persistence may not exist yet
            # during initial development.

            logger.warning(
                "Dependency records unavailable "
                "for repository=%s",
                repository_id,
            )

            return []

    def _calculate_metrics(
        self,
        files: list[dict[str, Any]],
        chunks: list[dict[str, Any]],
        symbols: list[dict[str, Any]],
        imports: list[dict[str, Any]],
        graph: DependencyGraph,
    ) -> dict[str, Any]:

        languages: dict[str, int] = {}

        for file in files:

            path = file.get(
                "path",
                "",
            )

            extension = (
                path.rsplit(
                    ".",
                    1,
                )[-1].lower()
                if "." in path
                else "unknown"
            )

            languages[extension] = (
                languages.get(
                    extension,
                    0,
                )
                + 1
            )

        return {
            "file_count": len(files),
            "chunk_count": len(chunks),
            "symbol_count": len(symbols),
            "dependency_count": len(
                graph.edges
            ),
            "language_distribution": languages,
            "graph_node_count": len(
                graph.adjacency
            ),
            "graph_edge_count": len(
                graph.edges
            ),
        }

    async def _persist_graph(
        self,
        db: AsyncSession,
        repository_id: str,
        graph: DependencyGraph,
    ) -> None:

        """
        Persist dependency graph edges.

        This uses the dependency table defined by RepoRAG's
        architecture.

        Adjust column names if your final SQL schema differs.
        """

        if not graph.edges:
            return

        for edge in graph.edges:

            source_file_id = (
                await self._find_file_id(
                    db,
                    repository_id,
                    edge.source,
                )
            )

            target_file_id = (
                await self._find_file_id(
                    db,
                    repository_id,
                    edge.target,
                )
            )

            if not source_file_id:
                continue

            await db.execute(
                text(
                    """
                    INSERT INTO dependencies (
                        repository_id,
                        source_file_id,
                        target_file_id,
                        dependency_type,
                        target
                    )
                    VALUES (
                        :repository_id,
                        :source_file_id,
                        :target_file_id,
                        :dependency_type,
                        :target
                    )
                    """
                ),
                {
                    "repository_id": repository_id,
                    "source_file_id": (
                        source_file_id
                    ),
                    "target_file_id": (
                        target_file_id
                    ),
                    "dependency_type": (
                        edge.dependency_type
                    ),
                    "target": edge.target,
                },
            )

    async def _find_file_id(
        self,
        db: AsyncSession,
        repository_id: str,
        path: str,
    ) -> str | None:

        query = text(
            """
            SELECT id
            FROM repository_files
            WHERE
                repository_id = :repository_id
                AND path = :path
            LIMIT 1
            """
        )

        result = await db.execute(
            query,
            {
                "repository_id": repository_id,
                "path": path,
            },
        )

        row = result.mappings().first()

        if not row:
            return None

        return str(row["id"])


async def run_analysis_job(
    db: AsyncSession,
    job: AnalysisJob,
) -> dict[str, Any]:

    worker = AnalysisWorker()

    return await worker.process(
        db=db,
        job=job,
    )