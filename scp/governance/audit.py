"""AuditLogger — persists governance events and produces compliance reports."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from .enums import AuditEventType, PolicyAction
from .models import AuditEvent, ComplianceReport, PolicyEvaluation
from .store import AuditStore


def _compute_outcome(evaluations: list[PolicyEvaluation]) -> PolicyAction:
    from .engine import compute_outcome

    return compute_outcome(evaluations)


class AuditLogger:
    """Records AuditEvents and answers compliance queries against an AuditStore."""

    def __init__(self, store: AuditStore) -> None:
        self._store = store

    async def log(
        self,
        *,
        event_type: AuditEventType,
        agent_id: str | None,
        step_id: str | None,
        entity_id: str | None,
        evaluations: list[PolicyEvaluation],
    ) -> AuditEvent:
        event = AuditEvent(
            event_id=uuid.uuid4().hex,
            event_type=event_type,
            agent_id=agent_id,
            step_id=step_id,
            entity_id=entity_id,
            evaluations=evaluations,
            outcome=_compute_outcome(evaluations),
            created_at=datetime.now(UTC),
        )
        await self._store.record(event)
        return event

    async def get_event(self, event_id: str) -> AuditEvent:
        return await self._store.get(event_id)

    async def trail(self, agent_id: str | None = None) -> list[AuditEvent]:
        return await self._store.query(agent_id=agent_id)

    async def compliance_report(self, agent_id: str | None = None) -> ComplianceReport:
        events = await self._store.query(agent_id=agent_id)
        violations = [e for e in events if e.outcome == PolicyAction.DENY]
        warnings = [e for e in events if e.outcome == PolicyAction.WARN]
        review_required = [e for e in events if e.outcome == PolicyAction.REQUIRE_REVIEW]
        return ComplianceReport(
            report_id=uuid.uuid4().hex,
            agent_id=agent_id,
            total_events=len(events),
            violations=violations,
            warnings=warnings,
            review_required=review_required,
            compliant=len(violations) == 0,
            generated_at=datetime.now(UTC),
        )
