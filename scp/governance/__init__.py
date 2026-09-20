"""Governance Layer — Phase 7.

Policy gates enforced on trust thresholds and verification status;
full audit trail; compliance controls.
"""

from .audit import AuditLogger
from .backends.in_memory import InMemoryAuditStore, InMemoryPolicyStore
from .engine import PolicyEngine, compute_outcome
from .enums import AuditEventType, PolicyAction, PolicyScope
from .errors import AuditError, GovernanceError, PolicyNotFoundError, PolicyViolationError
from .governance import GovernanceLayer
from .models import (
    AuditEvent,
    ComplianceReport,
    Policy,
    PolicyCondition,
    PolicyEvaluation,
)
from .store import AuditStore, PolicyStore

__all__ = [
    # Service
    "GovernanceLayer",
    # Engines
    "PolicyEngine",
    "AuditLogger",
    "compute_outcome",
    # Stores
    "PolicyStore",
    "AuditStore",
    "InMemoryPolicyStore",
    "InMemoryAuditStore",
    # Models
    "Policy",
    "PolicyCondition",
    "PolicyEvaluation",
    "AuditEvent",
    "ComplianceReport",
    # Enums
    "PolicyAction",
    "PolicyScope",
    "AuditEventType",
    # Errors
    "GovernanceError",
    "PolicyNotFoundError",
    "PolicyViolationError",
    "AuditError",
]
