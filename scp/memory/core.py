"""`MemoryCore` — the public service API for Phase 1 Memory Core.

Owns storage, retrieval, and lifecycle orchestration. Depends only on the
`MemoryStore` port (`store.py`), so the backend is swappable (ADR-002).
Pure lifecycle math lives in `lifecycle.py`; this module wires it to persistence.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable, Sequence
from datetime import UTC, datetime

from . import lifecycle
from .enums import (
    LifecycleState,
    MemoryType,
    ProvenanceOperation,
    SourceType,
    VerificationStatus,
)
from .errors import ConsolidationError, MemoryNotFoundError
from .models import (
    MemoryRecord,
    ProvenanceEntry,
    Source,
    TemporalContext,
    TrustMetadata,
)
from .store import MemoryQuery, MemoryStore

# Fallback confidence when neither an explicit value nor a confidence model is given.
DEFAULT_CONFIDENCE = 0.5

# A source-aware confidence model (the Trust Engine's `initial_confidence`, Phase 4).
ConfidenceModel = Callable[[Source, VerificationStatus], float]


def _utcnow() -> datetime:
    return datetime.now(UTC)


class MemoryCore:
    """High-level Memory Core API over a pluggable `MemoryStore`.

    `clock` and `id_factory` are injectable for deterministic behaviour/tests
    (NFR: deterministic — `02-system-architecture.md`).
    """

    def __init__(
        self,
        store: MemoryStore,
        *,
        clock: Callable[[], datetime] = _utcnow,
        id_factory: Callable[[], str] = lambda: uuid.uuid4().hex,
        default_confidence: float = DEFAULT_CONFIDENCE,
        confidence_model: ConfidenceModel | None = None,
    ) -> None:
        self._store = store
        self._clock = clock
        self._new_id = id_factory
        self._default_confidence = default_confidence
        # When wired, the Trust Engine computes real source-aware confidence,
        # replacing the flat `default_confidence` placeholder (`14-trust-model.md`).
        self._confidence_model = confidence_model

    async def close(self) -> None:
        """Release the underlying store's resources."""
        await self._store.close()

    async def store(
        self,
        content: str,
        *,
        memory_type: MemoryType,
        source_type: SourceType,
        source_identifier: str | None = None,
        confidence: float | None = None,
        verification_status: VerificationStatus = VerificationStatus.UNVERIFIED,
        valid_from: datetime | None = None,
        valid_to: datetime | None = None,
    ) -> MemoryRecord:
        """Ingest and persist a new memory with full trust metadata attached."""
        now = self._clock()
        source = Source(type=source_type, identifier=source_identifier)
        ingest = ProvenanceEntry(operation=ProvenanceOperation.INGEST, timestamp=now)
        trust = TrustMetadata(
            source=source,
            confidence=self._resolve_confidence(source, confidence, verification_status),
            verification_status=verification_status,
            provenance=(ingest,),
        )
        temporal = TemporalContext(
            created_at=now,
            last_accessed=now,
            valid_from=valid_from,
            valid_to=valid_to,
        )
        record = MemoryRecord(
            id=self._new_id(),
            type=memory_type,
            content=content,
            lifecycle_state=LifecycleState.ACTIVE,
            trust=trust,
            temporal=temporal,
        )
        await self._store.add(record)
        return record

    async def get(self, memory_id: str) -> MemoryRecord:
        """Return a record, updating last-accessed. Raises if not found."""
        record = await self._require(memory_id)
        touched = record.model_copy(
            update={"temporal": record.temporal.model_copy(update={"last_accessed": self._clock()})}
        )
        await self._store.update(touched)
        return touched

    async def query(
        self,
        *,
        memory_type: MemoryType | None = None,
        lifecycle_state: LifecycleState | None = None,
        newest_first: bool = True,
        limit: int = 100,
        offset: int = 0,
    ) -> list[MemoryRecord]:
        """Retrieve records by type / lifecycle state / recency."""
        return await self._store.query(
            MemoryQuery(
                type=memory_type,
                lifecycle_state=lifecycle_state,
                newest_first=newest_first,
                limit=limit,
                offset=offset,
            )
        )

    async def compress(self, memory_id: str) -> MemoryRecord:
        """Compress an aged memory, retaining trust fields and essence."""
        record = await self._require(memory_id)
        compressed = lifecycle.compress(record, now=self._clock())
        await self._store.update(compressed)
        return compressed

    async def archive(self, memory_id: str) -> MemoryRecord:
        """Move a memory to ARCHIVED."""
        return await self._transition(memory_id, LifecycleState.ARCHIVED)

    async def expire(self, memory_id: str) -> MemoryRecord:
        """Move a memory to EXPIRED (terminal)."""
        return await self._transition(memory_id, LifecycleState.EXPIRED)

    async def consolidate(
        self, memory_ids: Sequence[str], *, detail: str | None = None
    ) -> MemoryRecord:
        """Merge memories into one CONSOLIDATED record; archive the originals."""
        if len(memory_ids) < 2:
            raise ConsolidationError("consolidation requires at least two ids")
        now = self._clock()
        records = [await self._require(mid) for mid in memory_ids]
        merged = lifecycle.consolidate(records, new_id=self._new_id(), now=now, detail=detail)
        await self._store.add(merged)
        for record in records:
            superseded = lifecycle.transition(
                record,
                LifecycleState.ARCHIVED,
                now=now,
                detail=f"superseded by {merged.id}",
            )
            await self._store.update(superseded)
        return merged

    def _resolve_confidence(
        self, source: Source, confidence: float | None, verification_status: VerificationStatus
    ) -> float:
        """Explicit value wins; else the wired confidence model; else the fallback."""
        if confidence is not None:
            return confidence
        if self._confidence_model is not None:
            return self._confidence_model(source, verification_status)
        return self._default_confidence

    async def _transition(self, memory_id: str, target: LifecycleState) -> MemoryRecord:
        record = await self._require(memory_id)
        moved = lifecycle.transition(record, target, now=self._clock())
        await self._store.update(moved)
        return moved

    async def _require(self, memory_id: str) -> MemoryRecord:
        record = await self._store.get(memory_id)
        if record is None:
            raise MemoryNotFoundError(memory_id)
        return record
