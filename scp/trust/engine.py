"""`TrustEngine` — the public service API for Phase 4 Trust Engine.

Ties together the source registry, confidence model, scoring math, verification
policy, and contradiction detector. The engine is **pure and synchronous**: it
performs no I/O and never reaches into Memory/Graph storage (it reads the trust
primitives those modules already carry), so every result is deterministic and
reproducible (`02-system-architecture.md`, `99` §7).
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from datetime import UTC, datetime

from scp.memory import Source, VerificationStatus

from . import scoring
from .confidence import ConfidenceModel
from .contradiction import ContradictionDetector
from .enums import TrustSignal
from .models import Claim, Contradiction, TrustAssessment, TrustBearing, TrustWeights
from .registry import SourceRegistry
from .verification import VerificationPolicy

# Severity ordering used when reconciling: a worse status wins.
_SEVERITY: dict[VerificationStatus, int] = {
    VerificationStatus.VERIFIED: 0,
    VerificationStatus.UNVERIFIED: 1,
    VerificationStatus.DISPUTED: 2,
    VerificationStatus.CONTRADICTED: 3,
}


def _utcnow() -> datetime:
    return datetime.now(UTC)


class TrustEngine:
    """Authoritative, explainable trust computation over trust-bearing items."""

    def __init__(
        self,
        *,
        registry: SourceRegistry | None = None,
        confidence_model: ConfidenceModel | None = None,
        policy: VerificationPolicy | None = None,
        detector: ContradictionDetector | None = None,
        weights: TrustWeights | None = None,
        half_life_days: float = scoring.HALF_LIFE_DAYS,
        clock: Callable[[], datetime] = _utcnow,
    ) -> None:
        self._registry = registry or SourceRegistry()
        self._confidence = confidence_model or ConfidenceModel()
        self._policy = policy or VerificationPolicy()
        self._detector = detector or ContradictionDetector()
        self._weights = weights or TrustWeights()
        self._half_life = half_life_days
        self._clock = clock

    @property
    def registry(self) -> SourceRegistry:
        """The source-reliability registry (for registering known origins)."""
        return self._registry

    # --- Confidence (replaces the 0.5 placeholder) ------------------------
    def initial_confidence(
        self,
        source: Source,
        verification_status: VerificationStatus = VerificationStatus.UNVERIFIED,
    ) -> float:
        """Real, source-aware initial confidence; injectable into Memory/Graph."""
        return self._confidence.initial(source, verification_status)

    # --- Trust scoring ----------------------------------------------------
    def assess(self, item: TrustBearing, *, now: datetime | None = None) -> TrustAssessment:
        """Compute an explainable trust score for any trust-bearing item."""
        moment = now if now is not None else self._clock()
        return scoring.assess(
            reliability=self._registry.reliability(item.trust.source),
            confidence=item.trust.confidence,
            created_at=item.temporal.created_at,
            now=moment,
            verification_status=item.trust.verification_status,
            weights=self._weights,
            half_life_days=self._half_life,
        )

    # --- Verification -----------------------------------------------------
    def verify(self, current: VerificationStatus, signal: TrustSignal) -> VerificationStatus:
        """Apply a verification signal under the documented policy."""
        return self._policy.apply(current, signal)

    # --- Contradiction detection & reconciliation -------------------------
    def detect_contradictions(self, claims: Sequence[Claim]) -> list[Contradiction]:
        """Return conflicting claim pairs over the same (subject, predicate)."""
        return self._detector.detect(claims)

    def reconcile(self, claims: Sequence[Claim]) -> dict[str, VerificationStatus]:
        """Recommend verification statuses from detected contradictions.

        For each conflict, the lower-reliability claim is recommended
        CONTRADICTED and the other DISPUTED; equal reliability disputes both. A
        claim involved in several conflicts takes the most severe recommendation.
        Claims with no conflict are absent from the result.
        """
        by_id = {claim.id: claim for claim in claims}
        recommendations: dict[str, VerificationStatus] = {}

        def _bump(claim_id: str, status: VerificationStatus) -> None:
            current = recommendations.get(claim_id)
            if current is None or _SEVERITY[status] > _SEVERITY[current]:
                recommendations[claim_id] = status

        for conflict in self._detector.detect(claims):
            a_id, b_id = conflict.claim_ids
            r_a = self._reliability_of(by_id[a_id])
            r_b = self._reliability_of(by_id[b_id])
            if r_a > r_b:
                _bump(a_id, VerificationStatus.DISPUTED)
                _bump(b_id, VerificationStatus.CONTRADICTED)
            elif r_b > r_a:
                _bump(b_id, VerificationStatus.DISPUTED)
                _bump(a_id, VerificationStatus.CONTRADICTED)
            else:
                _bump(a_id, VerificationStatus.DISPUTED)
                _bump(b_id, VerificationStatus.DISPUTED)
        return recommendations

    def _reliability_of(self, claim: Claim) -> float:
        """Source reliability for a claim; neutral 0.5 when no source is attached."""
        if claim.source is None:
            return 0.5
        return self._registry.reliability(claim.source)
