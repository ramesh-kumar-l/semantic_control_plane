"""Unit tests for the pure lifecycle logic (transitions, consolidate, compress)."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from scp.memory import (
    ConsolidationError,
    InvalidLifecycleTransitionError,
    LifecycleState,
    MemoryRecord,
    MemoryType,
    ProvenanceOperation,
    Source,
    SourceType,
    TemporalContext,
    TrustMetadata,
    lifecycle,
)

_NOW = datetime(2026, 6, 20, tzinfo=UTC)


def _record(rid: str, content: str, confidence: float) -> MemoryRecord:
    return MemoryRecord(
        id=rid,
        type=MemoryType.SEMANTIC,
        content=content,
        trust=TrustMetadata(source=Source(type=SourceType.USER), confidence=confidence),
        temporal=TemporalContext(created_at=_NOW, last_accessed=_NOW),
    )


def test_transition_records_provenance() -> None:
    record = _record("mem-1", "x", 0.5)
    archived = lifecycle.transition(record, LifecycleState.ARCHIVED, now=_NOW)
    assert archived.lifecycle_state is LifecycleState.ARCHIVED
    assert archived.trust.provenance[-1].operation is ProvenanceOperation.ARCHIVE


def test_expired_is_terminal() -> None:
    record = _record("mem-1", "x", 0.5)
    expired = lifecycle.transition(record, LifecycleState.EXPIRED, now=_NOW)
    with pytest.raises(InvalidLifecycleTransitionError):
        lifecycle.transition(expired, LifecycleState.ARCHIVED, now=_NOW)


def test_compress_truncates_long_content() -> None:
    record = _record("mem-1", "a" * 500, 0.5)
    compressed = lifecycle.compress(record, now=_NOW, max_length=100)
    assert compressed.lifecycle_state is LifecycleState.COMPRESSED
    assert compressed.content.endswith("…[compressed]")
    assert len(compressed.content) < 500


def test_compress_keeps_short_content() -> None:
    record = _record("mem-1", "short", 0.5)
    compressed = lifecycle.compress(record, now=_NOW, max_length=100)
    assert compressed.content == "short"


def test_consolidate_merges_and_picks_primary() -> None:
    low = _record("mem-1", "fact A", 0.3)
    high = _record("mem-2", "fact B", 0.9)
    merged = lifecycle.consolidate([low, high], new_id="mem-3", now=_NOW)
    assert merged.id == "mem-3"
    assert merged.lifecycle_state is LifecycleState.CONSOLIDATED
    assert merged.trust.confidence == 0.9
    assert "fact A" in merged.content and "fact B" in merged.content
    last = merged.trust.provenance[-1]
    assert last.operation is ProvenanceOperation.CONSOLIDATE
    assert last.parent_ids == ("mem-1", "mem-2")


def test_consolidate_deduplicates_identical_content() -> None:
    a = _record("mem-1", "same", 0.5)
    b = _record("mem-2", "same", 0.6)
    merged = lifecycle.consolidate([a, b], new_id="mem-3", now=_NOW)
    assert merged.content == "same"


def test_consolidate_requires_two() -> None:
    with pytest.raises(ConsolidationError):
        lifecycle.consolidate([_record("mem-1", "x", 0.5)], new_id="m", now=_NOW)
