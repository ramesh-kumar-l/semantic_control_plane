"""Pure trust-scoring math — deterministic and reproducible (`99` §7).

The model is intentionally transparent rather than learned:

    base  = (w_r*reliability + w_c*confidence + w_t*recency) / (w_r + w_c + w_t)
    score = base * verification_factor

`base` is a weight-normalized blend of the three positive signals; verification
acts as a multiplicative *gate* so a contradicted item is strongly demoted no
matter how reliable its source. This generalizes the Phase 3 ranking stopgap
(`confidence * verification_factor`) into a documented multi-signal score.
"""

from __future__ import annotations

from datetime import datetime

from scp.memory import VerificationStatus

from .models import TrustAssessment, TrustComponents, TrustWeights

# Default age at which recency halves. Tunable per engine; documented, not magic.
HALF_LIFE_DAYS = 180.0

# How verification status gates trust (consistent with Phase 3 ranking).
_VERIFICATION_FACTOR: dict[VerificationStatus, float] = {
    VerificationStatus.VERIFIED: 1.0,
    VerificationStatus.UNVERIFIED: 0.7,
    VerificationStatus.DISPUTED: 0.4,
    VerificationStatus.CONTRADICTED: 0.1,
}


def clamp01(value: float) -> float:
    """Clamp a value into [0.0, 1.0]."""
    return max(0.0, min(1.0, value))


def verification_factor(status: VerificationStatus) -> float:
    """The multiplicative trust gate for a verification status."""
    return _VERIFICATION_FACTOR[status]


def recency_factor(
    created_at: datetime, now: datetime, *, half_life_days: float = HALF_LIFE_DAYS
) -> float:
    """Exponential freshness decay in (0, 1]; 1.0 for a just-asserted item.

    Future-dated or just-created items get the full 1.0 (no penalty).
    """
    age_days = (now - created_at).total_seconds() / 86_400.0
    if age_days <= 0.0:
        return 1.0
    return clamp01(0.5 ** (age_days / half_life_days))


def assess(
    *,
    reliability: float,
    confidence: float,
    created_at: datetime,
    now: datetime,
    verification_status: VerificationStatus,
    weights: TrustWeights,
    half_life_days: float = HALF_LIFE_DAYS,
) -> TrustAssessment:
    """Compute an explainable `TrustAssessment` from raw signals."""
    reliability = clamp01(reliability)
    confidence = clamp01(confidence)
    recency = recency_factor(created_at, now, half_life_days=half_life_days)
    factor = verification_factor(verification_status)

    total_w = weights.reliability + weights.confidence + weights.recency
    base = clamp01(
        (
            weights.reliability * reliability
            + weights.confidence * confidence
            + weights.recency * recency
        )
        / total_w
    )
    score = clamp01(base * factor)

    explanation = (
        f"trust={score:.3f} = base({base:.3f})"
        f" * verification[{verification_status}]({factor:.2f}); "
        f"base = ({weights.reliability:g}*rel{reliability:.2f} + "
        f"{weights.confidence:g}*conf{confidence:.2f} + "
        f"{weights.recency:g}*rec{recency:.2f}) / {total_w:g}"
    )
    return TrustAssessment(
        score=score,
        base=base,
        components=TrustComponents(
            reliability=reliability,
            confidence=confidence,
            recency=recency,
            verification_factor=factor,
        ),
        weights=weights,
        explanation=explanation,
    )
