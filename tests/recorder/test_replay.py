"""Tests for ReplayEngine and FlightRecorder replay surface."""

from __future__ import annotations

import pytest

from scp.recorder import FlightRecorder, RecordNotFoundError

from .conftest import AGENT_ID, AGENT_NAME, make_step


async def _record_steps(recorder: FlightRecorder, n: int, agent_id: str = AGENT_ID) -> list[str]:
    """Record `n` steps and return the step_ids in order."""
    step_ids = []
    for i in range(n):
        step = make_step(query=f"query {i}", agent_id=agent_id)
        await recorder.record(step, agent_name=AGENT_NAME, step_index=i)
        step_ids.append(step.step_id)
    return step_ids


async def test_replay_step_returns_recorded_snapshot(recorder: FlightRecorder) -> None:
    step = make_step()
    await recorder.record(step, agent_name=AGENT_NAME, step_index=0)

    result = await recorder.replay_step(step.step_id)

    assert result.step_id == step.step_id
    assert result.query == step.query
    assert result.agent_id == step.agent_id


async def test_replay_step_unknown_raises(recorder: FlightRecorder) -> None:
    with pytest.raises(RecordNotFoundError):
        await recorder.replay_step("no-such-step")


async def test_replay_agent_returns_all_steps_ordered(recorder: FlightRecorder) -> None:
    step_ids = await _record_steps(recorder, 3)

    session = await recorder.replay_agent(AGENT_ID)

    assert len(session.steps) == 3
    assert [s.step_id for s in session.steps] == step_ids


async def test_replay_agent_empty_history(recorder: FlightRecorder) -> None:
    session = await recorder.replay_agent("unknown-agent")

    assert session.agent_id == "unknown-agent"
    assert session.steps == []


async def test_replay_agent_from_index(recorder: FlightRecorder) -> None:
    step_ids = await _record_steps(recorder, 4)

    session = await recorder.replay_agent(AGENT_ID, from_index=2)

    assert len(session.steps) == 2
    assert session.steps[0].step_id == step_ids[2]
    assert session.from_index == 2


async def test_replay_agent_to_index(recorder: FlightRecorder) -> None:
    step_ids = await _record_steps(recorder, 4)

    session = await recorder.replay_agent(AGENT_ID, to_index=1)

    assert len(session.steps) == 2
    assert session.steps[-1].step_id == step_ids[1]
    assert session.to_index == 1


async def test_replay_session_metadata(recorder: FlightRecorder) -> None:
    await _record_steps(recorder, 3)

    session = await recorder.replay_agent(AGENT_ID, from_index=1, to_index=2)

    assert session.agent_id == AGENT_ID
    assert session.from_index == 1
    assert session.to_index == 2
    assert session.session_id  # non-empty


async def test_replay_agents_are_isolated(recorder: FlightRecorder) -> None:
    await _record_steps(recorder, 2, agent_id="agent-A")
    await _record_steps(recorder, 3, agent_id="agent-B")

    session_a = await recorder.replay_agent("agent-A")
    session_b = await recorder.replay_agent("agent-B")

    assert len(session_a.steps) == 2
    assert len(session_b.steps) == 3
    assert all(s.agent_id == "agent-A" for s in session_a.steps)
    assert all(s.agent_id == "agent-B" for s in session_b.steps)
