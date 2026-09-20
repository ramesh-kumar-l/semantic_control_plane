"""Enumerations for the Governance Layer (Phase 7)."""

from __future__ import annotations

from enum import StrEnum


class PolicyAction(StrEnum):
    """Action taken when a policy condition fires."""

    ALLOW = "allow"
    WARN = "warn"
    REQUIRE_REVIEW = "require_review"
    DENY = "deny"


class PolicyScope(StrEnum):
    """Which subjects a policy governs."""

    CONTEXT_ITEM = "context_item"
    AGENT_STEP = "agent_step"


class AuditEventType(StrEnum):
    """Type tag on every persisted audit event."""

    CONTEXT_ITEM_GOVERNED = "context_item_governed"
    STEP_GOVERNED = "step_governed"
    COMPLIANCE_CHECK = "compliance_check"
