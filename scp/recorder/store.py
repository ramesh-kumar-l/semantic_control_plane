"""RecordStore port — the persistence boundary for the Flight Recorder.

Implementations must satisfy this protocol. The in-memory backend lives
in `scp.recorder.backends.in_memory`; durable adapters are future work.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from .models import RecordedStep, RecordQuery


@runtime_checkable
class RecordStore(Protocol):
    """Port: persists and retrieves `RecordedStep` objects."""

    async def store(self, record: RecordedStep) -> None:
        """Persist a recorded step. Overwrites silently if record_id exists."""
        ...

    async def get(self, record_id: str) -> RecordedStep:
        """Return the record. Raises `RecordNotFoundError` if absent."""
        ...

    async def get_by_step(self, step_id: str) -> RecordedStep:
        """Return the record whose step_id matches. Raises `RecordNotFoundError`."""
        ...

    async def query(self, q: RecordQuery) -> list[RecordedStep]:
        """Return records matching all non-None filters, ordered by created_at asc."""
        ...

    async def count(self, agent_id: str) -> int:
        """Return the total number of records for the given agent."""
        ...
