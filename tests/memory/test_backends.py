"""Integration tests run against every MemoryStore adapter (in-memory + sqlite)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from scp.memory import (
    DuplicateMemoryError,
    LifecycleState,
    MemoryNotFoundError,
    MemoryQuery,
    MemoryRecord,
    MemoryStore,
    MemoryType,
    Source,
    SourceType,
    TemporalContext,
    TrustMetadata,
)

_BASE = datetime(2026, 6, 20, tzinfo=UTC)


def _record(rid: str, *, offset: int, mtype: MemoryType = MemoryType.SEMANTIC) -> MemoryRecord:
    created = _BASE + timedelta(seconds=offset)
    return MemoryRecord(
        id=rid,
        type=mtype,
        content=f"content {rid}",
        trust=TrustMetadata(source=Source(type=SourceType.USER), confidence=0.5),
        temporal=TemporalContext(created_at=created, last_accessed=created),
    )


async def test_add_and_get_roundtrip(store: MemoryStore) -> None:
    record = _record("a", offset=1)
    await store.add(record)
    fetched = await store.get("a")
    assert fetched == record


async def test_get_missing_returns_none(store: MemoryStore) -> None:
    assert await store.get("nope") is None


async def test_add_duplicate_raises(store: MemoryStore) -> None:
    await store.add(_record("a", offset=1))
    with pytest.raises(DuplicateMemoryError):
        await store.add(_record("a", offset=2))


async def test_update_persists_and_requires_existing(store: MemoryStore) -> None:
    await store.add(_record("a", offset=1))
    updated = (await store.get("a")).model_copy(  # type: ignore[union-attr]
        update={"lifecycle_state": LifecycleState.ARCHIVED}
    )
    await store.update(updated)
    assert (await store.get("a")).lifecycle_state is LifecycleState.ARCHIVED  # type: ignore[union-attr]
    with pytest.raises(MemoryNotFoundError):
        await store.update(_record("ghost", offset=9))


async def test_query_orders_newest_first_and_paginates(store: MemoryStore) -> None:
    for i in range(5):
        await store.add(_record(f"r{i}", offset=i))
    newest = await store.query(MemoryQuery(limit=2))
    assert [r.id for r in newest] == ["r4", "r3"]
    page2 = await store.query(MemoryQuery(limit=2, offset=2))
    assert [r.id for r in page2] == ["r2", "r1"]


async def test_query_filters_by_type_and_state(store: MemoryStore) -> None:
    await store.add(_record("s", offset=1, mtype=MemoryType.SEMANTIC))
    await store.add(_record("e", offset=2, mtype=MemoryType.EPISODIC))
    semantic = await store.query(MemoryQuery(type=MemoryType.SEMANTIC))
    assert [r.id for r in semantic] == ["s"]


async def test_delete(store: MemoryStore) -> None:
    await store.add(_record("a", offset=1))
    assert await store.delete("a") is True
    assert await store.delete("a") is False
    assert await store.get("a") is None
