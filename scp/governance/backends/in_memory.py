"""In-memory adapters for PolicyStore and AuditStore (dev/test backend)."""

from __future__ import annotations

from scp.governance.enums import AuditEventType, PolicyScope
from scp.governance.errors import AuditError, PolicyNotFoundError
from scp.governance.models import AuditEvent, Policy


class InMemoryPolicyStore:
    """Dict-backed PolicyStore; policies keyed by policy_id."""

    def __init__(self) -> None:
        self._policies: dict[str, Policy] = {}

    async def add(self, policy: Policy) -> None:
        self._policies[policy.policy_id] = policy

    async def get(self, policy_id: str) -> Policy:
        try:
            return self._policies[policy_id]
        except KeyError:
            raise PolicyNotFoundError(policy_id) from None

    async def list_active(self, scope: PolicyScope | None = None) -> list[Policy]:
        results = [p for p in self._policies.values() if p.enabled]
        if scope is not None:
            results = [p for p in results if p.scope == scope]
        return results

    async def disable(self, policy_id: str) -> None:
        policy = await self.get(policy_id)
        # Frozen model: replace with disabled copy using model_copy
        self._policies[policy_id] = policy.model_copy(update={"enabled": False})


class InMemoryAuditStore:
    """Dict-backed AuditStore; events keyed by event_id, insertion-ordered."""

    def __init__(self) -> None:
        self._events: dict[str, AuditEvent] = {}

    async def record(self, event: AuditEvent) -> None:
        self._events[event.event_id] = event

    async def get(self, event_id: str) -> AuditEvent:
        try:
            return self._events[event_id]
        except KeyError:
            raise AuditError(event_id) from None

    async def query(
        self,
        *,
        agent_id: str | None = None,
        step_id: str | None = None,
        event_type: AuditEventType | None = None,
    ) -> list[AuditEvent]:
        results = list(self._events.values())
        if agent_id is not None:
            results = [e for e in results if e.agent_id == agent_id]
        if step_id is not None:
            results = [e for e in results if e.step_id == step_id]
        if event_type is not None:
            results = [e for e in results if e.event_type == event_type]
        return sorted(results, key=lambda e: e.created_at)
