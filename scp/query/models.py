"""Pydantic models for the Semantic Query Engine.

Results are **explainable**: every `ScoredResult` carries the raw signal values
that produced its score (`14-trust-model.md` explainability requirement).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from .enums import RetrievalStrategy


class RankingWeights(BaseModel):
    """Relative weight of each ranking signal. Defaults favour semantics, with
    graph proximity as a strong secondary signal and trust as a tie-breaker.
    """

    model_config = ConfigDict(frozen=True)

    semantic: float = Field(default=0.6, ge=0.0)
    graph: float = Field(default=0.3, ge=0.0)
    trust: float = Field(default=0.1, ge=0.0)


class QueryPlan(BaseModel):
    """The resolved execution plan for a query (chosen by the planner)."""

    model_config = ConfigDict(frozen=True)

    strategy: RetrievalStrategy
    top_k: int = Field(ge=1)
    seed_k: int = Field(ge=1)
    expand_hops: int = Field(ge=0)
    decay: float = Field(gt=0.0, le=1.0)


class ScoredResult(BaseModel):
    """One ranked entity with its final score and the signals behind it."""

    entity_id: str
    name: str
    score: float
    hops: int
    components: dict[str, float]
    memory_refs: tuple[str, ...] = ()


class RetrievalResult(BaseModel):
    """The outcome of a semantic query."""

    query: str
    strategy: RetrievalStrategy
    results: list[ScoredResult]
