"""Storage ports for the Governance Layer (Phase 7).

Follows the same hexagonal pattern as Phases 1–6 stores.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from .enums import AuditEventType, PolicyScope
from .models import AuditEvent, Policy


@runtime_checkable
class PolicyStore(Protocol):
    """Port for persisting and querying governance policies."""

    async def add(self, policy: Policy) -> None: ...

    async def get(self, policy_id: str) -> Policy: ...

    async def list_active(self, scope: PolicyScope | None = None) -> list[Policy]: ...

    async def disable(self, policy_id: str) -> None: ...


@runtime_checkable
class AuditStore(Protocol):
    """Port for persisting and querying audit events."""

    async def record(self, event: AuditEvent) -> None: ...

    async def get(self, event_id: str) -> AuditEvent: ...

    async def query(
        self,
        *,
        agent_id: str | None = None,
        step_id: str | None = None,
        event_type: AuditEventType | None = None,
    ) -> list[AuditEvent]: ...
