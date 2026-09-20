"""Unit tests for AgentRuntime step execution and lifecycle integration."""

from __future__ import annotations

import pytest

from scp.agent import (
    AgentConfig,
    AgentRuntime,
    AgentStatus,
    ToolCall,
    ToolStatus,
)
from scp.agent.context import ContextAssembler
from scp.agent.errors import AgentNotRunningError, MaxStepsExceededError
from scp.agent.models import AgentContext
from scp.graph import InMemoryGraphStore, KnowledgeGraph
from scp.memory import InMemoryStore, MemoryCore, MemoryType
from scp.query import InMemoryVectorStore, SemanticQueryEngine
from scp.trust import TrustEngine


def _build_runtime(max_steps: int = 10) -> tuple[AgentRuntime, MemoryCore]:
    trust = TrustEngine()
    memory = MemoryCore(InMemoryStore(), confidence_model=trust.initial_confidence)
    kg = KnowledgeGraph(InMemoryGraphStore(), confidence_model=trust.initial_confidence)
    engine = SemanticQueryEngine(kg, InMemoryVectorStore())
    assembler = ContextAssembler(engine, trust, kg)
    runtime = AgentRuntime(memory, assembler, trust)
    return runtime, memory


async def test_create_agent_starts_idle() -> None:
    runtime, _ = _build_runtime()
    cfg = AgentConfig(agent_id="a1", name="tester")
    state = runtime.create_agent(cfg)
    assert state.status == AgentStatus.IDLE


async def test_run_step_transitions_to_running() -> None:
    runtime, _ = _build_runtime()
    runtime.create_agent(AgentConfig(agent_id="a1", name="tester"))
    step = await runtime.run_step("a1", "test query")
    assert step.query == "test query"
    assert step.context.query == "test query"
    assert runtime.get_agent("a1").status == AgentStatus.RUNNING
    assert len(runtime.get_agent("a1").steps) == 1


async def test_run_step_persists_to_episodic_memory() -> None:
    runtime, memory = _build_runtime()
    runtime.create_agent(AgentConfig(agent_id="a1", name="persist-test"))
    await runtime.run_step("a1", "knowledge query")
    records = await memory.query(memory_type=MemoryType.EPISODIC)
    assert len(records) == 1
    assert "persist-test" in records[0].content


async def test_run_step_with_tool_captures_result() -> None:
    runtime, _ = _build_runtime()

    class EchoTool:
        name = "echo"
        description = "echo"

        async def invoke(self, input: str, *, context: AgentContext) -> str:
            return f"echoed: {input}"

    runtime.tools.register(EchoTool())
    runtime.create_agent(AgentConfig(agent_id="a1", name="tool-test"))
    call = ToolCall(call_id="c1", tool_name="echo", input="hello")
    step = await runtime.run_step("a1", "q", tool_calls=[call])
    assert len(step.tool_results) == 1
    assert step.tool_results[0].status == ToolStatus.SUCCESS
    assert step.tool_results[0].output == "echoed: hello"


async def test_run_step_on_stopped_agent_raises() -> None:
    runtime, _ = _build_runtime()
    runtime.create_agent(AgentConfig(agent_id="a1", name="tester"))
    await runtime.run_step("a1", "q1")
    runtime.stop_agent("a1")
    with pytest.raises(AgentNotRunningError):
        await runtime.run_step("a1", "q2")


async def test_max_steps_exceeded_raises_and_marks_failed() -> None:
    runtime, _ = _build_runtime()
    runtime.create_agent(AgentConfig(agent_id="a1", name="tester", max_steps=2))
    await runtime.run_step("a1", "q1")
    await runtime.run_step("a1", "q2")
    with pytest.raises(MaxStepsExceededError):
        await runtime.run_step("a1", "q3")
    assert runtime.get_agent("a1").status == AgentStatus.FAILED


async def test_pause_and_resume_lifecycle() -> None:
    runtime, _ = _build_runtime()
    runtime.create_agent(AgentConfig(agent_id="a1", name="tester"))
    await runtime.run_step("a1", "q1")
    runtime.pause_agent("a1")
    assert runtime.get_agent("a1").status == AgentStatus.PAUSED
    runtime.resume_agent("a1")
    assert runtime.get_agent("a1").status == AgentStatus.RUNNING
    runtime.stop_agent("a1")
    assert runtime.get_agent("a1").status == AgentStatus.STOPPED


async def test_multiple_steps_accumulate() -> None:
    runtime, memory = _build_runtime()
    runtime.create_agent(AgentConfig(agent_id="a1", name="multi"))
    await runtime.run_step("a1", "step one")
    await runtime.run_step("a1", "step two")
    await runtime.run_step("a1", "step three")
    assert len(runtime.get_agent("a1").steps) == 3
    records = await memory.query(memory_type=MemoryType.EPISODIC)
    assert len(records) == 3
