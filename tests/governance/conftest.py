"""Shared fixtures for Governance Layer tests."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

from scp.agent.context import ContextAssembler
from scp.agent.models import AgentContext, AgentStep, ContextItem, ToolResult
from scp.agent.runtime import AgentRuntime
from scp.governance import GovernanceLayer, InMemoryAuditStore, InMemoryPolicyStore
from scp.governance.enums import PolicyAction, PolicyScope
from scp.governance.models import Policy, PolicyCondition
from scp.graph import InMemoryGraphStore, KnowledgeGraph
from scp.memory import InMemoryStore, MemoryCore
from scp.memory.enums import VerificationStatus
from scp.query import InMemoryVectorStore, SemanticQueryEngine
from scp.trust import TrustEngine

# ---- SCP stack fixtures (mirrors agent/conftest.py) -------------------------


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


# ---- governance fixtures -----------------------------------------------------


@pytest.fixture
def governance() -> GovernanceLayer:
    return GovernanceLayer()


@pytest.fixture
def policy_store() -> InMemoryPolicyStore:
    return InMemoryPolicyStore()


@pytest.fixture
def audit_store() -> InMemoryAuditStore:
    return InMemoryAuditStore()


# ---- helpers -----------------------------------------------------------------


def make_context_item(
    entity_id: str = "eid-1",
    name: str = "test entity",
    trust: float = 0.8,
) -> ContextItem:
    return ContextItem(
        entity_id=entity_id,
        name=name,
        content_summary="test summary",
        trust_score=trust,
        explanation=f"trust={trust:.2f}",
    )


def make_agent_step(
    agent_id: str = "agent-1",
    query: str = "what is X?",
    items: list[ContextItem] | None = None,
    tool_results: list[ToolResult] | None = None,
) -> AgentStep:
    if items is None:
        items = [make_context_item()]
    ctx = AgentContext(query=query, items=items, assembled_at=datetime.now(UTC))
    return AgentStep(
        step_id=uuid.uuid4().hex,
        agent_id=agent_id,
        query=query,
        context=ctx,
        tool_results=tool_results or [],
        created_at=datetime.now(UTC),
    )


def make_deny_policy(
    min_trust: float = 0.5,
    scope: PolicyScope = PolicyScope.CONTEXT_ITEM,
) -> Policy:
    return Policy(
        policy_id=uuid.uuid4().hex,
        name="deny-low-trust",
        description="Deny items with trust below threshold",
        scope=scope,
        condition=PolicyCondition(min_trust_score=min_trust),
        action=PolicyAction.DENY,
        created_at=datetime.now(UTC),
    )


def make_warn_policy(
    forbidden: VerificationStatus = VerificationStatus.CONTRADICTED,
) -> Policy:
    return Policy(
        policy_id=uuid.uuid4().hex,
        name="warn-contradicted",
        description="Warn on contradicted context",
        scope=PolicyScope.CONTEXT_ITEM,
        condition=PolicyCondition(forbidden_verification_status=forbidden),
        action=PolicyAction.WARN,
        created_at=datetime.now(UTC),
    )
