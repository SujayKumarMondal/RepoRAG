"""
Embedding generation orchestration.
"""

from app.services.embeddings.provider import (
    EmbeddingProvider,
)


class EmbeddingGenerator:
    """
    Generates embeddings for RepoRAG code chunks.
    """

    def __init__(
        self,
        provider: EmbeddingProvider,
    ) -> None:

        self.provider = provider

    async def generate(
        self,
        content: str,
    ) -> list[float]:

        if not content.strip():
            raise ValueError(
                "Cannot generate embedding for empty text."
            )

        return await self.provider.embed(
            content
        )

    async def generate_many(
        self,
        contents: list[str],
    ) -> list[list[float]]:

        if not contents:
            return []

        return await self.provider.embed_many(
            contents
        )