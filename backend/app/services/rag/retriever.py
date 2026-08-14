"""
Vector/code retrieval service.
"""

from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class RAGRetriever:
    """
    Retrieves semantically relevant code chunks.

    PostgreSQL + pgvector is used for vector similarity.
    """

    def __init__(
        self,
        db: AsyncSession,
    ) -> None:

        self.db = db

    async def vector_search(
        self,
        repository_id: str,
        embedding: list[float],
        top_k: int = 10,
    ) -> list[dict[str, Any]]:

        query = text(
            """
            SELECT
                cc.id AS chunk_id,
                rf.id AS file_id,
                rf.path AS file_path,
                cc.content,
                cc.start_line,
                cc.end_line,
                cc.chunk_type,
                cc.symbol_name,
                cc.symbol_type,
                1 - (
                    e.vector <=> CAST(
                        :embedding AS vector
                    )
                ) AS score
            FROM embeddings e
            JOIN code_chunks cc
                ON cc.id = e.chunk_id
            JOIN repository_files rf
                ON rf.id = cc.file_id
            WHERE rf.repository_id = :repository_id
            ORDER BY
                e.vector <=> CAST(
                    :embedding AS vector
                )
            LIMIT :top_k
            """
        )

        result = await self.db.execute(
            query,
            {
                "embedding": str(embedding),
                "repository_id": repository_id,
                "top_k": top_k,
            },
        )

        return [
            dict(row)
            for row in result.mappings().all()
        ]

    async def keyword_search(
        self,
        repository_id: str,
        query_text: str,
        top_k: int = 10,
    ) -> list[dict[str, Any]]:

        query = text(
            """
            SELECT
                cc.id AS chunk_id,
                rf.id AS file_id,
                rf.path AS file_path,
                cc.content,
                cc.start_line,
                cc.end_line,
                cc.chunk_type,
                cc.symbol_name,
                cc.symbol_type
            FROM code_chunks cc
            JOIN repository_files rf
                ON rf.id = cc.file_id
            WHERE
                rf.repository_id = :repository_id
                AND cc.content ILIKE :query
            LIMIT :top_k
            """
        )

        result = await self.db.execute(
            query,
            {
                "repository_id": repository_id,
                "query": f"%{query_text}%",
                "top_k": top_k,
            },
        )

        return [
            dict(row)
            for row in result.mappings().all()
        ]