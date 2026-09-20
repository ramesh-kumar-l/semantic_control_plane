"""Pydantic models and the structural port for the Trust Engine.

Every score is **explainable** and **reproducible**: a `TrustAssessment` carries
its component signals and the weights used, so the final number is fully
reconstructable from its inputs (`14-trust-model.md` explainability requirement,
`99` §7).
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field, model_validator

# Trust primitives are reused from Memory Core (one cross-cutting concept).
from scp.memory import Source, TemporalContext, TrustMetadata

from .enums import ContradictionKind


@runtime_checkable
class TrustBearing(Protocol):
    """Anything carrying first-class trust + temporal context.

    `MemoryRecord`, `Entity`, and `Relationship` all satisfy this structurally,
    so the Trust Engine assesses any of them without importing their concrete
    types (respects module boundaries, `02-system-architecture.md`).
    """

    trust: TrustMetadata
    temporal: TemporalContext


class TrustWeights(BaseModel):
    """Relative weights of the three additive trust signals (before verification).

    Need not sum to 1 — scoring normalizes by their total — but must be positive.
    """

    model_config = ConfigDict(frozen=True)

    reliability: float = Field(default=0.35, ge=0.0)
    confidence: float = Field(default=0.40, ge=0.0)
    recency: float = Field(default=0.25, ge=0.0)

    @model_validator(mode="after")
    def _non_zero_total(self) -> TrustWeights:
        if self.reliability + self.confidence + self.recency <= 0.0:
            raise ValueError("trust weights must have a positive total")
        return self


class TrustComponents(BaseModel):
    """The normalized [0, 1] signals that produced a trust score."""

    model_config = ConfigDict(frozen=True)

    reliability: float = Field(ge=0.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)
    recency: float = Field(ge=0.0, le=1.0)
    verification_factor: float = Field(ge=0.0, le=1.0)


class TrustAssessment(BaseModel):
    """An explainable, reproducible trust score for one item.

    ``score = base * verification_factor`` where ``base`` is the weight-normalized
    sum of {reliability, confidence, recency}. All inputs are retained.
    """

    model_config = ConfigDict(frozen=True)

    score: float = Field(ge=0.0, le=1.0)
    base: float = Field(ge=0.0, le=1.0)
    components: TrustComponents
    weights: TrustWeights
    explanation: str


class Claim(BaseModel):
    """A normalized assertion used for contradiction detection.

    A fact is identified by (subject, predicate); `object` is its asserted value
    and `negated` flips polarity. `source` lets the engine weight conflicts by
    source reliability during reconciliation.
    """

    model_config = ConfigDict(frozen=True)

    id: str
    subject: str
    predicate: str
    object: str
    negated: bool = False
    source: Source | None = None


class Contradiction(BaseModel):
    """A detected conflict between two claims over the same (subject, predicate)."""

    model_config = ConfigDict(frozen=True)

    kind: ContradictionKind
    subject: str
    predicate: str
    claim_ids: tuple[str, str]
    detail: str
