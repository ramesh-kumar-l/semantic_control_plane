"""Enumerations for the Semantic Query Engine domain.

Kept separate from models so types stay small and single-responsibility
(`99-development-rules.md` §11).
"""

from __future__ import annotations

from enum import StrEnum


class RetrievalStrategy(StrEnum):
    """How a query is answered.

    VECTOR_ONLY — semantic similarity only; no graph expansion (the baseline).
    GRAPH_ONLY  — expand from lexical seeds and rank by graph proximity + trust,
                  ignoring the semantic signal.
    HYBRID      — fuse semantic + graph proximity + trust (the default).
    """

    VECTOR_ONLY = "vector_only"
    GRAPH_ONLY = "graph_only"
    HYBRID = "hybrid"
