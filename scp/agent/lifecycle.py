"""In-memory agent lifecycle management.

Owns all state transitions and enforces the documented transition graph.
This is intentionally in-memory for Phase 5; a durable `AgentStore` port
can be introduced in a future phase without changing the `AgentRuntime` API.

Valid transitions (from → to):
    IDLE     → RUNNING
    RUNNING  → PAUSED | STOPPED | FAILED
    PAUSED   → RUNNING | STOPPED
"""

from __future__ import annotations

from datetime import UTC, datetime

from .enums import AgentStatus
from .errors import AgentNotFoundError, InvalidAgentTransitionError
from .models import AgentConfig, AgentState

_VALID: frozenset[tuple[AgentStatus, AgentStatus]] = frozenset(
    {
        (AgentStatus.IDLE, AgentStatus.RUNNING),
        (AgentStatus.RUNNING, AgentStatus.PAUSED),
        (AgentStatus.RUNNING, AgentStatus.STOPPED),
        (AgentStatus.RUNNING, AgentStatus.FAILED),
        (AgentStatus.PAUSED, AgentStatus.RUNNING),
        (AgentStatus.PAUSED, AgentStatus.STOPPED),
    }
)


class AgentLifecycle:
    """In-memory lifecycle store: create, look up, and transition agent states."""

    def __init__(self) -> None:
        self._states: dict[str, AgentState] = {}

    def create(self, config: AgentConfig) -> AgentState:
        """Register a new agent in the IDLE state."""
        now = datetime.now(UTC)
        state = AgentState(
            agent_id=config.agent_id,
            status=AgentStatus.IDLE,
            config=config,
            created_at=now,
            updated_at=now,
        )
        self._states[config.agent_id] = state
        return state

    def get(self, agent_id: str) -> AgentState:
        """Return the current state. Raises `AgentNotFoundError` if unknown."""
        try:
            return self._states[agent_id]
        except KeyError:
            raise AgentNotFoundError(f"Agent {agent_id!r} not found") from None

    def transition(
        self,
        agent_id: str,
        target: AgentStatus,
        *,
        error: str | None = None,
    ) -> AgentState:
        """Apply a lifecycle transition, enforcing the documented graph.

        Idempotent: transitioning to the current status is a no-op.
        Raises `InvalidAgentTransitionError` for illegal moves.
        """
        state = self.get(agent_id)
        if state.status == target:
            return state
        if (state.status, target) not in _VALID:
            raise InvalidAgentTransitionError(
                f"Agent {agent_id!r}: {state.status!r} → {target!r} is not a valid transition"
            )
        state.status = target
        state.updated_at = datetime.now(UTC)
        if error is not None:
            state.error = error
        return state

    def all_agents(self) -> list[AgentState]:
        """All registered agents (unordered)."""
        return list(self._states.values())

    def remove(self, agent_id: str) -> None:
        """Deregister an agent (silently ignores unknown ids)."""
        self._states.pop(agent_id, None)
