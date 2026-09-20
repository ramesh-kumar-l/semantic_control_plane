"""In-memory `MemoryStore` adapter — deterministic, no I/O. For tests/dev."""

from __future__ import annotations

from ..errors import DuplicateMemoryError, MemoryNotFoundError
from ..models import MemoryRecord
from ..store import MemoryQuery, MemoryStore


class InMemoryStore(MemoryStore):
    """A dict-backed store. Returns deep copies so callers can't mutate state."""

    def __init__(self) -> None:
        self._records: dict[str, MemoryRecord] = {}

    async def add(self, record: MemoryRecord) -> None:
        if record.id in self._records:
            raise DuplicateMemoryError(record.id)
        self._records[record.id] = record.model_copy(deep=True)

    async def get(self, memory_id: str) -> MemoryRecord | None:
        record = self._records.get(memory_id)
        return record.model_copy(deep=True) if record is not None else None

    async def update(self, record: MemoryRecord) -> None:
        if record.id not in self._records:
            raise MemoryNotFoundError(record.id)
        self._records[record.id] = record.model_copy(deep=True)

    async def query(self, query: MemoryQuery) -> list[MemoryRecord]:
        matches = [
            record
            for record in self._records.values()
            if (query.type is None or record.type == query.type)
            and (query.lifecycle_state is None or record.lifecycle_state == query.lifecycle_state)
        ]
        matches.sort(key=lambda r: r.temporal.created_at, reverse=query.newest_first)
        window = matches[query.offset : query.offset + query.limit]
        return [record.model_copy(deep=True) for record in window]

    async def delete(self, memory_id: str) -> bool:
        return self._records.pop(memory_id, None) is not None
