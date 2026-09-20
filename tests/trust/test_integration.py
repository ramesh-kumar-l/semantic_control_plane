"""Integration: wiring the Trust Engine into Phase 1/2 replaces the 0.5 placeholder.

The Trust Engine's `initial_confidence` is injected as a confidence model. Memory
Core and Knowledge Graph then store real, source-aware confidence instead of the
flat default — without either module importing the Trust Engine (clean dependency
inversion, `02-system-architecture.md`).
"""

from __future__ import annotations

from datetime import UTC, datetime

from scp.graph import EntityType, InMemoryGraphStore, KnowledgeGraph
from scp.memory import InMemoryStore, MemoryCore, MemoryType, SourceType
from scp.trust import TrustEngine


async def test_memory_core_uses_real_confidence_not_placeholder() -> None:
    engine = TrustEngine()
    core = MemoryCore(InMemoryStore(), confidence_model=engine.initial_confidence)

    from_user = await core.store(
        "fact", memory_type=MemoryType.SEMANTIC, source_type=SourceType.USER
    )
    from_inference = await core.store(
        "guess", memory_type=MemoryType.SEMANTIC, source_type=SourceType.INFERENCE
    )

    assert from_user.trust.confidence == 0.70
    assert from_inference.trust.confidence == 0.40
    assert from_user.trust.confidence != 0.5  # placeholder is gone


async def test_explicit_confidence_still_overrides_the_model() -> None:
    engine = TrustEngine()
    core = MemoryCore(InMemoryStore(), confidence_model=engine.initial_confidence)
    record = await core.store(
        "fact", memory_type=MemoryType.SEMANTIC, source_type=SourceType.USER, confidence=0.33
    )
    assert record.trust.confidence == 0.33


async def test_without_a_model_behaviour_is_unchanged() -> None:
    core = MemoryCore(InMemoryStore())
    record = await core.store("fact", memory_type=MemoryType.SEMANTIC, source_type=SourceType.USER)
    assert record.trust.confidence == 0.5  # backward-compatible fallback


async def test_knowledge_graph_uses_real_confidence() -> None:
    engine = TrustEngine()
    kg = KnowledgeGraph(InMemoryGraphStore(), confidence_model=engine.initial_confidence)
    entity = await kg.add_entity(
        "Eiffel Tower", entity_type=EntityType.CONCEPT, source_type=SourceType.TOOL
    )
    assert entity.trust.confidence == 0.80

    # And the engine can re-assess the stored item explainably/reproducibly.
    now = datetime.now(UTC)
    first = engine.assess(entity, now=now)
    second = engine.assess(entity, now=now)
    assert first == second
    assert "trust=" in first.explanation
