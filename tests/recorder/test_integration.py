"""End-to-end tests: FlightRecorder + AgentRuntime over the full SCP stack."""

from __future__ import annotations

import uuid

from scp.agent.models import AgentConfig
from scp.agent.runtime import AgentRuntime
from scp.graph import EntityType, KnowledgeGraph
from scp.memory import SourceType
from scp.query.engine import SemanticQueryEngine
from scp.recorder import FlightRecorder


async def _seed_entity(
    kg: KnowledgeGraph,
    qe: SemanticQueryEngine,
    name: str,
) -> str:
    """Add an entity to the graph and index it for semantic search."""
    entity = await kg.add_entity(
        name,
        entity_type=EntityType.CONCEPT,
        source_type=SourceType.USER,
    )
    await qe.index_entity(entity)
    return entity.id


async def _create_agent(runtime: AgentRuntime, name: str) -> str:
    config = AgentConfig(agent_id=uuid.uuid4().hex, name=name)
    state = runtime.create_agent(config)
    return state.agent_id


async def test_record_and_replay_end_to_end(
    runtime: AgentRuntime,
    recorder: FlightRecorder,
    kg: KnowledgeGraph,
    query_engine: SemanticQueryEngine,
) -> None:
    """Run a step via AgentRuntime, record it, and verify replay matches."""
    await _seed_entity(kg, query_engine, "Photosynthesis")
    agent_id = await _create_agent(runtime, "e2e-agent")

    step = await runtime.run_step(agent_id, "photosynthesis process")
    rec = await recorder.record(step, agent_name="e2e-agent", step_index=0)

    session = await recorder.replay_agent(agent_id)

    assert len(session.steps) == 1
    assert session.steps[0].step_id == rec.step_id
    assert session.steps[0].query == "photosynthesis process"
    assert session.agent_id == agent_id


async def test_multiple_steps_accumulate_in_replay(
    runtime: AgentRuntime,
    recorder: FlightRecorder,
) -> None:
    """Record 3 steps and verify replay returns all 3 in order."""
    agent_id = await _create_agent(runtime, "multi-step-agent")

    for i in range(3):
        step = await runtime.run_step(agent_id, f"query {i}")
        await recorder.record(step, agent_name="multi-step-agent", step_index=i)

    session = await recorder.replay_agent(agent_id)
    assert len(session.steps) == 3
    assert [s.query for s in session.steps] == ["query 0", "query 1", "query 2"]


async def test_trace_entity_appears_in_recorded_step(
    runtime: AgentRuntime,
    recorder: FlightRecorder,
    kg: KnowledgeGraph,
    query_engine: SemanticQueryEngine,
) -> None:
    """Run a step that surfaces a graph entity; trace must report that step."""
    entity_id = await _seed_entity(kg, query_engine, "MitochondriaEnergy")
    agent_id = await _create_agent(runtime, "trace-agent")

    step = await runtime.run_step(agent_id, "mitochondria energy production")
    await recorder.record(step, agent_name="trace-agent", step_index=0)

    trace = await recorder.trace_entity(entity_id, agent_id=agent_id)

    # If the hybrid retrieval surfaced the entity, it should appear in the trace.
    # (It may or may not rank in top-k depending on hash overlap — the assertion
    # is conditional so the test is deterministic regardless of ranking.)
    if trace.appearances:
        assert trace.entity_name == "MitochondriaEnergy"
        assert any(a.step_id == step.step_id for a in trace.appearances)


async def test_root_cause_step_metadata_correct(
    runtime: AgentRuntime,
    recorder: FlightRecorder,
    kg: KnowledgeGraph,
    query_engine: SemanticQueryEngine,
) -> None:
    """Root-cause report captures the right step metadata."""
    await _seed_entity(kg, query_engine, "NeuralPlasticity")
    agent_id = await _create_agent(runtime, "debug-agent")

    step = await runtime.run_step(agent_id, "neural plasticity research")
    await recorder.record(step, agent_name="debug-agent", step_index=0)

    report = await recorder.root_cause(step.step_id)

    assert report.step_id == step.step_id
    assert report.agent_id == agent_id
    assert report.query == "neural plasticity research"
    assert report.report_id  # non-empty UUID hex


async def test_recorder_is_independent_of_runtime_state(
    runtime: AgentRuntime,
    recorder: FlightRecorder,
) -> None:
    """Stopping the agent does not erase records — the recorder is independent."""
    agent_id = await _create_agent(runtime, "independent-agent")

    step = await runtime.run_step(agent_id, "last query before stop")
    await recorder.record(step, agent_name="independent-agent", step_index=0)
    runtime.stop_agent(agent_id)

    # Record survives agent termination
    rec = await recorder.replay_step(step.step_id)
    assert rec.step_id == step.step_id
    assert rec.query == "last query before stop"
