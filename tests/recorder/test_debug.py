"""Tests for DebugEngine and FlightRecorder root-cause surface."""

from __future__ import annotations

import pytest

from scp.recorder import FlightRecorder, RecordNotFoundError

from .conftest import (
    AGENT_ID,
    AGENT_NAME,
    make_context_item,
    make_step,
    make_tool_result,
)


async def test_root_cause_has_correct_step_metadata(recorder: FlightRecorder) -> None:
    step = make_step(query="why is the sky blue?")
    await recorder.record(step, agent_name=AGENT_NAME, step_index=0)

    report = await recorder.root_cause(step.step_id)

    assert report.step_id == step.step_id
    assert report.agent_id == AGENT_ID
    assert report.query == "why is the sky blue?"


async def test_top_context_sorted_by_trust_descending(recorder: FlightRecorder) -> None:
    items = [
        make_context_item(entity_id="low", trust=0.3),
        make_context_item(entity_id="high", trust=0.9),
        make_context_item(entity_id="mid", trust=0.6),
    ]
    step = make_step(context_items=items)
    await recorder.record(step, agent_name=AGENT_NAME, step_index=0)

    report = await recorder.root_cause(step.step_id)

    scores = [i.trust_score for i in report.top_context_items]
    assert scores == sorted(scores, reverse=True)
    assert report.top_context_items[0].entity_id == "high"


async def test_trust_signals_extracted_from_explanations(recorder: FlightRecorder) -> None:
    items = [
        make_context_item(entity_id="e1", trust=0.8),
        make_context_item(entity_id="e2", trust=0.5),
    ]
    step = make_step(context_items=items)
    await recorder.record(step, agent_name=AGENT_NAME, step_index=0)

    report = await recorder.root_cause(step.step_id)

    assert len(report.trust_signals) == 2
    for signal in report.trust_signals:
        assert signal  # non-empty strings


async def test_tool_outcomes_captured_in_report(recorder: FlightRecorder) -> None:
    tool_result = make_tool_result(tool_name="lookup", output="found it")
    step = make_step(tool_results=[tool_result])
    await recorder.record(step, agent_name=AGENT_NAME, step_index=0)

    report = await recorder.root_cause(step.step_id)

    assert len(report.tool_outcomes) == 1
    assert report.tool_outcomes[0].tool_name == "lookup"
    assert report.tool_outcomes[0].output == "found it"


async def test_related_steps_identified_via_shared_entity(recorder: FlightRecorder) -> None:
    shared = make_context_item(entity_id="shared-e")

    step1 = make_step(query="q1", context_items=[shared])
    step2 = make_step(query="q2", context_items=[shared])
    await recorder.record(step1, agent_name=AGENT_NAME, step_index=0)
    await recorder.record(step2, agent_name=AGENT_NAME, step_index=1)

    report = await recorder.root_cause(step1.step_id)

    assert step2.step_id in report.related_step_ids
    # step1 should not reference itself
    assert step1.step_id not in report.related_step_ids


async def test_root_cause_no_related_steps_when_entity_unique(
    recorder: FlightRecorder,
) -> None:
    step = make_step(context_items=[make_context_item(entity_id="unique-e")])
    await recorder.record(step, agent_name=AGENT_NAME, step_index=0)

    report = await recorder.root_cause(step.step_id)

    assert report.related_step_ids == []


async def test_root_cause_unknown_step_raises(recorder: FlightRecorder) -> None:
    with pytest.raises(RecordNotFoundError):
        await recorder.root_cause("no-such-step")
