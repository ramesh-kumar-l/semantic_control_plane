"""Pydantic models for the Agent Runtime.

All models are frozen (immutable) except `AgentState`, which is mutated by
the lifecycle manager as the agent progresses through its states.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from .enums import AgentStatus, ToolStatus


class AgentConfig(BaseModel):
    """Immutable configuration for a single agent instance."""

    model_config = ConfigDict(frozen=True)

    agent_id: str
    name: str
    max_steps: int = Field(default=50, ge=1, le=1000)
    max_context_items: int = Field(default=10, ge=1, le=100)
    context_hops: int = Field(default=1, ge=0, le=5)
    metadata: dict[str, str] = Field(default_factory=dict)


class ContextItem(BaseModel):
    """One entity retrieved and trust-assessed for a step's context window."""

    model_config = ConfigDict(frozen=True)

    entity_id: str
    name: str
    content_summary: str
    trust_score: float  # from TrustEngine.assess — real, source-aware score
    explanation: str  # human-readable reconstruction of the trust score


class AgentContext(BaseModel):
    """The assembled context window for one agent step."""

    model_config = ConfigDict(frozen=True)

    query: str
    items: list[ContextItem]
    assembled_at: datetime


class ToolCall(BaseModel):
    """A request to invoke a named tool."""

    model_config = ConfigDict(frozen=True)

    call_id: str
    tool_name: str
    input: str


class ToolResult(BaseModel):
    """The outcome of a single tool invocation."""

    model_config = ConfigDict(frozen=True)

    call_id: str
    tool_name: str
    input: str
    output: str | None
    status: ToolStatus
    error: str | None = None
    latency_ms: float


class AgentStep(BaseModel):
    """One completed execution step: context assembled + tools invoked."""

    model_config = ConfigDict(frozen=True)

    step_id: str
    agent_id: str
    query: str
    context: AgentContext
    tool_results: list[ToolResult]
    created_at: datetime


class AgentState(BaseModel):
    """Mutable runtime state for an agent instance (owned by `AgentLifecycle`)."""

    agent_id: str
    status: AgentStatus
    config: AgentConfig
    steps: list[AgentStep] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
    error: str | None = None
