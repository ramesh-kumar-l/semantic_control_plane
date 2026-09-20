"""`DebugEngine` — synthesises root-cause reports from recorded step evidence."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from scp.agent.models import ContextItem

from .models import RecordQuery, RootCauseReport
from .store import RecordStore


class DebugEngine:
    """Builds structured root-cause reports explaining what drove an agent step."""

    def __init__(self, store: RecordStore) -> None:
        self._store = store

    async def root_cause(self, step_id: str) -> RootCauseReport:
        """Explain why a step produced the outcome it did.

        Returns the top context items (sorted by trust score), all tool outcomes,
        extracted trust signals (explanation strings), and the step_ids of any
        prior steps that shared at least one context entity.

        Raises `RecordNotFoundError` if `step_id` is unknown.
        """
        record = await self._store.get_by_step(step_id)

        top_items: list[ContextItem] = sorted(
            record.context_snapshot.items,
            key=lambda i: i.trust_score,
            reverse=True,
        )

        trust_signals: list[str] = [item.explanation for item in top_items if item.explanation]

        related_ids: set[str] = set()
        for item in record.context_snapshot.items:
            siblings = await self._store.query(
                RecordQuery(entity_id=item.entity_id, agent_id=record.agent_id, max_results=500)
            )
            for sibling in siblings:
                if sibling.step_id != step_id:
                    related_ids.add(sibling.step_id)

        return RootCauseReport(
            report_id=uuid.uuid4().hex,
            step_id=step_id,
            agent_id=record.agent_id,
            query=record.query,
            top_context_items=top_items,
            tool_outcomes=record.tool_results,
            trust_signals=trust_signals,
            related_step_ids=sorted(related_ids),
            created_at=datetime.now(UTC),
        )
