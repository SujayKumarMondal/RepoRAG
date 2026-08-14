"""
RepoRAG RAG pipeline.
"""

import time
from typing import Any

from app.services.rag.context_builder import (
    ContextBuilder,
)


class RAGPipeline:
    """
    Complete retrieval pipeline:

    Query
      ↓
    Embedding
      ↓
    Vector Search
      ↓
    Keyword Search
      ↓
    Hybrid Merge
      ↓
    Reranking
      ↓
    Context Construction
    """

    def __init__(
        self,
        embedding_generator,
        retriever,
    ) -> None:

        self.embedding_generator = (
            embedding_generator
        )

        # Hybrid search and reranking logic inlined here to reduce
        # cross-file dependencies while preserving behavior.
        self.retriever = retriever

        self.context_builder = (
            ContextBuilder()
        )

    async def retrieve(
        self,
        repository_id: str,
        query: str,
        top_k: int = 8,
    ) -> dict[str, Any]:

        started = time.perf_counter()

        embedding = (
            await self.embedding_generator.generate(
                query
            )
        )

        # --- Hybrid retrieval ---
        vector_results = []

        if embedding:
            vector_results = (
                await self.retriever.vector_search(
                    repository_id=repository_id,
                    embedding=embedding,
                    top_k=top_k * 2,
                )
            )

        keyword_results = (
            await self.retriever.keyword_search(
                repository_id=repository_id,
                query_text=query,
                top_k=top_k * 2,
            )
        )

        results = self._merge_results(
            vector_results,
            keyword_results,
            top_k * 2,
        )

        # --- Rerank ---
        results = self._rerank(
            query=query,
            results=results,
            top_k=top_k,
        )

        context = (
            self.context_builder.build(
                query=query,
                results=results,
            )
        )

        elapsed_ms = (
            time.perf_counter()
            - started
        ) * 1000

        return {
            "query": query,
            "results": results,
            "context": context,
            "processing_time_ms": elapsed_ms,
        }

    def _merge_results(
        self,
        vector_results: list[dict[str, Any]],
        keyword_results: list[dict[str, Any]],
        top_k: int,
    ) -> list[dict[str, Any]]:

        merged: dict[str, dict[str, Any]] = {}

        for item in vector_results:

            key = str(item["chunk_id"])

            item["vector_score"] = float(
                item.get("score", 0.0)
            )

            item["keyword_score"] = 0.0

            item["score"] = (
                item["vector_score"] * 0.7
            )

            merged[key] = item

        for item in keyword_results:

            key = str(item["chunk_id"])

            if key in merged:

                merged[key]["keyword_score"] = 1.0

                merged[key]["score"] += 0.3

            else:

                item["vector_score"] = 0.0
                item["keyword_score"] = 1.0
                item["score"] = 0.3

                merged[key] = item

        results = list(
            merged.values()
        )

        results.sort(
            key=lambda item: item.get(
                "score",
                0.0,
            ),
            reverse=True,
        )

        return results[:top_k]

    def _rerank(
        self,
        query: str,
        results: list[dict[str, Any]],
        top_k: int = 10,
    ) -> list[dict[str, Any]]:

        query_terms = {
            term.lower()
            for term in query.split()
            if len(term) > 2
        }

        ranked = []

        for result in results:

            content = result.get(
                "content",
                "",
            ).lower()

            symbol_name = (
                result.get(
                    "symbol_name"
                )
                or ""
            ).lower()

            term_matches = sum(
                1
                for term in query_terms
                if term in content
            )

            symbol_bonus = (
                0.25
                if any(
                    term in symbol_name
                    for term in query_terms
                )
                else 0.0
            )

            base_score = float(
                result.get(
                    "score",
                    0.0,
                )
            )

            rerank_score = (
                base_score
                + min(
                    term_matches * 0.05,
                    0.25,
                )
                + symbol_bonus
            )

            result["rerank_score"] = (
                rerank_score
            )

            result["score"] = (
                rerank_score
            )

            ranked.append(result)

        ranked.sort(
            key=lambda item: item.get(
                "rerank_score",
                0.0,
            ),
            reverse=True,
        )

        return ranked[:top_k]