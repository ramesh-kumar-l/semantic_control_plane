"""In-memory `VectorStore` adapter — brute-force cosine. Deterministic, no I/O.

Adequate for development, tests, and single-node deployments where the index is
rebuilt on startup from Memory Core / the Knowledge Graph. An approximate-nearest-
neighbour or pgvector adapter is a future ADR behind the same port
(`adr/ADR-004-semantic-query-engine.md`).
"""

from __future__ import annotations

from ..embeddings import Vector, cosine
from ..vector_store import VectorMatch, VectorStore


class InMemoryVectorStore(VectorStore):
    """Dict-backed cosine index."""

    def __init__(self) -> None:
        self._vectors: dict[str, Vector] = {}

    async def upsert(self, vector_id: str, vector: Vector) -> None:
        self._vectors[vector_id] = vector

    async def get(self, vector_id: str) -> Vector | None:
        return self._vectors.get(vector_id)

    async def delete(self, vector_id: str) -> bool:
        return self._vectors.pop(vector_id, None) is not None

    async def search(self, vector: Vector, top_k: int) -> list[VectorMatch]:
        if top_k < 1:
            return []
        scored = [
            VectorMatch(id=vid, score=cosine(vector, stored))
            for vid, stored in self._vectors.items()
        ]
        # Highest score first; ties broken by ascending id (deterministic).
        scored.sort(key=lambda m: (-m.score, m.id))
        return scored[:top_k]

    async def clear(self) -> None:
        self._vectors.clear()

    async def size(self) -> int:
        return len(self._vectors)
