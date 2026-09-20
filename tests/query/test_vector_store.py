"""Unit tests for the in-memory cosine vector index."""

from __future__ import annotations

from scp.query import HashingEmbedder, InMemoryVectorStore


async def test_upsert_get_delete_size() -> None:
    store = InMemoryVectorStore()
    embedder = HashingEmbedder(dimension=64)
    await store.upsert("a", embedder.embed("python"))
    assert await store.size() == 1
    assert await store.get("a") is not None
    # Upsert replaces, does not duplicate.
    await store.upsert("a", embedder.embed("django"))
    assert await store.size() == 1
    assert await store.delete("a") is True
    assert await store.delete("a") is False
    assert await store.get("a") is None


async def test_search_orders_by_similarity() -> None:
    store = InMemoryVectorStore()
    embedder = HashingEmbedder(dimension=256)
    await store.upsert("python", embedder.embed("python programming language"))
    await store.upsert("ocean", embedder.embed("atlantic ocean tides"))
    matches = await store.search(embedder.embed("python language"), top_k=2)
    assert [m.id for m in matches] == ["python", "ocean"]
    assert matches[0].score > matches[1].score


async def test_search_respects_top_k_and_empty() -> None:
    store = InMemoryVectorStore()
    embedder = HashingEmbedder(dimension=64)
    await store.upsert("a", embedder.embed("alpha"))
    await store.upsert("b", embedder.embed("beta"))
    assert len(await store.search(embedder.embed("alpha"), top_k=1)) == 1
    assert await store.search(embedder.embed("alpha"), top_k=0) == []


async def test_search_tie_break_is_deterministic_by_id() -> None:
    store = InMemoryVectorStore()
    embedder = HashingEmbedder(dimension=64)
    same = embedder.embed("identical text")
    for vid in ("z", "a", "m"):
        await store.upsert(vid, same)
    matches = await store.search(same, top_k=3)
    assert [m.id for m in matches] == ["a", "m", "z"]


async def test_clear() -> None:
    store = InMemoryVectorStore()
    await store.upsert("a", HashingEmbedder(dimension=8).embed("x"))
    await store.clear()
    assert await store.size() == 0
