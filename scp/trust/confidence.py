"""Confidence model — maps ingest signals to an item's confidence (`14-trust-model.md`).

Confidence is the *assertion's own certainty*, distinct from source reliability.
At ingest the only signals are the source kind and any verification state, so the
model is a documented per-`SourceType` base, adjusted by verification. This
**replaces the flat 0.5 placeholder** with a real, varied, explainable value.
"""

from __future__ import annotations

from scp.memory import Source, SourceType, VerificationStatus

from .scoring import clamp01

# Documented intrinsic certainty per source kind.
BASE_CONFIDENCE: dict[SourceType, float] = {
    SourceType.USER: 0.70,
    SourceType.TOOL: 0.80,
    SourceType.SYSTEM: 0.75,
    SourceType.AGENT: 0.60,
    SourceType.EXTERNAL: 0.50,
    SourceType.INFERENCE: 0.40,
}

# How a known verification state nudges initial confidence.
_VERIFICATION_ADJUST: dict[VerificationStatus, float] = {
    VerificationStatus.VERIFIED: 1.15,
    VerificationStatus.UNVERIFIED: 1.00,
    VerificationStatus.DISPUTED: 0.60,
    VerificationStatus.CONTRADICTED: 0.20,
}


class ConfidenceModel:
    """Computes initial confidence for a newly ingested item."""

    def __init__(self, *, base: dict[SourceType, float] | None = None) -> None:
        self._base = dict(base or BASE_CONFIDENCE)

    def initial(
        self,
        source: Source,
        verification_status: VerificationStatus = VerificationStatus.UNVERIFIED,
    ) -> float:
        """Initial confidence in [0, 1] for ``source`` at ``verification_status``.

        Unknown source kinds fall back to a neutral 0.5 base.
        """
        base = self._base.get(source.type, 0.5)
        return clamp01(base * _VERIFICATION_ADJUST[verification_status])
