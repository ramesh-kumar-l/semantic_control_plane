"""GovernanceLayer — single service entry point composing PolicyEngine + AuditLogger."""

from __future__ import annotations

from scp.agent.models import AgentStep, ContextItem
from scp.memory.enums import VerificationStatus

from .audit import AuditLogger
from .backends.in_memory import InMemoryAuditStore, InMemoryPolicyStore
from .engine import PolicyEngine
from .enums import AuditEventType, PolicyScope
from .models import AuditEvent, ComplianceReport, Policy
from .store import AuditStore, PolicyStore


class GovernanceLayer:
    """Composes PolicyEngine and AuditLogger behind a single public API.

    Usage::

        gov = GovernanceLayer()
        await gov.add_policy(policy)
        event = await gov.govern_context_item(item, agent_id=..., step_id=...)
        report = await gov.compliance_report(agent_id=...)
    """

    def __init__(
        self,
        *,
        policy_store: PolicyStore | None = None,
        audit_store: AuditStore | None = None,
    ) -> None:
        ps: PolicyStore = policy_store if policy_store is not None else InMemoryPolicyStore()
        as_: AuditStore = audit_store if audit_store is not None else InMemoryAuditStore()
        self._engine = PolicyEngine(ps)
        self._audit = AuditLogger(as_)
        self._policy_store = ps

    # ------------------------------------------------------------------ policies

    async def add_policy(self, policy: Policy) -> None:
        await self._policy_store.add(policy)

    async def get_policy(self, policy_id: str) -> Policy:
        return await self._policy_store.get(policy_id)

    async def list_policies(self, scope: PolicyScope | None = None) -> list[Policy]:
        return await self._policy_store.list_active(scope=scope)

    async def disable_policy(self, policy_id: str) -> None:
        await self._policy_store.disable(policy_id)

    # ------------------------------------------------------------------ govern

    async def govern_context_item(
        self,
        item: ContextItem,
        *,
        agent_id: str,
        step_id: str,
        verification_status: VerificationStatus | None = None,
    ) -> AuditEvent:
        """Evaluate all CONTEXT_ITEM policies and persist one AuditEvent."""
        evaluations = await self._engine.evaluate_context_item(
            item, verification_status=verification_status
        )
        return await self._audit.log(
            event_type=AuditEventType.CONTEXT_ITEM_GOVERNED,
            agent_id=agent_id,
            step_id=step_id,
            entity_id=item.entity_id,
            evaluations=evaluations,
        )

    async def govern_step(self, step: AgentStep) -> AuditEvent:
        """Evaluate all AGENT_STEP policies and persist one AuditEvent."""
        evaluations = await self._engine.evaluate_step(step)
        return await self._audit.log(
            event_type=AuditEventType.STEP_GOVERNED,
            agent_id=step.agent_id,
            step_id=step.step_id,
            entity_id=None,
            evaluations=evaluations,
        )

    # ------------------------------------------------------------------ audit

    async def get_audit_event(self, event_id: str) -> AuditEvent:
        return await self._audit.get_event(event_id)

    async def get_audit_trail(self, agent_id: str | None = None) -> list[AuditEvent]:
        return await self._audit.trail(agent_id=agent_id)

    async def compliance_report(self, agent_id: str | None = None) -> ComplianceReport:
        return await self._audit.compliance_report(agent_id=agent_id)
