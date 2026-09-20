"""Typed exceptions for the Governance Layer (Phase 7)."""

from __future__ import annotations


class GovernanceError(Exception):
    """Base for all governance errors."""


class PolicyNotFoundError(GovernanceError):
    def __init__(self, policy_id: str) -> None:
        super().__init__(f"Policy not found: {policy_id!r}")
        self.policy_id = policy_id


class PolicyViolationError(GovernanceError):
    """Raised by callers that treat a DENY outcome as a hard exception."""

    def __init__(self, step_id: str, policy_names: list[str]) -> None:
        names = ", ".join(policy_names)
        super().__init__(f"Step {step_id!r} denied by policies: {names}")
        self.step_id = step_id
        self.policy_names = policy_names


class AuditError(GovernanceError):
    """Raised when an audit event cannot be stored or retrieved."""

    def __init__(self, event_id: str) -> None:
        super().__init__(f"Audit event not found: {event_id!r}")
        self.event_id = event_id
