"""Enumerations for the Trust Engine domain.

Kept separate from `models.py` so types stay small and single-responsibility
(`99-development-rules.md` §11). Verification *status* itself is reused from
Memory Core (`scp.memory.VerificationStatus`) — trust is one cross-cutting
concept, never duplicated (`14-trust-model.md`).
"""

from __future__ import annotations

from enum import StrEnum


class TrustSignal(StrEnum):
    """An external signal that can move an item between verification states.

    Signals are the *inputs* to verification; the `VerificationPolicy` maps each
    to a target `VerificationStatus` and validates the transition is allowed.
    """

    HUMAN_VERIFIED = "human_verified"
    CORROBORATED = "corroborated"
    CONFLICTING_EVIDENCE = "conflicting_evidence"
    CONTRADICTED_BY_SOURCE = "contradicted_by_source"
    RETRACTED = "retracted"
    REOPENED = "reopened"


class ContradictionKind(StrEnum):
    """Why two assertions conflict (`14-trust-model.md` — contradiction detection)."""

    VALUE_MISMATCH = "value_mismatch"  # same subject+predicate, different object
    POLARITY_CONFLICT = "polarity_conflict"  # one asserts, one negates the same fact
