"""Integration tests for GraphStore adapters (both in-memory and SQLite)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from scp.graph import (
    Entity,
    EntityQuery,
    EntityType,
    GraphStore,
    Relationship,
    RelationshipQuery,
    RelationType,
    TraversalDirection,
)
from scp.graph.errors import DuplicateEntityError, DuplicateRelationshipError
from scp.memory import Source, SourceType, TemporalContext, TrustMetadata

_BASE = datetime(2026, 6, 20, tzinfo=UTC)


def _entity(eid: str, *, name: str = "n", seconds: int = 0) -> Entity:
    ts = _BASE + timedelta(seconds=seconds)
    return Entity(
        id=eid,
        type=EntityType.CONCEPT,
        name=name,
        trust=TrustMetadata(source=Source(type=SourceType.SYSTEM), confidence=0.5),
        temporal=TemporalContext(created_at=ts, last_accessed=ts),
    )


def _rel(rid: str, src: str, tgt: str, *, directed: bool = True, seconds: int = 0) -> Relationship:
    ts = _BASE + timedelta(seconds=seconds)
    return Relationship(
        id=rid,
        type=RelationType.RELATED_TO,
        source_id=src,
        target_id=tgt,
        directed=directed,
        trust=TrustMetadata(source=Source(type=SourceType.SYSTEM), confidence=0.5),
        temporal=TemporalContext(created_at=ts, last_accessed=ts),
    )


async def test_entity_round_trip(graph_store: GraphStore) -> None:
    await graph_store.add_entity(_entity("e1", name="Ada"))
    got = await graph_store.get_entity("e1")
    assert got is not None and got.name == "Ada"


async def test_duplicate_entity_raises(graph_store: GraphStore) -> None:
    await graph_store.add_entity(_entity("e1"))
    with pytest.raises(DuplicateEntityError):
        await graph_store.add_entity(_entity("e1"))


async def test_relationship_round_trip_and_duplicate(graph_store: GraphStore) -> None:
    await graph_store.add_entity(_entity("e1"))
    await graph_store.add_entity(_entity("e2"))
    await graph_store.add_relationship(_rel("r1", "e1", "e2"))
    got = await graph_store.get_relationship("r1")
    assert got is not None and got.source_id == "e1"
    with pytest.raises(DuplicateRelationshipError):
        await graph_store.add_relationship(_rel("r1", "e1", "e2"))


async def test_delete_entity_cascades_relationships(graph_store: GraphStore) -> None:
    await graph_store.add_entity(_entity("e1"))
    await graph_store.add_entity(_entity("e2"))
    await graph_store.add_relationship(_rel("r1", "e1", "e2"))
    assert await graph_store.delete_entity("e1") is True
    assert await graph_store.get_relationship("r1") is None


async def test_query_entities_by_type_and_recency(graph_store: GraphStore) -> None:
    await graph_store.add_entity(_entity("e1", seconds=1))
    await graph_store.add_entity(_entity("e2", seconds=2))
    newest = await graph_store.query_entities(EntityQuery(type=EntityType.CONCEPT))
    assert [e.id for e in newest] == ["e2", "e1"]


async def test_query_relationships_by_source(graph_store: GraphStore) -> None:
    await graph_store.add_entity(_entity("e1"))
    await graph_store.add_entity(_entity("e2"))
    await graph_store.add_entity(_entity("e3"))
    await graph_store.add_relationship(_rel("r1", "e1", "e2"))
    await graph_store.add_relationship(_rel("r2", "e1", "e3"))
    out = await graph_store.query_relationships(RelationshipQuery(source_id="e1"))
    assert {r.id for r in out} == {"r1", "r2"}


async def test_neighbors_direction(graph_store: GraphStore) -> None:
    await graph_store.add_entity(_entity("e1"))
    await graph_store.add_entity(_entity("e2"))
    await graph_store.add_relationship(_rel("r1", "e1", "e2"))  # directed e1 -> e2

    out = await graph_store.neighbors("e1", direction=TraversalDirection.OUTBOUND)
    assert [r.id for r in out] == ["r1"]
    assert await graph_store.neighbors("e1", direction=TraversalDirection.INBOUND) == []
    inbound = await graph_store.neighbors("e2", direction=TraversalDirection.INBOUND)
    assert [r.id for r in inbound] == ["r1"]


async def test_undirected_neighbors_both_directions(graph_store: GraphStore) -> None:
    await graph_store.add_entity(_entity("e1"))
    await graph_store.add_entity(_entity("e2"))
    await graph_store.add_relationship(_rel("r1", "e1", "e2", directed=False))
    # Undirected edge is reachable from the target via OUTBOUND too.
    out = await graph_store.neighbors("e2", direction=TraversalDirection.OUTBOUND)
    assert [r.id for r in out] == ["r1"]
