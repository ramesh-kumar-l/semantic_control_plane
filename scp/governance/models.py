"""Pydantic models for the Governance Layer (Phase 7).

All models are frozen (immutable) — governance records are append-only.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from scp.memory.enums import VerificationStatus

from .enums import AuditEventType, PolicyAction, PolicyScope


class PolicyCondition(BaseModel, frozen=True):
    """Conditions that must ALL be met for the policy action to fire.

    CONTEXT_ITEM scope uses `min_trust_score` and `forbidden_verification_status`.
    AGENT_STEP scope uses `min_average_trust`.
    A condition with no fields set never triggers.
    """

    # Context-item level conditions
    min_trust_score: float | None = None
    forbidden_verification_status: VerificationStatus | None = None

    # Step-level aggregate condition
    min_average_trust: float | None = None


class Policy(BaseModel, frozen=True):
    """A named governance rule: when condition fires, apply action."""

    policy_id: str
    name: str
    description: str
    scope: PolicyScope
    condition: PolicyCondition
    action: PolicyAction
    enabled: bool = True
    created_at: datetime


class PolicyEvaluation(BaseModel, frozen=True):
    """Result of evaluating a single policy against one subject."""

    evaluation_id: str
    policy_id: str
    policy_name: str
    scope: PolicyScope
    action: PolicyAction
    triggered: bool
    target_id: str
    trust_score: float | None
    reason: str
    evaluated_at: datetime


class AuditEvent(BaseModel, frozen=True):
    """Immutable record of one governance evaluation (context item or step)."""

    event_id: str
    event_type: AuditEventType
    agent_id: str | None
    step_id: str | None
    entity_id: str | None
    evaluations: list[PolicyEvaluation]
    outcome: PolicyAction
    created_at: datetime


class ComplianceReport(BaseModel, frozen=True):
    """Summary of compliance status for an agent (or entire system)."""

    report_id: str
    agent_id: str | None
    total_events: int
    violations: list[AuditEvent]
    warnings: list[AuditEvent]
    review_required: list[AuditEvent]
    compliant: bool
    generated_at: datetime
