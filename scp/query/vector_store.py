"""The `VectorStore` port — the similarity-index seam the engine depends on.

The index is a **derived** structure: Memory Core and the Knowledge Graph remain
the source of truth, so the index can be rebuilt at any time (`reindex`). Concrete
adapters live in `backends/`. Changing this interface is a protected-architecture
change (`99` §3, `adr/ADR-004-semantic-query-engine.md`).
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from pydantic import BaseModel

from .embeddings import Vector


class VectorMatch(BaseModel):
    """A search hit: the indexed id and its similarity score in [0.0, 1.0]."""

    id: str
    score: float


class VectorStore(ABC):
    """Persistence port for embedding vectors keyed by entity id."""

    @abstractmethod
    async def upsert(self, vector_id: str, vector: Vector) -> None:
        """Insert or replace the vector stored under `vector_id`."""

    @abstractmethod
    async def get(self, vector_id: str) -> Vector | None:
        """Return the stored vector, or None if absent."""

    @abstractmethod
    async def delete(self, vector_id: str) -> bool:
        """Remove a vector. Returns True if one was removed."""

    @abstractmethod
    async def search(self, vector: Vector, top_k: int) -> list[VectorMatch]:
        """Return the `top_k` most similar ids, highest score first.

        Ties are broken by ascending id for deterministic ordering.
        """

    @abstractmethod
    async def clear(self) -> None:
        """Drop all vectors."""

    @abstractmethod
    async def size(self) -> int:
        """Number of indexed vectors."""

    async def close(self) -> None:
        """Release resources. Default no-op; adapters override as needed."""
        return None
