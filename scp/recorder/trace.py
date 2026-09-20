"""`TraceEngine` — links entity appearances across recorded steps."""

from __future__ import annotations

import uuid

from .models import RecordQuery, Trace, TraceAppearance
from .store import RecordStore


class TraceEngine:
    """Traces where a specific entity appeared across an agent's history."""

    def __init__(self, store: RecordStore) -> None:
        self._store = store

    async def trace_entity(
        self,
        entity_id: str,
        *,
        agent_id: str | None = None,
    ) -> Trace:
        """Return all recorded appearances of `entity_id`.

        Pass `agent_id` to scope the trace to one agent; omit for cross-agent traces.
        """
        records = await self._store.query(
            RecordQuery(entity_id=entity_id, agent_id=agent_id, max_results=10_000)
        )

        appearances: list[TraceAppearance] = []
        entity_name = ""

        for record in records:
            for item in record.context_snapshot.items:
                if item.entity_id == entity_id:
                    if not entity_name:
                        entity_name = item.name
                    appearances.append(
                        TraceAppearance(
                            step_id=record.step_id,
                            step_index=record.step_index,
                            query=record.query,
                            trust_score=item.trust_score,
                            explanation=item.explanation,
                            created_at=record.created_at,
                        )
                    )

        return Trace(
            trace_id=uuid.uuid4().hex,
            entity_id=entity_id,
            entity_name=entity_name,
            agent_id=agent_id,
            appearances=appearances,
        )

    async def trace_step(self, step_id: str) -> list[Trace]:
        """Return one `Trace` per context entity referenced in the given step."""
        record = await self._store.get_by_step(step_id)
        traces: list[Trace] = []
        for item in record.context_snapshot.items:
            trace = await self.trace_entity(item.entity_id, agent_id=record.agent_id)
            traces.append(trace)
        return traces
