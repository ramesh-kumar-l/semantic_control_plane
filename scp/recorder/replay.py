"""`ReplayEngine` — reconstructs ordered step sequences from recorded evidence."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from .models import RecordedStep, RecordQuery, ReplaySession
from .store import RecordStore


class ReplayEngine:
    """Rebuilds an agent's step history from the record store."""

    def __init__(self, store: RecordStore) -> None:
        self._store = store

    async def replay_step(self, step_id: str) -> RecordedStep:
        """Return the recorded step for `step_id`. Raises `RecordNotFoundError`."""
        return await self._store.get_by_step(step_id)

    async def replay_agent(
        self,
        agent_id: str,
        *,
        from_index: int = 0,
        to_index: int | None = None,
    ) -> ReplaySession:
        """Return an ordered reconstruction of the agent's steps.

        `from_index` and `to_index` are 0-based step_index values (inclusive).
        When `to_index` is None the full history from `from_index` is returned.
        """
        records = await self._store.query(RecordQuery(agent_id=agent_id, max_results=10_000))
        records.sort(key=lambda r: (r.created_at, r.step_index))

        end = to_index if to_index is not None else max(len(records) - 1, 0)
        window = records[from_index : end + 1]

        return ReplaySession(
            session_id=uuid.uuid4().hex,
            agent_id=agent_id,
            steps=window,
            from_index=from_index,
            to_index=end,
            created_at=datetime.now(UTC),
        )
