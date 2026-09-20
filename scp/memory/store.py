"""The `MemoryStore` port — the storage seam Memory Core depends on.

Concrete adapters live in `backends/` (`adr/ADR-002-memory-core-storage.md`).
Changing this interface is a protected-architecture change (`99` §3).
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from pydantic import BaseModel, Field

from .enums import LifecycleState, MemoryType
from .models import MemoryRecord


class MemoryQuery(BaseModel):
    """Retrieval filter for the store.

    Memory Core retrieves by id / type / recency / lifecycle state only.
    Similarity and graph retrieval belong to later phases (`11` boundaries).
    """

    type: MemoryType | None = None
    lifecycle_state: LifecycleState | None = None
    newest_first: bool = True
    limit: int = Field(default=100, ge=1, le=10_000)
    offset: int = Field(default=0, ge=0)


class MemoryStore(ABC):
    """Persistence port for memory records."""

    @abstractmethod
    async def add(self, record: MemoryRecord) -> None:
        """Persist a new record. Raises `DuplicateMemoryError` if id exists."""

    @abstractmethod
    async def get(self, memory_id: str) -> MemoryRecord | None:
        """Return the record, or None if absent."""

    @abstractmethod
    async def update(self, record: MemoryRecord) -> None:
        """Overwrite an existing record. Raises `MemoryNotFoundError` if absent."""

    @abstractmethod
    async def query(self, query: MemoryQuery) -> list[MemoryRecord]:
        """Return records matching the filter, ordered by recency."""

    @abstractmethod
    async def delete(self, memory_id: str) -> bool:
        """Hard-delete a record. Returns True if a row was removed."""

    async def close(self) -> None:
        """Release resources. Default no-op; adapters override as needed."""
        return None
