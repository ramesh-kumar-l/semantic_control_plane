"""Pydantic models for the Agent Flight Recorder.

All models are frozen (immutable). The recorder takes snapshots of agent
steps; those snapshots must never mutate after the fact so replays are
deterministic.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from scp.agent.models import AgentContext, ContextItem, ToolResult


class RecordedStep(BaseModel):
    """Persisted, queryable snapshot of one `AgentStep`."""

    model_config = ConfigDict(frozen=True)

    record_id: str
    agent_id: str
    agent_name: str
    step_id: str
    step_index: int  # 0-based position within the agent's step history
    query: str
    context_snapshot: AgentContext  # full context window at execution time
    tool_results: list[ToolResult]
    created_at: datetime  # when the step executed
    recorded_at: datetime  # when this record was stored


class RecordQuery(BaseModel):
    """Filter for querying the record store."""

    model_config = ConfigDict(frozen=True)

    agent_id: str | None = None
    step_id: str | None = None
    entity_id: str | None = None  # steps whose context referenced this entity
    created_after: datetime | None = None
    created_before: datetime | None = None
    max_results: int = Field(default=100, ge=1)


class ReplaySession(BaseModel):
    """An ordered reconstruction of an agent's step history."""

    model_config = ConfigDict(frozen=True)

    session_id: str
    agent_id: str
    steps: list[RecordedStep]
    from_index: int
    to_index: int
    created_at: datetime


class TraceAppearance(BaseModel):
    """One occurrence of an entity in a recorded step's context window."""

    model_config = ConfigDict(frozen=True)

    step_id: str
    step_index: int
    query: str
    trust_score: float
    explanation: str
    created_at: datetime


class Trace(BaseModel):
    """All appearances of one entity across recorded steps."""

    model_config = ConfigDict(frozen=True)

    trace_id: str
    entity_id: str
    entity_name: str
    agent_id: str | None  # None when tracing across all agents
    appearances: list[TraceAppearance]


class RootCauseReport(BaseModel):
    """Structured explanation of what drove a specific agent step."""

    model_config = ConfigDict(frozen=True)

    report_id: str
    step_id: str
    agent_id: str
    query: str
    top_context_items: list[ContextItem]  # sorted by trust_score descending
    tool_outcomes: list[ToolResult]
    trust_signals: list[str]  # explanation strings from top_context_items
    related_step_ids: list[str]  # other steps sharing at least one context entity
    created_at: datetime
