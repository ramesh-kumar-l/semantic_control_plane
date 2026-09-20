"""Unit tests for ContextAssembler."""

from __future__ import annotations

from datetime import UTC, datetime

from scp.agent.context import ContextAssembler
from scp.graph import EntityType, InMemoryGraphStore, KnowledgeGraph
from scp.memory import SourceType
from scp.query import InMemoryVectorStore, SemanticQueryEngine
from scp.trust import TrustEngine


def _stack(
    source_type: SourceType = SourceType.TOOL,
) -> tuple[KnowledgeGraph, SemanticQueryEngine, ContextAssembler]:
    trust = TrustEngine()
    kg = KnowledgeGraph(InMemoryGraphStore(), confidence_model=trust.initial_confidence)
    engine = SemanticQueryEngine(kg, InMemoryVectorStore())
    assembler = ContextAssembler(engine, trust, kg)
    return kg, engine, assembler


async def test_assemble_empty_graph_returns_no_items() -> None:
    _, _, assembler = _stack()
    ctx = await assembler.assemble("anything")
    assert ctx.query == "anything"
    assert ctx.items == []


async def test_assemble_indexed_entity_appears_in_context() -> None:
    kg, engine, assembler = _stack()
    entity = await kg.add_entity(
        "London", entity_type=EntityType.CONCEPT, source_type=SourceType.TOOL
    )
    await engine.index_entity(entity)

    now = datetime.now(UTC)
    ctx = await assembler.assemble("London", max_items=5, now=now)

    assert len(ctx.items) == 1
    item = ctx.items[0]
    assert item.entity_id == entity.id
    assert item.name == "London"
    assert item.trust_score > 0.0
    assert "trust=" in item.explanation


async def test_trust_scores_differ_by_source_type() -> None:
    """Tool sources (reliability=0.85) must outscore inference (reliability=0.45)."""
    trust = TrustEngine()
    kg = KnowledgeGraph(InMemoryGraphStore(), confidence_model=trust.initial_confidence)
    engine = SemanticQueryEngine(kg, InMemoryVectorStore())
    assembler = ContextAssembler(engine, trust, kg)

    e_tool = await kg.add_entity(
        "fact_tool", entity_type=EntityType.CONCEPT, source_type=SourceType.TOOL
    )
    e_inf = await kg.add_entity(
        "fact_inf", entity_type=EntityType.CONCEPT, source_type=SourceType.INFERENCE
    )
    await engine.index_entity(e_tool)
    await engine.index_entity(e_inf)

    now = datetime.now(UTC)
    ctx = await assembler.assemble("fact", max_items=10, now=now)

    by_name = {i.name: i.trust_score for i in ctx.items}
    assert by_name["fact_tool"] > by_name["fact_inf"]


async def test_assembled_at_matches_supplied_now() -> None:
    _, _, assembler = _stack()
    fixed = datetime(2026, 6, 20, tzinfo=UTC)
    ctx = await assembler.assemble("q", now=fixed)
    assert ctx.assembled_at == fixed


async def test_assemble_skips_deleted_entity_gracefully() -> None:
    """An entity removed from the graph after indexing should not cause an error."""
    kg, engine, assembler = _stack()
    entity = await kg.add_entity(
        "Ghost", entity_type=EntityType.CONCEPT, source_type=SourceType.SYSTEM
    )
    await engine.index_entity(entity)
    await kg.delete_entity(entity.id)

    ctx = await assembler.assemble("Ghost")
    assert ctx.items == []
