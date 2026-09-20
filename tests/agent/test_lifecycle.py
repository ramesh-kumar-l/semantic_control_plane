"""Unit tests for AgentLifecycle state management."""

from __future__ import annotations

import pytest

from scp.agent.enums import AgentStatus
from scp.agent.errors import AgentNotFoundError, InvalidAgentTransitionError
from scp.agent.lifecycle import AgentLifecycle
from scp.agent.models import AgentConfig


def _cfg(agent_id: str = "a1") -> AgentConfig:
    return AgentConfig(agent_id=agent_id, name="test-agent")


def test_create_yields_idle_state() -> None:
    lc = AgentLifecycle()
    state = lc.create(_cfg())
    assert state.status == AgentStatus.IDLE
    assert state.agent_id == "a1"
    assert state.steps == []


def test_get_returns_same_state() -> None:
    lc = AgentLifecycle()
    created = lc.create(_cfg())
    assert lc.get("a1") is created


def test_get_unknown_raises() -> None:
    lc = AgentLifecycle()
    with pytest.raises(AgentNotFoundError):
        lc.get("ghost")


def test_valid_transition_idle_to_running() -> None:
    lc = AgentLifecycle()
    lc.create(_cfg())
    state = lc.transition("a1", AgentStatus.RUNNING)
    assert state.status == AgentStatus.RUNNING


def test_valid_transitions_paused_resumed_stopped() -> None:
    lc = AgentLifecycle()
    lc.create(_cfg())
    lc.transition("a1", AgentStatus.RUNNING)
    lc.transition("a1", AgentStatus.PAUSED)
    assert lc.get("a1").status == AgentStatus.PAUSED
    lc.transition("a1", AgentStatus.RUNNING)
    lc.transition("a1", AgentStatus.STOPPED)
    assert lc.get("a1").status == AgentStatus.STOPPED


def test_invalid_transition_raises() -> None:
    lc = AgentLifecycle()
    lc.create(_cfg())
    with pytest.raises(InvalidAgentTransitionError):
        lc.transition("a1", AgentStatus.STOPPED)  # IDLE → STOPPED is not allowed


def test_transition_to_same_status_is_idempotent() -> None:
    lc = AgentLifecycle()
    lc.create(_cfg())
    lc.transition("a1", AgentStatus.RUNNING)
    state = lc.transition("a1", AgentStatus.RUNNING)
    assert state.status == AgentStatus.RUNNING


def test_failed_transition_records_error() -> None:
    lc = AgentLifecycle()
    lc.create(_cfg())
    lc.transition("a1", AgentStatus.RUNNING)
    state = lc.transition("a1", AgentStatus.FAILED, error="max_steps exceeded")
    assert state.status == AgentStatus.FAILED
    assert state.error == "max_steps exceeded"


def test_remove_silently_ignores_unknown() -> None:
    lc = AgentLifecycle()
    lc.remove("ghost")  # should not raise


def test_all_agents_returns_all() -> None:
    lc = AgentLifecycle()
    lc.create(_cfg("a1"))
    lc.create(_cfg("a2"))
    assert len(lc.all_agents()) == 2
