"""Shared test fixtures: deterministic clock + id factory, and both backends."""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from scp.memory import InMemoryStore, MemoryCore, MemoryStore, SqliteStore


@pytest.fixture
def clock() -> Callable[[], datetime]:
    """A monotonic clock advancing one second per call (deterministic)."""
    base = datetime(2026, 6, 20, tzinfo=UTC)
    counter = {"n": 0}

    def _tick() -> datetime:
        counter["n"] += 1
        return base + timedelta(seconds=counter["n"])

    return _tick


@pytest.fixture
def id_factory() -> Callable[[], str]:
    """Sequential ids: mem-1, mem-2, ... (deterministic)."""
    counter = {"n": 0}

    def _next() -> str:
        counter["n"] += 1
        return f"mem-{counter['n']}"

    return _next


@pytest.fixture
def core(clock: Callable[[], datetime], id_factory: Callable[[], str]) -> MemoryCore:
    """A MemoryCore over an in-memory store with deterministic clock/ids."""
    return MemoryCore(InMemoryStore(), clock=clock, id_factory=id_factory)


@pytest.fixture(params=["in_memory", "sqlite"])
async def store(request: pytest.FixtureRequest, tmp_path: Path) -> AsyncIterator[MemoryStore]:
    """Parametrized fixture yielding each concrete MemoryStore adapter."""
    if request.param == "in_memory":
        adapter: MemoryStore = InMemoryStore()
    else:
        adapter = await SqliteStore.connect(str(tmp_path / "memories.db"))
    yield adapter
    await adapter.close()
