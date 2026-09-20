"""Tool Protocol and ToolRegistry for the Agent Runtime.

Tools are pure async callables behind a structural protocol — no inheritance
required. The registry records timing and converts raised exceptions into
`ToolResult(status=ERROR)` so agent steps always complete (non-fatal tool errors).
"""

from __future__ import annotations

import time
from typing import Protocol, runtime_checkable

from .enums import ToolStatus
from .errors import ToolNotFoundError
from .models import AgentContext, ToolCall, ToolResult


@runtime_checkable
class Tool(Protocol):
    """Structural protocol for agent tools.

    Implementors need only a `name` str property, a `description` str property,
    and an async `invoke` method — no base class required.
    """

    @property
    def name(self) -> str: ...

    @property
    def description(self) -> str: ...

    async def invoke(self, input: str, *, context: AgentContext) -> str:
        """Execute the tool and return its string output."""
        ...


class ToolRegistry:
    """Registry of tools available to agents in this runtime."""

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        """Add or replace a tool by name."""
        self._tools[tool.name] = tool

    def names(self) -> list[str]:
        """Sorted list of registered tool names."""
        return sorted(self._tools)

    def get(self, name: str) -> Tool:
        """Return the tool, or raise `ToolNotFoundError`."""
        try:
            return self._tools[name]
        except KeyError:
            raise ToolNotFoundError(f"Tool {name!r} is not registered") from None

    async def invoke(self, call: ToolCall, *, context: AgentContext) -> ToolResult:
        """Invoke a tool by name, capturing errors as non-fatal ToolResult(ERROR)."""
        tool = self.get(call.tool_name)
        start = time.perf_counter()
        try:
            output = await tool.invoke(call.input, context=context)
            latency = (time.perf_counter() - start) * 1000.0
            return ToolResult(
                call_id=call.call_id,
                tool_name=call.tool_name,
                input=call.input,
                output=output,
                status=ToolStatus.SUCCESS,
                latency_ms=latency,
            )
        except Exception as exc:
            latency = (time.perf_counter() - start) * 1000.0
            return ToolResult(
                call_id=call.call_id,
                tool_name=call.tool_name,
                input=call.input,
                output=None,
                status=ToolStatus.ERROR,
                error=str(exc),
                latency_ms=latency,
            )
