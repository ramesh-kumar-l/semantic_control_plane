"""Semantic Query Engine (Phase 3) — hybrid vector + graph retrieval, trust-aware
ranking, and query planning over the Knowledge Graph.

Builds on Phase 2 traversal and Phase 1 trust primitives
(`adr/ADR-004-semantic-query-engine.md`). Public API surface
(`02-system-architecture.md` boundary; protected by `99` §3).
"""

from __future__ import annotations

from .backends import InMemoryVectorStore
from .embeddings import Embedder, HashingEmbedder
from .engine import SemanticQueryEngine
from .enums import RetrievalStrategy
from .errors import EmptyQueryError, SemanticQueryError
from .models import QueryPlan, RankingWeights, RetrievalResult, ScoredResult
from .ranking import trust_score
from .vector_store import VectorMatch, VectorStore

__all__ = [
    # Service
    "SemanticQueryEngine",
    # Embeddings
    "Embedder",
    "HashingEmbedder",
    # Vector index port + adapter
    "VectorStore",
    "VectorMatch",
    "InMemoryVectorStore",
    # Models
    "RankingWeights",
    "QueryPlan",
    "ScoredResult",
    "RetrievalResult",
    # Ranking
    "trust_score",
    # Enums
    "RetrievalStrategy",
    # Errors
    "SemanticQueryError",
    "EmptyQueryError",
]
