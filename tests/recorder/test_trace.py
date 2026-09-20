"""Tests for TraceEngine and FlightRecorder trace surface."""

from __future__ import annotations

import pytest

from scp.recorder import FlightRecorder, RecordNotFoundError

from .conftest import AGENT_NAME, make_context_item, make_step


async def test_trace_entity_no_appearances(recorder: FlightRecorder) -> None:
    trace = await recorder.trace_entity("e-unknown")

    assert trace.entity_id == "e-unknown"
    assert trace.appearances == []
    assert trace.entity_name == ""


async def test_trace_entity_single_appearance(recorder: FlightRecorder) -> None:
    item = make_context_item(entity_id="e1", name="Alpha", trust=0.75)
    step = make_step(context_items=[item])
    await recorder.record(step, agent_name=AGENT_NAME, step_index=0)

    trace = await recorder.trace_entity("e1")

    assert len(trace.appearances) == 1
    assert trace.entity_name == "Alpha"
    assert trace.appearances[0].step_id == step.step_id
    assert trace.appearances[0].trust_score == pytest.approx(0.75)


async def test_trace_entity_multiple_appearances(recorder: FlightRecorder) -> None:
    item = make_context_item(entity_id="e1")
    for i in range(3):
        step = make_step(query=f"q{i}", context_items=[item])
        await recorder.record(step, agent_name=AGENT_NAME, step_index=i)

    trace = await recorder.trace_entity("e1")

    assert len(trace.appearances) == 3


async def test_trace_entity_agent_filter(recorder: FlightRecorder) -> None:
    item = make_context_item(entity_id="shared")
    step_a = make_step(agent_id="agent-A", context_items=[item])
    step_b = make_step(agent_id="agent-B", context_items=[item])
    await recorder.record(step_a, agent_name="A", step_index=0)
    await recorder.record(step_b, agent_name="B", step_index=0)

    trace_a = await recorder.trace_entity("shared", agent_id="agent-A")
    trace_all = await recorder.trace_entity("shared")

    assert len(trace_a.appearances) == 1
    assert trace_a.appearances[0].step_id == step_a.step_id
    assert len(trace_all.appearances) == 2


async def test_trace_step_returns_one_trace_per_context_item(
    recorder: FlightRecorder,
) -> None:
    items = [
        make_context_item(entity_id="e1", name="Alpha"),
        make_context_item(entity_id="e2", name="Beta"),
    ]
    step = make_step(context_items=items)
    await recorder.record(step, agent_name=AGENT_NAME, step_index=0)

    traces = await recorder.trace_step(step.step_id)

    entity_ids = {t.entity_id for t in traces}
    assert entity_ids == {"e1", "e2"}


async def test_trace_step_unknown_raises(recorder: FlightRecorder) -> None:
    with pytest.raises(RecordNotFoundError):
        await recorder.trace_step("no-such-step")


async def test_trace_appearance_trust_matches_context_item(recorder: FlightRecorder) -> None:
    item = make_context_item(entity_id="e1", trust=0.92)
    step = make_step(context_items=[item])
    await recorder.record(step, agent_name=AGENT_NAME, step_index=0)

    trace = await recorder.trace_entity("e1")

    assert trace.appearances[0].trust_score == pytest.approx(0.92)


async def test_trace_appearance_step_index_correct(recorder: FlightRecorder) -> None:
    item = make_context_item(entity_id="e1")
    step = make_step(context_items=[item])
    await recorder.record(step, agent_name=AGENT_NAME, step_index=7)

    trace = await recorder.trace_entity("e1")

    assert trace.appearances[0].step_index == 7


async def test_trace_entity_name_captured_from_context(recorder: FlightRecorder) -> None:
    item = make_context_item(entity_id="e99", name="SpecialName", trust=0.5)
    step = make_step(context_items=[item])
    await recorder.record(step, agent_name=AGENT_NAME, step_index=0)

    trace = await recorder.trace_entity("e99")

    assert trace.entity_name == "SpecialName"
