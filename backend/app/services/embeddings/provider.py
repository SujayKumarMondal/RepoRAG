"""
Embedding provider abstraction.
"""

import hashlib
import math
import re
from abc import ABC, abstractmethod


class EmbeddingProvider(ABC):
    """
    Interface for embedding providers.
    """

    @abstractmethod
    async def embed(
        self,
        text: str,
    ) -> list[float]:
        """
        Generate one embedding vector.
        """
        raise NotImplementedError

    async def embed_many(
        self,
        texts: list[str],
    ) -> list[list[float]]:

        results = []

        for text in texts:
            results.append(await self.embed(text))

        return results


class DeterministicEmbeddingProvider(EmbeddingProvider):
    """
    Small local fallback embedding engine used when no external embedding
    service is configured. It produces stable vectors based on token hashing,
    which is enough for local ranking and retrieval tests.
    """

    DIMENSION = 1536

    def _normalize(self, vector: list[float]) -> list[float]:
        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0:
            return [0.0] * self.DIMENSION
        return [value / norm for value in vector]

    async def embed(self, text: str) -> list[float]:
        tokens = re.findall(r"[A-Za-z0-9_]+", text.lower())
        if not tokens:
            return [0.0] * self.DIMENSION

        vector = [0.0] * self.DIMENSION
        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
            index = int(digest[:8], 16) % self.DIMENSION
            vector[index] += 1.0

        # Weigh common tokens more strongly for relevance.
        for i, value in enumerate(vector):
            if value:
                vector[i] = value * (1.0 + (i % 9) / 20.0)

        return self._normalize(vector)