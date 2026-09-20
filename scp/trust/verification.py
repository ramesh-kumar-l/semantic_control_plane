"""Verification state machine — signal-driven transitions (`14-trust-model.md`).

Each `TrustSignal` maps to a target `VerificationStatus`; a transition is applied
only if allowed. Same-state signals are idempotent. The one deliberate guard:
a CONTRADICTED item cannot jump straight to VERIFIED — it must be REOPENED (to
DISPUTED) first, keeping an auditable trail before a contradiction is overturned.
"""

from __future__ import annotations

from scp.memory import VerificationStatus

from .enums import TrustSignal
from .errors import InvalidVerificationTransitionError

_SIGNAL_TARGET: dict[TrustSignal, VerificationStatus] = {
    TrustSignal.HUMAN_VERIFIED: VerificationStatus.VERIFIED,
    TrustSignal.CORROBORATED: VerificationStatus.VERIFIED,
    TrustSignal.CONFLICTING_EVIDENCE: VerificationStatus.DISPUTED,
    TrustSignal.REOPENED: VerificationStatus.DISPUTED,
    TrustSignal.CONTRADICTED_BY_SOURCE: VerificationStatus.CONTRADICTED,
    TrustSignal.RETRACTED: VerificationStatus.CONTRADICTED,
}

# Transitions that are explicitly forbidden (must route through an intermediate).
_FORBIDDEN: frozenset[tuple[VerificationStatus, VerificationStatus]] = frozenset(
    {(VerificationStatus.CONTRADICTED, VerificationStatus.VERIFIED)}
)


class VerificationPolicy:
    """Applies trust signals to verification status under documented rules."""

    @staticmethod
    def target(signal: TrustSignal) -> VerificationStatus:
        """The verification status a signal moves an item toward."""
        return _SIGNAL_TARGET[signal]

    def apply(self, current: VerificationStatus, signal: TrustSignal) -> VerificationStatus:
        """Return the new status after `signal`, or raise if the move is forbidden."""
        target = _SIGNAL_TARGET[signal]
        if target == current:
            return current
        if (current, target) in _FORBIDDEN:
            raise InvalidVerificationTransitionError(current, signal, target)
        return target
