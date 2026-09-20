"""Unit tests for the Tool protocol and ToolRegistry."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from scp.agent.enums import ToolStatus
from scp.agent.errors import ToolNotFoundError
from scp.agent.models import AgentContext, ToolCall
from scp.agent.tools import Tool, ToolRegistry


def _ctx() -> AgentContext:
    return AgentContext(query="q", items=[], assembled_at=datetime.now(UTC))


class EchoTool:
    name = "echo"
    description = "Echoes the input unchanged."

    async def invoke(self, input: str, *, context: AgentContext) -> str:
        return f"echo: {input}"


class FailTool:
    name = "fail"
    description = "Always raises."

    async def invoke(self, input: str, *, context: AgentContext) -> str:
        raise ValueError("deliberate failure")


def test_tool_satisfies_protocol() -> None:
    assert isinstance(EchoTool(), Tool)


def test_register_and_list_names() -> None:
    reg = ToolRegistry()
    reg.register(EchoTool())
    assert "echo" in reg.names()


def test_get_unknown_raises() -> None:
    reg = ToolRegistry()
    with pytest.raises(ToolNotFoundError):
        reg.get("missing")


async def test_invoke_success_records_output_and_latency() -> None:
    reg = ToolRegistry()
    reg.register(EchoTool())
    call = ToolCall(call_id="c1", tool_name="echo", input="hello")
    result = await reg.invoke(call, context=_ctx())
    assert result.status == ToolStatus.SUCCESS
    assert result.output == "echo: hello"
    assert result.latency_ms >= 0.0
    assert result.error is None


async def test_invoke_tool_error_is_non_fatal() -> None:
    reg = ToolRegistry()
    reg.register(FailTool())
    call = ToolCall(call_id="c2", tool_name="fail", input="x")
    result = await reg.invoke(call, context=_ctx())
    assert result.status == ToolStatus.ERROR
    assert result.output is None
    assert "deliberate failure" in (result.error or "")


async def test_invoke_unregistered_raises_not_found() -> None:
    reg = ToolRegistry()
    call = ToolCall(call_id="c3", tool_name="ghost", input="y")
    with pytest.raises(ToolNotFoundError):
        await reg.invoke(call, context=_ctx())


def test_register_overwrites_same_name() -> None:
    class EchoV2:
        name = "echo"
        description = "v2"

        async def invoke(self, input: str, *, context: AgentContext) -> str:
            return f"v2: {input}"

    reg = ToolRegistry()
    reg.register(EchoTool())
    reg.register(EchoV2())
    assert len(reg.names()) == 1  # no duplicate
