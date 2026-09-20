"""PolicyEngine — evaluates active policies against context items and steps."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from scp.agent.models import AgentStep, ContextItem
from scp.memory.enums import VerificationStatus

from .enums import PolicyAction, PolicyScope
from .models import Policy, PolicyCondition, PolicyEvaluation
from .store import PolicyStore

# Severity ordering for outcome computation
_SEVERITY: dict[PolicyAction, int] = {
    PolicyAction.ALLOW: 0,
    PolicyAction.WARN: 1,
    PolicyAction.REQUIRE_REVIEW: 2,
    PolicyAction.DENY: 3,
}


def _check_item_condition(
    condition: PolicyCondition,
    trust_score: float,
    verification_status: VerificationStatus | None,
) -> tuple[bool, str]:
    """Return (triggered, reason) for CONTEXT_ITEM scope conditions.

    Uses AND logic: all present sub-conditions must fire for triggered=True.
    A condition with no item-level fields never triggers.
    """
    parts: list[tuple[bool, str]] = []

    if condition.min_trust_score is not None:
        below = trust_score < condition.min_trust_score
        msg = (
            f"trust {trust_score:.3f} < required {condition.min_trust_score:.3f}"
            if below
            else f"trust {trust_score:.3f} >= required {condition.min_trust_score:.3f}"
        )
        parts.append((below, msg))

    if condition.forbidden_verification_status is not None:
        forbidden = verification_status == condition.forbidden_verification_status
        msg = (
            f"status {verification_status!r} is forbidden"
            if forbidden
            else f"status {verification_status!r} is acceptable"
        )
        parts.append((forbidden, msg))

    if not parts:
        return False, "no item-level conditions defined"

    triggered = all(fired for fired, _ in parts)
    reason = "; ".join(msg for _, msg in parts)
    return triggered, reason


def _check_step_condition(condition: PolicyCondition, avg_trust: float) -> tuple[bool, str]:
    """Return (triggered, reason) for AGENT_STEP scope conditions."""
    if condition.min_average_trust is None:
        return False, "no step-level conditions defined"

    below = avg_trust < condition.min_average_trust
    reason = (
        f"average trust {avg_trust:.3f} < required {condition.min_average_trust:.3f}"
        if below
        else f"average trust {avg_trust:.3f} >= required {condition.min_average_trust:.3f}"
    )
    return below, reason


def _make_evaluation(
    policy: Policy,
    *,
    triggered: bool,
    target_id: str,
    trust_score: float | None,
    reason: str,
) -> PolicyEvaluation:
    return PolicyEvaluation(
        evaluation_id=uuid.uuid4().hex,
        policy_id=policy.policy_id,
        policy_name=policy.name,
        scope=policy.scope,
        action=policy.action,
        triggered=triggered,
        target_id=target_id,
        trust_score=trust_score,
        reason=reason,
        evaluated_at=datetime.now(UTC),
    )


def compute_outcome(evaluations: list[PolicyEvaluation]) -> PolicyAction:
    """Most severe action among triggered evaluations; ALLOW if none triggered."""
    triggered = [e for e in evaluations if e.triggered]
    if not triggered:
        return PolicyAction.ALLOW
    return max(triggered, key=lambda e: _SEVERITY[e.action]).action


class PolicyEngine:
    """Evaluates active policies against context items and agent steps."""

    def __init__(self, store: PolicyStore) -> None:
        self._store = store

    async def evaluate_context_item(
        self,
        item: ContextItem,
        *,
        verification_status: VerificationStatus | None = None,
    ) -> list[PolicyEvaluation]:
        policies = await self._store.list_active(scope=PolicyScope.CONTEXT_ITEM)
        evaluations: list[PolicyEvaluation] = []
        for policy in policies:
            triggered, reason = _check_item_condition(
                policy.condition, item.trust_score, verification_status
            )
            evaluations.append(
                _make_evaluation(
                    policy,
                    triggered=triggered,
                    target_id=item.entity_id,
                    trust_score=item.trust_score,
                    reason=reason,
                )
            )
        return evaluations

    async def evaluate_step(self, step: AgentStep) -> list[PolicyEvaluation]:
        policies = await self._store.list_active(scope=PolicyScope.AGENT_STEP)
        items = step.context.items
        avg_trust = (sum(i.trust_score for i in items) / len(items)) if items else 0.0
        evaluations: list[PolicyEvaluation] = []
        for policy in policies:
            triggered, reason = _check_step_condition(policy.condition, avg_trust)
            evaluations.append(
                _make_evaluation(
                    policy,
                    triggered=triggered,
                    target_id=step.step_id,
                    trust_score=avg_trust,
                    reason=reason,
                )
            )
        return evaluations
