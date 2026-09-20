"""Agent Runtime (Phase 5) — context assembly, tool invocation, memory access,
and agent lifecycle management over Phases 1–4.

The `AgentRuntime` is the single entry point: create an agent, run steps
(each step assembles context from the Knowledge Graph via the Semantic Query
Engine, invokes tools, and persists the outcome to Memory Core), and manage
the agent's lifecycle (pause, resume, stop).

Public API surface (`02-system-architecture.md` boundary; protected by `99` §3).
See `adr/ADR-006-agent-runtime.md`.
"""

from __future__ import annotations

from .context import ContextAssembler
from .enums import AgentStatus, ToolStatus
from .errors import (
    AgentNotFoundError,
    AgentNotRunningError,
    AgentRuntimeError,
    ContextAssemblyError,
    InvalidAgentTransitionError,
    MaxStepsExceededError,
    ToolInvocationError,
    ToolNotFoundError,
)
from .lifecycle import AgentLifecycle
from .models import (
    AgentConfig,
    AgentContext,
    AgentState,
    AgentStep,
    ContextItem,
    ToolCall,
    ToolResult,
)
from .runtime import AgentRuntime
from .tools import Tool, ToolRegistry

__all__ = [
    # Primary service
    "AgentRuntime",
    # Supporting services
    "ContextAssembler",
    "ToolRegistry",
    "AgentLifecycle",
    # Protocol
    "Tool",
    # Models
    "AgentConfig",
    "AgentContext",
    "AgentState",
    "AgentStep",
    "ContextItem",
    "ToolCall",
    "ToolResult",
    # Enums
    "AgentStatus",
    "ToolStatus",
    # Errors
    "AgentRuntimeError",
    "AgentNotFoundError",
    "AgentNotRunningError",
    "ToolNotFoundError",
    "ToolInvocationError",
    "InvalidAgentTransitionError",
    "MaxStepsExceededError",
    "ContextAssemblyError",
]
