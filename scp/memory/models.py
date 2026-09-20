"""Pydantic models for the Memory Core.

Trust metadata and temporal context are **inseparable** parts of every
`MemoryRecord` — never bolted on later (`14-trust-model.md`, `99` §8).
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from .enums import (
    LifecycleState,
    MemoryType,
    ProvenanceOperation,
    SourceType,
    VerificationStatus,
)


class Source(BaseModel):
    """Where a memory originated."""

    model_config = ConfigDict(frozen=True)

    type: SourceType
    identifier: str | None = None
    # Reliability weighting is owned by the Trust Engine (Phase 4); optional now.
    reliability: float | None = Field(default=None, ge=0.0, le=1.0)


class ProvenanceEntry(BaseModel):
    """One immutable step in a memory's derivation chain."""

    model_config = ConfigDict(frozen=True)

    operation: ProvenanceOperation
    timestamp: datetime
    detail: str | None = None
    parent_ids: tuple[str, ...] = ()


class TemporalContext(BaseModel):
    """When a memory was asserted and over what validity window."""

    created_at: datetime
    last_accessed: datetime
    valid_from: datetime | None = None
    valid_to: datetime | None = None


class TrustMetadata(BaseModel):
    """Trust primitives carried on every memory (`14-trust-model.md`).

    `confidence` may be a placeholder default until the Trust Engine (Phase 4)
    computes real scores — Memory Core stores and carries it (`11` boundaries).
    """

    source: Source
    confidence: float = Field(ge=0.0, le=1.0)
    verification_status: VerificationStatus = VerificationStatus.UNVERIFIED
    provenance: tuple[ProvenanceEntry, ...] = ()


class MemoryRecord(BaseModel):
    """A single stored memory with its trust and temporal context.

    Content is a string payload for Phase 1; structured payloads are deferred.
    """

    id: str
    type: MemoryType
    content: str
    lifecycle_state: LifecycleState = LifecycleState.ACTIVE
    trust: TrustMetadata
    temporal: TemporalContext
