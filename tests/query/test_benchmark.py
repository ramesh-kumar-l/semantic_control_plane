"""Exit-criterion benchmark: hybrid retrieval must beat the vector-only baseline
on a labeled fixture set (`04-roadmap.md` Phase 3 exit, `ADR-004`).

Each query's gold answer is a graph neighbour of a lexical seed but shares no
query words, so vector-only ranking cannot surface it while hybrid can.
"""

from __future__ import annotations

from scp.query import RetrievalStrategy, ScoredResult, SemanticQueryEngine


def _recall_at_k(results: list[ScoredResult], gold: set[str], k: int) -> float:
    retrieved = {r.entity_id for r in results[:k]}
    return len(retrieved & gold) / len(gold)


async def test_hybrid_beats_vector_only_baseline(
    tech_corpus: tuple[SemanticQueryEngine, dict[str, str]],
) -> None:
    engine, ids = tech_corpus
    top_k = 5
    queries = [
        ("python programming", {ids["guido van rossum"]}),
        ("web framework", {ids["object relational mapper"]}),
    ]

    baseline_total = 0.0
    hybrid_total = 0.0
    for text, gold in queries:
        baseline = await engine.search(text, top_k=top_k, strategy=RetrievalStrategy.VECTOR_ONLY)
        hybrid = await engine.search(text, top_k=top_k, expand_hops=1)
        baseline_total += _recall_at_k(baseline.results, gold, top_k)
        hybrid_total += _recall_at_k(hybrid.results, gold, top_k)

    baseline_recall = baseline_total / len(queries)
    hybrid_recall = hybrid_total / len(queries)

    assert hybrid_recall > baseline_recall, (
        f"hybrid ({hybrid_recall:.2f}) did not beat baseline ({baseline_recall:.2f})"
    )
    # The fixture is constructed so hybrid recalls every gold answer.
    assert hybrid_recall == 1.0
