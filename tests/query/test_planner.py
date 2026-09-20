"""Unit tests for the rule-based query planner."""

from __future__ import annotations

from scp.query import RetrievalStrategy
from scp.query.planner import plan


def test_default_strategy_is_hybrid_when_expanding() -> None:
    p = plan(top_k=10, expand_hops=1, decay=0.5)
    assert p.strategy is RetrievalStrategy.HYBRID
    assert p.expand_hops == 1


def test_default_strategy_is_vector_only_without_expansion() -> None:
    p = plan(top_k=10, expand_hops=0, decay=0.5)
    assert p.strategy is RetrievalStrategy.VECTOR_ONLY
    assert p.expand_hops == 0


def test_vector_only_override_forces_no_expansion() -> None:
    p = plan(top_k=10, expand_hops=3, decay=0.5, strategy=RetrievalStrategy.VECTOR_ONLY)
    assert p.expand_hops == 0


def test_graph_only_override_forces_at_least_one_hop() -> None:
    p = plan(top_k=10, expand_hops=0, decay=0.5, strategy=RetrievalStrategy.GRAPH_ONLY)
    assert p.strategy is RetrievalStrategy.GRAPH_ONLY
    assert p.expand_hops == 1


def test_seed_k_overfetches_relative_to_top_k() -> None:
    assert plan(top_k=1, expand_hops=1, decay=0.5).seed_k == 5  # MIN_SEED_K floor
    assert plan(top_k=10, expand_hops=1, decay=0.5).seed_k == 30  # top_k * 3
