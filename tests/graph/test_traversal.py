"""Unit tests for the pure BFS traversal functions (no storage dependency)."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from scp.graph import RelationType, TraversalDirection
from scp.graph.errors import InvalidTraversalError
from scp.graph.models import Relationship
from scp.graph.traversal import breadth_first, shortest_path
from scp.memory import Source, SourceType, TemporalContext, TrustMetadata

_NOW = datetime(2026, 6, 20, tzinfo=UTC)


def _edge(rid: str, src: str, tgt: str) -> Relationship:
    return Relationship(
        id=rid,
        type=RelationType.RELATED_TO,
        source_id=src,
        target_id=tgt,
        trust=TrustMetadata(source=Source(type=SourceType.SYSTEM), confidence=0.5),
        temporal=TemporalContext(created_at=_NOW, last_accessed=_NOW),
    )


# Directed chain e1->e2->e3->e4 with a branch e1->e5.
_EDGES = [
    _edge("r12", "e1", "e2"),
    _edge("r23", "e2", "e3"),
    _edge("r34", "e3", "e4"),
    _edge("r15", "e1", "e5"),
]


def _make_neighbors_fn() -> object:
    async def neighbors_fn(
        entity_id: str,
        direction: TraversalDirection,
        relation_type: RelationType | None,
    ) -> list[Relationship]:
        if direction is TraversalDirection.OUTBOUND:
            return [e for e in _EDGES if e.source_id == entity_id]
        if direction is TraversalDirection.INBOUND:
            return [e for e in _EDGES if e.target_id == entity_id]
        return [e for e in _EDGES if entity_id in (e.source_id, e.target_id)]

    return neighbors_fn


async def test_breadth_first_respects_max_depth() -> None:
    result = await breadth_first("e1", neighbors_fn=_make_neighbors_fn(), max_depth=1)
    reached = {step.entity_id for step in result.steps}
    assert reached == {"e1", "e2", "e5"}  # e3, e4 are 2+ hops away


async def test_breadth_first_records_depth() -> None:
    result = await breadth_first("e1", neighbors_fn=_make_neighbors_fn(), max_depth=3)
    depth = {step.entity_id: step.depth for step in result.steps}
    assert depth == {"e1": 0, "e2": 1, "e5": 1, "e3": 2, "e4": 3}


async def test_shortest_path_found() -> None:
    path = await shortest_path("e1", "e4", neighbors_fn=_make_neighbors_fn(), max_depth=5)
    assert path is not None
    assert [r.id for r in path] == ["r12", "r23", "r34"]


async def test_shortest_path_unreachable_within_depth() -> None:
    path = await shortest_path("e1", "e4", neighbors_fn=_make_neighbors_fn(), max_depth=2)
    assert path is None


async def test_shortest_path_same_node_is_empty() -> None:
    path = await shortest_path("e1", "e1", neighbors_fn=_make_neighbors_fn())
    assert path == []


async def test_invalid_depth_raises() -> None:
    with pytest.raises(InvalidTraversalError):
        await breadth_first("e1", neighbors_fn=_make_neighbors_fn(), max_depth=0)
