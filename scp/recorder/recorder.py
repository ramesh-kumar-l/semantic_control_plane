"""`FlightRecorder` — the public service API for Phase 6 Agent Flight Recorder.

Composes ReplayEngine, TraceEngine, and DebugEngine behind a single entry
point. Accepts `AgentStep` objects produced by Phase 5 `AgentRuntime` and
stores them as immutable `RecordedStep` snapshots.

Boundaries: the recorder depends only on Phase 5's public `AgentStep` /
`AgentContext` / `ToolResult` models. It never reaches into agent internals.
See `adr/ADR-007-flight-recorder.md`.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from scp.agent.models import AgentStep

from .backends.in_memory import InMemoryRecordStore
from .debug import DebugEngine
from .models import RecordedStep, ReplaySession, RootCauseReport, Trace
from .replay import ReplayEngine
from .store import RecordStore
from .trace import TraceEngine


class FlightRecorder:
    """Phase 6 service: record agent steps, replay, trace, and debug."""

    def __init__(self, *, store: RecordStore | None = None) -> None:
        self._store: RecordStore = store if store is not None else InMemoryRecordStore()
        self._replay = ReplayEngine(self._store)
        self._trace = TraceEngine(self._store)
        self._debug = DebugEngine(self._store)

    # --- Recording --------------------------------------------------------

    async def record(
        self,
        step: AgentStep,
        *,
        agent_name: str,
        step_index: int = 0,
    ) -> RecordedStep:
        """Persist a snapshot of `step` and return the `RecordedStep`.

        `step_index` should be the 0-based position of this step within the
        agent's history (e.g. ``len(agent_state.steps) - 1`` after appending).
        """
        rec = RecordedStep(
            record_id=uuid.uuid4().hex,
            agent_id=step.agent_id,
            agent_name=agent_name,
            step_id=step.step_id,
            step_index=step_index,
            query=step.query,
            context_snapshot=step.context,
            tool_results=list(step.tool_results),
            created_at=step.created_at,
            recorded_at=datetime.now(UTC),
        )
        await self._store.store(rec)
        return rec

    # --- Replay -----------------------------------------------------------

    async def replay_step(self, step_id: str) -> RecordedStep:
        """Return the recorded snapshot for `step_id`. Raises `RecordNotFoundError`."""
        return await self._replay.replay_step(step_id)

    async def replay_agent(
        self,
        agent_id: str,
        *,
        from_index: int = 0,
        to_index: int | None = None,
    ) -> ReplaySession:
        """Return an ordered reconstruction of the agent's step history."""
        return await self._replay.replay_agent(agent_id, from_index=from_index, to_index=to_index)

    # --- Trace ------------------------------------------------------------

    async def trace_entity(
        self,
        entity_id: str,
        *,
        agent_id: str | None = None,
    ) -> Trace:
        """Return all recorded appearances of `entity_id` across steps."""
        return await self._trace.trace_entity(entity_id, agent_id=agent_id)

    async def trace_step(self, step_id: str) -> list[Trace]:
        """Return one `Trace` per context entity in the given step."""
        return await self._trace.trace_step(step_id)

    # --- Debug ------------------------------------------------------------

    async def root_cause(self, step_id: str) -> RootCauseReport:
        """Return a structured root-cause report for the given step."""
        return await self._debug.root_cause(step_id)
