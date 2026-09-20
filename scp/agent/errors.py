"""Typed exceptions for the Agent Runtime (`02-system-architecture.md` boundary)."""

from __future__ import annotations


class AgentRuntimeError(Exception):
    """Base for all Agent Runtime errors."""


class AgentNotFoundError(AgentRuntimeError):
    """Raised when an agent_id is not registered in the lifecycle store."""


class AgentNotRunningError(AgentRuntimeError):
    """Raised when run_step is called on an agent that is not IDLE or RUNNING."""


class ToolNotFoundError(AgentRuntimeError):
    """Raised when an unregistered tool name is requested."""


class ToolInvocationError(AgentRuntimeError):
    """Raised when tool invocation fails at the infrastructure level (not tool errors)."""


class InvalidAgentTransitionError(AgentRuntimeError):
    """Raised when an illegal lifecycle transition is attempted."""


class MaxStepsExceededError(AgentRuntimeError):
    """Raised when an agent exceeds its configured `max_steps` limit."""


class ContextAssemblyError(AgentRuntimeError):
    """Raised when context assembly fails (e.g., retrieval or graph lookup error)."""
