"""Integration tests for the SemanticQueryEngine service."""

from __future__ import annotations

import pytest

from scp.query import RetrievalStrategy, SemanticQueryEngine
from scp.query.errors import EmptyQueryError


async def test_reindex_counts_all_entities(
    tech_corpus: tuple[SemanticQueryEngine, dict[str, str]],
) -> None:
    engine, ids = tech_corpus
    assert await engine.reindex() == len(ids)


async def test_search_returns_strategy_and_explainable_components(
    tech_corpus: tuple[SemanticQueryEngine, dict[str, str]],
) -> None:
    engine, _ = tech_corpus
    result = await engine.search("python programming", top_k=3)
    assert result.strategy is RetrievalStrategy.HYBRID
    assert result.results, "expected at least one hit"
    assert set(result.results[0].components) == {"semantic", "graph", "trust"}


async def test_empty_query_raises(
    tech_corpus: tuple[SemanticQueryEngine, dict[str, str]],
) -> None:
    engine, _ = tech_corpus
    with pytest.raises(EmptyQueryError):
        await engine.search("!!! ???")


async def test_hybrid_surfaces_graph_adjacent_entity_that_vector_only_misses(
    tech_corpus: tuple[SemanticQueryEngine, dict[str, str]],
) -> None:
    engine, ids = tech_corpus
    gold = ids["guido van rossum"]

    baseline = await engine.search(
        "python programming", top_k=5, strategy=RetrievalStrategy.VECTOR_ONLY
    )
    hybrid = await engine.search("python programming", top_k=5, expand_hops=1)

    baseline_ids = {r.entity_id for r in baseline.results}
    hybrid_ids = {r.entity_id for r in hybrid.results}
    assert gold not in baseline_ids  # lexically invisible to vector-only
    assert gold in hybrid_ids  # graph expansion surfaces it


async def test_remove_entity_drops_it_from_results(
    tech_corpus: tuple[SemanticQueryEngine, dict[str, str]],
) -> None:
    engine, ids = tech_corpus
    python = ids["python programming language"]
    assert await engine.remove_entity(python) is True
    result = await engine.search("python programming", top_k=5)
    assert python not in {r.entity_id for r in result.results}
