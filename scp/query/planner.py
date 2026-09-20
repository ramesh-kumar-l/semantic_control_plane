"""Query planning — choose a retrieval strategy and resolve execution parameters.

Planning is rule-based and cheap for now: it selects the strategy and sizes the
seed set. Cost-based planning (using index statistics) is a documented future
extension (`adr/ADR-004-semantic-query-engine.md`). The chosen `strategy` later
masks ranking weights in the engine (e.g. GRAPH_ONLY zeroes the semantic weight).
"""

from __future__ import annotations

from .enums import RetrievalStrategy
from .models import QueryPlan

# Seeds are over-fetched relative to top_k so graph expansion has anchors to grow
# from; the resulting candidate set is re-ranked back down to top_k.
DEFAULT_SEED_MULTIPLIER = 3
MIN_SEED_K = 5


def plan(
    *,
    top_k: int,
    expand_hops: int,
    decay: float,
    strategy: RetrievalStrategy | None = None,
    seed_multiplier: int = DEFAULT_SEED_MULTIPLIER,
) -> QueryPlan:
    """Resolve a `QueryPlan` from request parameters.

    Without an explicit `strategy`: HYBRID when expansion is requested
    (`expand_hops > 0`), otherwise VECTOR_ONLY. GRAPH_ONLY is opt-in.
    """
    if strategy is None:
        strategy = RetrievalStrategy.HYBRID if expand_hops > 0 else RetrievalStrategy.VECTOR_ONLY

    # VECTOR_ONLY never expands; GRAPH_ONLY/HYBRID need at least one hop.
    effective_hops = 0 if strategy is RetrievalStrategy.VECTOR_ONLY else max(expand_hops, 1)
    seed_k = max(MIN_SEED_K, top_k * seed_multiplier)

    return QueryPlan(
        strategy=strategy,
        top_k=top_k,
        seed_k=seed_k,
        expand_hops=effective_hops,
        decay=decay,
    )
