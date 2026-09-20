"""Explainable, trust-aware ranking for the Semantic Query Engine.

A candidate's final score is a weighted sum of three normalized signals:

    score = w_semantic * semantic + w_graph * graph + w_trust * trust

- **semantic** — cosine similarity of the entity's text to the query [0, 1].
- **graph**    — proximity to a lexical seed: ``seed_similarity * decay**hops`` [0, 1].
- **trust**    — derived from the entity's first-class trust metadata (below).

Every signal is preserved on the result so the score is reconstructable
(`14-trust-model.md` explainability requirement, `99` §7).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from scp.graph import Entity
from scp.memory import VerificationStatus

from .models import RankingWeights, ScoredResult

# How verification status adjusts the confidence-based trust signal.
_VERIFICATION_FACTOR: dict[VerificationStatus, float] = {
    VerificationStatus.VERIFIED: 1.0,
    VerificationStatus.UNVERIFIED: 0.7,
    VerificationStatus.DISPUTED: 0.4,
    VerificationStatus.CONTRADICTED: 0.1,
}


def trust_score(entity: Entity) -> float:
    """Map an entity's trust metadata to a [0, 1] signal.

    Confidence is scaled by a verification factor so that verified facts
    outrank unverified ones and contradicted facts are strongly demoted. The
    mapping is explicit and documented (no opaque trust, `14-trust-model.md`).
    """
    factor = _VERIFICATION_FACTOR[entity.trust.verification_status]
    return max(0.0, min(1.0, entity.trust.confidence * factor))


@dataclass
class Candidate:
    """A retrieval candidate with its raw signals, before final scoring."""

    entity: Entity
    semantic: float = 0.0
    graph: float = 0.0
    hops: int = 0
    _trust: float = field(default=0.0, init=False)


def rank(candidates: list[Candidate], weights: RankingWeights, *, top_k: int) -> list[ScoredResult]:
    """Score and order candidates, returning the top `top_k` (deterministic)."""
    results: list[ScoredResult] = []
    for candidate in candidates:
        trust = trust_score(candidate.entity)
        score = (
            weights.semantic * candidate.semantic
            + weights.graph * candidate.graph
            + weights.trust * trust
        )
        results.append(
            ScoredResult(
                entity_id=candidate.entity.id,
                name=candidate.entity.name,
                score=score,
                hops=candidate.hops,
                components={
                    "semantic": candidate.semantic,
                    "graph": candidate.graph,
                    "trust": trust,
                },
                memory_refs=candidate.entity.memory_refs,
            )
        )
    # Highest score first; ties broken by ascending id (deterministic).
    results.sort(key=lambda r: (-r.score, r.entity_id))
    return results[:top_k]
