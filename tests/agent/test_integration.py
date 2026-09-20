"""Integration: agent reads/writes Memory + Graph + Trust through SCP end-to-end.

Exit criterion for Phase 5: an agent reads from and writes to the knowledge
graph and memory core, with real trust scores (not the 0.5 placeholder), and
its full lifecycle (IDLE → RUNNING → PAUSED → RUNNING → STOPPED) is exercised.
"""

from __future__ import annotations

from scp.agent import (
    AgentConfig,
    AgentRuntime,
    AgentStatus,
    ContextAssembler,
    ToolCall,
    ToolStatus,
)
from scp.agent.models import AgentContext
from scp.graph import EntityType, InMemoryGraphStore, KnowledgeGraph
from scp.memory import InMemoryStore, MemoryCore, MemoryType, SourceType
from scp.query import InMemoryVectorStore, SemanticQueryEngine
from scp.trust import TrustEngine


def _full_stack() -> tuple[AgentRuntime, MemoryCore, KnowledgeGraph, SemanticQueryEngine]:
    trust = TrustEngine()
    memory = MemoryCore(InMemoryStore(), confidence_model=trust.initial_confidence)
    kg = KnowledgeGraph(InMemoryGraphStore(), confidence_model=trust.initial_confidence)
    engine = SemanticQueryEngine(kg, InMemoryVectorStore())
    assembler = ContextAssembler(engine, trust, kg)
    runtime = AgentRuntime(memory, assembler, trust)
    return runtime, memory, kg, engine


async def test_agent_reads_graph_entity_in_context() -> None:
    runtime, memory, kg, engine = _full_stack()
    entity = await kg.add_entity(
        "Eiffel Tower", entity_type=EntityType.CONCEPT, source_type=SourceType.TOOL
    )
    await engine.index_entity(entity)

    runtime.create_agent(AgentConfig(agent_id="a1", name="explorer"))
    step = await runtime.run_step("a1", "Eiffel Tower")

    assert any(i.name == "Eiffel Tower" for i in step.context.items)


async def test_agent_writes_episodic_memory_after_step() -> None:
    runtime, memory, kg, engine = _full_stack()
    runtime.create_agent(AgentConfig(agent_id="a1", name="mem-writer"))
    await runtime.run_step("a1", "knowledge query")

    records = await memory.query(memory_type=MemoryType.EPISODIC)
    assert len(records) >= 1
    assert "mem-writer" in records[0].content


async def test_context_items_carry_real_trust_scores() -> None:
    """Scores must be source-aware via TrustEngine, not the 0.5 placeholder."""
    runtime, _, kg, engine = _full_stack()
    entity = await kg.add_entity(
        "Physics", entity_type=EntityType.CONCEPT, source_type=SourceType.SYSTEM
    )
    await engine.index_entity(entity)

    runtime.create_agent(AgentConfig(agent_id="a1", name="trust-check"))
    step = await runtime.run_step("a1", "Physics")

    for item in step.context.items:
        assert item.trust_score != 0.5  # real source-aware score
        assert "trust=" in item.explanation  # explainable


async def test_agent_tool_invocation_end_to_end() -> None:
    runtime, _, _, _ = _full_stack()

    class SummarizeTool:
        name = "summarize"
        description = "Returns a fixed summary."

        async def invoke(self, input: str, *, context: AgentContext) -> str:
            ctx_count = len(context.items)
            return f"summary of {input!r} with {ctx_count} context items"

    runtime.tools.register(SummarizeTool())
    runtime.create_agent(AgentConfig(agent_id="a1", name="tool-agent"))
    call = ToolCall(call_id="c1", tool_name="summarize", input="topic")
    step = await runtime.run_step("a1", "topic", tool_calls=[call])

    assert step.tool_results[0].status == ToolStatus.SUCCESS
    assert "summary of 'topic'" in (step.tool_results[0].output or "")


async def test_full_lifecycle_idle_running_paused_stopped() -> None:
    runtime, _, _, _ = _full_stack()
    runtime.create_agent(AgentConfig(agent_id="lc", name="lifecycle"))

    assert runtime.get_agent("lc").status == AgentStatus.IDLE
    await runtime.run_step("lc", "q1")
    assert runtime.get_agent("lc").status == AgentStatus.RUNNING
    runtime.pause_agent("lc")
    assert runtime.get_agent("lc").status == AgentStatus.PAUSED
    runtime.resume_agent("lc")
    assert runtime.get_agent("lc").status == AgentStatus.RUNNING
    await runtime.run_step("lc", "q2")
    runtime.stop_agent("lc")
    assert runtime.get_agent("lc").status == AgentStatus.STOPPED
