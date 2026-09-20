"""Shared fixtures for Flight Recorder tests."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

from scp.agent.context import ContextAssembler
from scp.agent.enums import ToolStatus
from scp.agent.models import AgentContext, AgentStep, ContextItem, ToolResult
from scp.agent.runtime import AgentRuntime
from scp.graph import InMemoryGraphStore, KnowledgeGraph
from scp.memory import InMemoryStore, MemoryCore
from scp.query import InMemoryVectorStore, SemanticQueryEngine
from scp.recorder import FlightRecorder
from scp.trust import TrustEngine

AGENT_ID = "agent-test"
AGENT_NAME = "test-agent"


# ---------------------------------------------------------------------------
# Full SCP stack fixtures (mirrors tests/agent/conftest.py)
# ---------------------------------------------------------------------------


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


@pytest.fixture
def recorder() -> FlightRecorder:
    return FlightRecorder()


# ---------------------------------------------------------------------------
# Lightweight helpers (no stack needed)
# ---------------------------------------------------------------------------


def make_context_item(
    entity_id: str = "e1",
    name: str = "Entity One",
    trust: float = 0.8,
) -> ContextItem:
    return ContextItem(
        entity_id=entity_id,
        name=name,
        content_summary=f"Summary of {name}",
        trust_score=trust,
        explanation=f"source_reliability=0.9 trust={trust:.2f}",
    )


def make_agent_context(*items: ContextItem, query: str = "test query") -> AgentContext:
    return AgentContext(
        query=query,
        items=list(items),
        assembled_at=datetime.now(UTC),
    )


def make_step(
    query: str = "what is X?",
    agent_id: str = AGENT_ID,
    context_items: list[ContextItem] | None = None,
    tool_results: list[ToolResult] | None = None,
) -> AgentStep:
    items = context_items if context_items is not None else [make_context_item()]
    return AgentStep(
        step_id=uuid.uuid4().hex,
        agent_id=agent_id,
        query=query,
        context=make_agent_context(*items, query=query),
        tool_results=tool_results or [],
        created_at=datetime.now(UTC),
    )


def make_tool_result(
    tool_name: str = "search",
    output: str = "ok",
    status: ToolStatus = ToolStatus.SUCCESS,
) -> ToolResult:
    return ToolResult(
        call_id=uuid.uuid4().hex,
        tool_name=tool_name,
        input="input",
        output=output,
        status=status,
        latency_ms=5.0,
    )
