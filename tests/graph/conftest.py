"""Graph test fixtures: both backends + a deterministic KnowledgeGraph.

Reuses the root `clock` / `id_factory` fixtures (deterministic).
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from datetime import datetime
from pathlib import Path

import pytest

from scp.graph import (
    GraphStore,
    InMemoryGraphStore,
    KnowledgeGraph,
    SqliteGraphStore,
)


@pytest.fixture(params=["in_memory", "sqlite"])
async def graph_store(request: pytest.FixtureRequest, tmp_path: Path) -> AsyncIterator[GraphStore]:
    """Parametrized fixture yielding each concrete GraphStore adapter."""
    if request.param == "in_memory":
        adapter: GraphStore = InMemoryGraphStore()
    else:
        adapter = await SqliteGraphStore.connect(str(tmp_path / "graph.db"))
    yield adapter
    await adapter.close()


@pytest.fixture
def graph(clock: Callable[[], datetime], id_factory: Callable[[], str]) -> KnowledgeGraph:
    """A KnowledgeGraph over an in-memory store with deterministic clock/ids."""
    return KnowledgeGraph(InMemoryGraphStore(), clock=clock, id_factory=id_factory)
