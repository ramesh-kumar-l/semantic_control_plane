"""Shared fixtures for Agent Runtime tests."""

from __future__ import annotations

import pytest

from scp.agent.context import ContextAssembler
from scp.agent.runtime import AgentRuntime
from scp.graph import InMemoryGraphStore, KnowledgeGraph
from scp.memory import InMemoryStore, MemoryCore
from scp.query import InMemoryVectorStore, SemanticQueryEngine
from scp.trust import TrustEngine


@pytest.fixture
def trust_engine() -> TrustEngine:
    return TrustEngine()


@pytest.fixture
def kg(trust_engine: TrustEngine) -> KnowledgeGraph:
    return KnowledgeGraph(InMemoryGraphStore(), confidence_model=trust_engine.initial_confidence)


@pytest.fixture
def query_engine(kg: KnowledgeGraph) -> SemanticQueryEngine:
    return SemanticQueryEngine(kg, InMemoryVectorStore())


@pytest.fixture
def assembler(
    query_engine: SemanticQueryEngine,
    trust_engine: TrustEngine,
    kg: KnowledgeGraph,
) -> ContextAssembler:
    return ContextAssembler(query_engine, trust_engine, kg)


@pytest.fixture
def memory(trust_engine: TrustEngine) -> MemoryCore:
    return MemoryCore(InMemoryStore(), confidence_model=trust_engine.initial_confidence)


@pytest.fixture
def runtime(
    memory: MemoryCore,
    assembler: ContextAssembler,
    trust_engine: TrustEngine,
) -> AgentRuntime:
    return AgentRuntime(memory, assembler, trust_engine)
