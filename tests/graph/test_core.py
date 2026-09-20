"""Unit tests for the KnowledgeGraph service facade."""

from __future__ import annotations

import pytest

from scp.graph import (
    EntityType,
    KnowledgeGraph,
    RelationType,
    TraversalDirection,
)
from scp.graph.errors import (
    DanglingRelationshipError,
    EntityNotFoundError,
    RelationshipNotFoundError,
)
from scp.memory import ProvenanceOperation, SourceType, VerificationStatus


async def _person(graph: KnowledgeGraph, name: str) -> str:
    entity = await graph.add_entity(
        name, entity_type=EntityType.PERSON, source_type=SourceType.USER
    )
    return entity.id


async def test_add_entity_attaches_trust_and_provenance(graph: KnowledgeGraph) -> None:
    entity = await graph.add_entity(
        "Ada",
        entity_type=EntityType.PERSON,
        source_type=SourceType.USER,
        confidence=0.9,
        verification_status=VerificationStatus.VERIFIED,
    )
    assert entity.id == "mem-1"  # deterministic id_factory
    assert entity.trust.confidence == 0.9
    assert entity.trust.verification_status is VerificationStatus.VERIFIED
    assert entity.trust.provenance[0].operation is ProvenanceOperation.INGEST


async def test_get_missing_entity_raises(graph: KnowledgeGraph) -> None:
    with pytest.raises(EntityNotFoundError):
        await graph.get_entity("nope")


async def test_add_relationship_requires_existing_endpoints(graph: KnowledgeGraph) -> None:
    src = await _person(graph, "Ada")
    with pytest.raises(DanglingRelationshipError):
        await graph.add_relationship(
            src, "ghost", relation_type=RelationType.RELATED_TO, source_type=SourceType.USER
        )


async def test_relationship_round_trip(graph: KnowledgeGraph) -> None:
    a = await _person(graph, "Ada")
    b = await _person(graph, "Charles")
    rel = await graph.add_relationship(
        a, b, relation_type=RelationType.RELATED_TO, source_type=SourceType.USER
    )
    fetched = await graph.get_relationship(rel.id)
    assert fetched.source_id == a and fetched.target_id == b


async def test_traverse_and_find_path(graph: KnowledgeGraph) -> None:
    a = await _person(graph, "a")
    b = await _person(graph, "b")
    c = await _person(graph, "c")
    await graph.add_relationship(
        a, b, relation_type=RelationType.RELATED_TO, source_type=SourceType.SYSTEM
    )
    await graph.add_relationship(
        b, c, relation_type=RelationType.RELATED_TO, source_type=SourceType.SYSTEM
    )

    result = await graph.traverse(a, max_depth=2)
    assert {s.entity_id for s in result.steps} == {a, b, c}

    path = await graph.find_path(a, c, max_depth=5)
    assert path is not None and len(path) == 2


async def test_neighbors_validates_entity(graph: KnowledgeGraph) -> None:
    with pytest.raises(EntityNotFoundError):
        await graph.neighbors("missing")


async def test_delete_entity_cascades(graph: KnowledgeGraph) -> None:
    a = await _person(graph, "a")
    b = await _person(graph, "b")
    rel = await graph.add_relationship(
        a, b, relation_type=RelationType.RELATED_TO, source_type=SourceType.SYSTEM
    )
    assert await graph.delete_entity(a) is True
    with pytest.raises(RelationshipNotFoundError):
        await graph.get_relationship(rel.id)


async def test_directed_traverse_excludes_inbound(graph: KnowledgeGraph) -> None:
    a = await _person(graph, "a")
    b = await _person(graph, "b")
    await graph.add_relationship(
        a, b, relation_type=RelationType.RELATED_TO, source_type=SourceType.SYSTEM
    )
    # From b, OUTBOUND on a directed a->b edge reaches nothing.
    result = await graph.traverse(b, direction=TraversalDirection.OUTBOUND, max_depth=3)
    assert {s.entity_id for s in result.steps} == {b}
