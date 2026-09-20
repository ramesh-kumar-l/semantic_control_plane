"""Integration tests for the MemoryCore service (over the in-memory store)."""

from __future__ import annotations

import pytest

from scp.memory import (
    InvalidLifecycleTransitionError,
    LifecycleState,
    MemoryCore,
    MemoryNotFoundError,
    MemoryType,
    ProvenanceOperation,
    SourceType,
    VerificationStatus,
)


async def _store_one(core: MemoryCore, content: str = "hello") -> str:
    record = await core.store(
        content,
        memory_type=MemoryType.SEMANTIC,
        source_type=SourceType.USER,
    )
    return record.id


async def test_store_attaches_trust_and_temporal(core: MemoryCore) -> None:
    record = await core.store(
        "the earth orbits the sun",
        memory_type=MemoryType.SEMANTIC,
        source_type=SourceType.AGENT,
        source_identifier="agent-1",
    )
    assert record.id == "mem-1"
    assert record.lifecycle_state is LifecycleState.ACTIVE
    assert record.trust.confidence == 0.5  # placeholder default (Trust Engine TBD)
    assert record.trust.verification_status is VerificationStatus.UNVERIFIED
    assert record.trust.provenance[0].operation is ProvenanceOperation.INGEST
    assert record.trust.source.identifier == "agent-1"
    assert record.temporal.created_at == record.temporal.last_accessed


async def test_get_missing_raises(core: MemoryCore) -> None:
    with pytest.raises(MemoryNotFoundError):
        await core.get("absent")


async def test_get_updates_last_accessed(core: MemoryCore) -> None:
    mid = await _store_one(core)
    fetched = await core.get(mid)
    assert fetched.temporal.last_accessed > fetched.temporal.created_at


async def test_query_filters_by_type(core: MemoryCore) -> None:
    await core.store("a", memory_type=MemoryType.SEMANTIC, source_type=SourceType.USER)
    await core.store("b", memory_type=MemoryType.EPISODIC, source_type=SourceType.USER)
    episodic = await core.query(memory_type=MemoryType.EPISODIC)
    assert [r.content for r in episodic] == ["b"]


async def test_compress_then_archive_then_expire(core: MemoryCore) -> None:
    mid = await _store_one(core, "x" * 400)
    compressed = await core.compress(mid)
    assert compressed.lifecycle_state is LifecycleState.COMPRESSED
    archived = await core.archive(mid)
    assert archived.lifecycle_state is LifecycleState.ARCHIVED
    expired = await core.expire(mid)
    assert expired.lifecycle_state is LifecycleState.EXPIRED
    with pytest.raises(InvalidLifecycleTransitionError):
        await core.archive(mid)


async def test_consolidate_merges_and_archives_sources(core: MemoryCore) -> None:
    a = await core.store("fact A", memory_type=MemoryType.SEMANTIC, source_type=SourceType.USER)
    b = await core.store("fact B", memory_type=MemoryType.SEMANTIC, source_type=SourceType.USER)
    merged = await core.consolidate([a.id, b.id])
    assert merged.lifecycle_state is LifecycleState.CONSOLIDATED
    assert "fact A" in merged.content and "fact B" in merged.content
    # Originals are archived and reference the consolidation.
    original = await core.get(a.id)
    assert original.lifecycle_state is LifecycleState.ARCHIVED
    assert merged.id in original.trust.provenance[-1].detail  # type: ignore[operator]


async def test_consolidate_missing_member_raises(core: MemoryCore) -> None:
    a = await _store_one(core, "only one")
    with pytest.raises(MemoryNotFoundError):
        await core.consolidate([a, "ghost"])
