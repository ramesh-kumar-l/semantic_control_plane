"""Pure lifecycle logic for memories: transitions, consolidation, compression.

These functions are side-effect free (no I/O) so they are trivially testable.
The `MemoryCore` service orchestrates persistence around them.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from .enums import LifecycleState, ProvenanceOperation
from .errors import ConsolidationError, InvalidLifecycleTransitionError
from .models import MemoryRecord, ProvenanceEntry, TemporalContext, TrustMetadata

# Allowed lifecycle transitions (`11-memory-model.md`). EXPIRED is terminal.
ALLOWED_TRANSITIONS: dict[LifecycleState, frozenset[LifecycleState]] = {
    LifecycleState.ACTIVE: frozenset(
        {
            LifecycleState.CONSOLIDATED,
            LifecycleState.COMPRESSED,
            LifecycleState.ARCHIVED,
            LifecycleState.EXPIRED,
        }
    ),
    LifecycleState.CONSOLIDATED: frozenset(
        {LifecycleState.COMPRESSED, LifecycleState.ARCHIVED, LifecycleState.EXPIRED}
    ),
    LifecycleState.COMPRESSED: frozenset({LifecycleState.ARCHIVED, LifecycleState.EXPIRED}),
    LifecycleState.ARCHIVED: frozenset({LifecycleState.EXPIRED}),
    LifecycleState.EXPIRED: frozenset(),
}

# Lifecycle target -> the provenance operation that records the transition.
_TRANSITION_OPERATION: dict[LifecycleState, ProvenanceOperation] = {
    LifecycleState.CONSOLIDATED: ProvenanceOperation.CONSOLIDATE,
    LifecycleState.COMPRESSED: ProvenanceOperation.COMPRESS,
    LifecycleState.ARCHIVED: ProvenanceOperation.ARCHIVE,
    LifecycleState.EXPIRED: ProvenanceOperation.EXPIRE,
}

DEFAULT_COMPRESSION_LENGTH = 280


def assert_transition(current: LifecycleState, target: LifecycleState) -> None:
    """Raise if `current -> target` is not an allowed lifecycle transition."""
    if target not in ALLOWED_TRANSITIONS[current]:
        raise InvalidLifecycleTransitionError(current.value, target.value)


def _append_provenance(
    trust: TrustMetadata,
    operation: ProvenanceOperation,
    now: datetime,
    detail: str | None,
    parent_ids: tuple[str, ...] = (),
) -> TrustMetadata:
    entry = ProvenanceEntry(
        operation=operation, timestamp=now, detail=detail, parent_ids=parent_ids
    )
    return trust.model_copy(update={"provenance": (*trust.provenance, entry)})


def transition(
    record: MemoryRecord,
    target: LifecycleState,
    *,
    now: datetime,
    detail: str | None = None,
) -> MemoryRecord:
    """Return a new record moved to `target`, recording provenance + access time."""
    assert_transition(record.lifecycle_state, target)
    operation = _TRANSITION_OPERATION[target]
    trust = _append_provenance(record.trust, operation, now, detail)
    temporal = record.temporal.model_copy(update={"last_accessed": now})
    return record.model_copy(
        update={"lifecycle_state": target, "trust": trust, "temporal": temporal}
    )


def compress(
    record: MemoryRecord,
    *,
    now: datetime,
    max_length: int = DEFAULT_COMPRESSION_LENGTH,
) -> MemoryRecord:
    """Return a COMPRESSED copy whose content is reduced to a recoverable essence.

    Phase 1 compression is deterministic truncation; semantic summarisation
    (LLM-assisted) is deferred to a later phase.
    """
    assert_transition(record.lifecycle_state, LifecycleState.COMPRESSED)
    if len(record.content) <= max_length:
        content = record.content
    else:
        content = record.content[:max_length].rstrip() + " …[compressed]"
    trust = _append_provenance(
        record.trust,
        ProvenanceOperation.COMPRESS,
        now,
        f"compressed from {len(record.content)} chars",
    )
    temporal = record.temporal.model_copy(update={"last_accessed": now})
    return record.model_copy(
        update={
            "content": content,
            "lifecycle_state": LifecycleState.COMPRESSED,
            "trust": trust,
            "temporal": temporal,
        }
    )


def consolidate(
    records: Sequence[MemoryRecord],
    *,
    new_id: str,
    now: datetime,
    detail: str | None = None,
) -> MemoryRecord:
    """Merge >=2 records into one CONSOLIDATED record, preserving provenance.

    The highest-confidence record is the primary (its source / verification win).
    Distinct contents are merged; the full provenance of all inputs is retained.
    """
    if len(records) < 2:
        raise ConsolidationError("consolidation requires at least two records")

    primary = max(records, key=lambda r: r.trust.confidence)
    parent_ids = tuple(r.id for r in records)

    seen: set[str] = set()
    contents: list[str] = []
    for record in records:
        if record.content not in seen:
            seen.add(record.content)
            contents.append(record.content)
    merged_content = "\n\n".join(contents)

    merged_provenance: tuple[ProvenanceEntry, ...] = ()
    for record in records:
        merged_provenance = (*merged_provenance, *record.trust.provenance)
    merged_provenance = (
        *merged_provenance,
        ProvenanceEntry(
            operation=ProvenanceOperation.CONSOLIDATE,
            timestamp=now,
            detail=detail or f"consolidated {len(records)} memories",
            parent_ids=parent_ids,
        ),
    )

    trust = TrustMetadata(
        source=primary.trust.source,
        confidence=max(r.trust.confidence for r in records),
        verification_status=primary.trust.verification_status,
        provenance=merged_provenance,
    )
    temporal = TemporalContext(created_at=now, last_accessed=now)
    return MemoryRecord(
        id=new_id,
        type=primary.type,
        content=merged_content,
        lifecycle_state=LifecycleState.CONSOLIDATED,
        trust=trust,
        temporal=temporal,
    )
