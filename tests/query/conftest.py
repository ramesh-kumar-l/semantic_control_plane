"""Query test fixtures: a deterministic KnowledgeGraph + SemanticQueryEngine.

Reuses the root `clock` / `id_factory` fixtures (deterministic).
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

import pytest

from scp.graph import EntityType, InMemoryGraphStore, KnowledgeGraph, RelationType
from scp.memory import SourceType
from scp.query import HashingEmbedder, InMemoryVectorStore, SemanticQueryEngine


@pytest.fixture
def kg(clock: Callable[[], datetime], id_factory: Callable[[], str]) -> KnowledgeGraph:
    """A KnowledgeGraph over an in-memory store with deterministic clock/ids."""
    return KnowledgeGraph(InMemoryGraphStore(), clock=clock, id_factory=id_factory)


@pytest.fixture
def engine(kg: KnowledgeGraph) -> SemanticQueryEngine:
    """A SemanticQueryEngine over the graph with a deterministic embedder."""
    return SemanticQueryEngine(kg, InMemoryVectorStore(), embedder=HashingEmbedder())


@pytest.fixture
async def tech_corpus(
    engine: SemanticQueryEngine, kg: KnowledgeGraph
) -> tuple[SemanticQueryEngine, dict[str, str]]:
    """A small labeled corpus where the relevant answers are graph-adjacent to a
    lexical seed but share no query words — the case hybrid retrieval must win.

    Filler concepts are created first (so they hold the lowest ids and dominate
    a vector-only score tie); the gold answers are created last.
    """
    ids: dict[str, str] = {}

    async def add(name: str, entity_type: EntityType = EntityType.CONCEPT) -> str:
        entity = await kg.add_entity(name, entity_type=entity_type, source_type=SourceType.USER)
        ids[name] = entity.id
        return entity.id

    for filler in (
        "photosynthesis in plants",
        "the planet jupiter",
        "baroque chamber music",
        "the atlantic ocean",
        "mount everest summit",
    ):
        await add(filler)

    python = await add("python programming language")
    guido = await add("guido van rossum", EntityType.PERSON)
    django = await add("django web framework")
    orm = await add("object relational mapper")

    # Relevant neighbours, lexically dissimilar from their queries.
    await kg.add_relationship(
        python, guido, relation_type=RelationType.RELATED_TO, source_type=SourceType.USER
    )
    await kg.add_relationship(
        django, orm, relation_type=RelationType.HAS_PART, source_type=SourceType.USER
    )

    await engine.reindex()
    return engine, ids
