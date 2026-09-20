"""Typed exceptions for the Trust Engine (explicit failures, never silent — `99` §11)."""

from __future__ import annotations

from scp.memory import VerificationStatus

from .enums import TrustSignal


class TrustEngineError(Exception):
    """Base class for all Trust Engine errors."""


class InvalidVerificationTransitionError(TrustEngineError):
    """Raised when a `TrustSignal` would force a disallowed verification transition.

    Overturning a contradiction requires re-opening it first (audit-friendly),
    so e.g. CONTRADICTED → VERIFIED is rejected (`14-trust-model.md`).
    """

    def __init__(
        self, current: VerificationStatus, signal: TrustSignal, target: VerificationStatus
    ) -> None:
        self.current = current
        self.signal = signal
        self.target = target
        super().__init__(f"cannot move {current} -> {target} via signal {signal}")
