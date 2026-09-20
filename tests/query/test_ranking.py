"""Unit tests for trust-aware, explainable ranking."""

from __future__ import annotations

import pytest

from scp.graph import EntityType, KnowledgeGraph
from scp.memory import SourceType, VerificationStatus
from scp.query import RankingWeights, trust_score
from scp.query.ranking import Candidate, rank


async def _entity(kg: KnowledgeGraph, name: str, **kwargs: object) -> object:
    return await kg.add_entity(
        name, entity_type=EntityType.CONCEPT, source_type=SourceType.USER, **kwargs
    )


async def test_trust_score_orders_by_verification(kg: KnowledgeGraph) -> None:
    verified = await _entity(
        kg, "v", confidence=0.8, verification_status=VerificationStatus.VERIFIED
    )
    unverified = await _entity(
        kg, "u", confidence=0.8, verification_status=VerificationStatus.UNVERIFIED
    )
    contradicted = await _entity(
        kg, "c", confidence=0.8, verification_status=VerificationStatus.CONTRADICTED
    )
    assert trust_score(verified) > trust_score(unverified) > trust_score(contradicted)
    assert trust_score(verified) == pytest.approx(0.8)


async def test_rank_orders_by_weighted_score_and_records_components(kg: KnowledgeGraph) -> None:
    strong = await _entity(kg, "strong")
    weak = await _entity(kg, "weak")
    weights = RankingWeights(semantic=0.6, graph=0.3, trust=0.1)
    ranked = rank(
        [
            Candidate(entity=weak, semantic=0.1),
            Candidate(entity=strong, semantic=0.9),
        ],
        weights,
        top_k=10,
    )
    assert [r.name for r in ranked] == ["strong", "weak"]
    assert set(ranked[0].components) == {"semantic", "graph", "trust"}
    assert ranked[0].components["semantic"] == pytest.approx(0.9)


async def test_graph_proximity_can_outrank_a_weak_lexical_hit(kg: KnowledgeGraph) -> None:
    lexical = await _entity(kg, "lexical")
    adjacent = await _entity(kg, "adjacent")
    weights = RankingWeights(semantic=0.6, graph=0.3, trust=0.1)
    ranked = rank(
        [
            Candidate(entity=lexical, semantic=0.05),
            Candidate(entity=adjacent, semantic=0.0, graph=0.8, hops=1),
        ],
        weights,
        top_k=10,
    )
    assert ranked[0].name == "adjacent"


async def test_rank_truncates_to_top_k(kg: KnowledgeGraph) -> None:
    candidates = [Candidate(entity=await _entity(kg, f"e{i}"), semantic=i / 10) for i in range(5)]
    assert len(rank(candidates, RankingWeights(), top_k=2)) == 2
