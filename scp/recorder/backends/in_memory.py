"""In-memory `RecordStore` adapter — development and test backend."""

from __future__ import annotations

from scp.recorder.errors import RecordNotFoundError
from scp.recorder.models import RecordedStep, RecordQuery


class InMemoryRecordStore:
    """Thread-safe (single-process) record store backed by a plain dict."""

    def __init__(self) -> None:
        self._by_id: dict[str, RecordedStep] = {}
        self._step_index: dict[str, str] = {}  # step_id → record_id

    async def store(self, record: RecordedStep) -> None:
        self._by_id[record.record_id] = record
        self._step_index[record.step_id] = record.record_id

    async def get(self, record_id: str) -> RecordedStep:
        try:
            return self._by_id[record_id]
        except KeyError:
            raise RecordNotFoundError(record_id) from None

    async def get_by_step(self, step_id: str) -> RecordedStep:
        record_id = self._step_index.get(step_id)
        if record_id is None:
            raise RecordNotFoundError(step_id)
        return self._by_id[record_id]

    async def query(self, q: RecordQuery) -> list[RecordedStep]:
        results: list[RecordedStep] = list(self._by_id.values())

        if q.agent_id is not None:
            results = [r for r in results if r.agent_id == q.agent_id]
        if q.step_id is not None:
            results = [r for r in results if r.step_id == q.step_id]
        if q.entity_id is not None:
            results = [
                r
                for r in results
                if any(item.entity_id == q.entity_id for item in r.context_snapshot.items)
            ]
        if q.created_after is not None:
            results = [r for r in results if r.created_at >= q.created_after]
        if q.created_before is not None:
            results = [r for r in results if r.created_at <= q.created_before]

        results.sort(key=lambda r: (r.created_at, r.step_index))
        return results[: q.max_results]

    async def count(self, agent_id: str) -> int:
        return sum(1 for r in self._by_id.values() if r.agent_id == agent_id)
