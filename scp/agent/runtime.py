"""`AgentRuntime` — the public service API for Phase 5 Agent Runtime.

Ties together context assembly (Phase 3+4), tool invocation, memory
persistence (Phase 1), and agent lifecycle management into a single
coherent service.

Every agent step:
  1. Assembles context from the Knowledge Graph via the Semantic Query Engine,
     with trust scores from the Trust Engine.
  2. Invokes any requested tools (errors are non-fatal; captured in results).
  3. Persists the step summary to Memory Core as EPISODIC memory.

Boundaries (`02-system-architecture.md`): the runtime uses only public APIs
from Phases 1–4; it never reaches into their internal storage directly.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from scp.memory import MemoryCore, MemoryType, SourceType
from scp.trust import TrustEngine

from .context import ContextAssembler
from .enums import AgentStatus
from .errors import AgentNotRunningError, MaxStepsExceededError
from .lifecycle import AgentLifecycle
from .models import AgentConfig, AgentState, AgentStep, ToolCall, ToolResult
from .tools import ToolRegistry

# Statuses from which a new step is allowed.
_RUNNABLE: frozenset[AgentStatus] = frozenset({AgentStatus.IDLE, AgentStatus.RUNNING})


class AgentRuntime:
    """Phase 5 service: context assembly, tool invocation, memory access, lifecycle."""

    def __init__(
        self,
        memory: MemoryCore,
        assembler: ContextAssembler,
        trust_engine: TrustEngine,
        *,
        tool_registry: ToolRegistry | None = None,
        lifecycle: AgentLifecycle | None = None,
    ) -> None:
        self._memory = memory
        self._assembler = assembler
        self._trust = trust_engine
        self._tools = tool_registry if tool_registry is not None else ToolRegistry()
        self._lifecycle = lifecycle if lifecycle is not None else AgentLifecycle()

    @property
    def tools(self) -> ToolRegistry:
        """The tool registry — register tools before calling `run_step`."""
        return self._tools

    # --- Lifecycle management ---------------------------------------------

    def create_agent(self, config: AgentConfig) -> AgentState:
        """Register a new agent in the IDLE state."""
        return self._lifecycle.create(config)

    def get_agent(self, agent_id: str) -> AgentState:
        """Return the current state. Raises `AgentNotFoundError` if unknown."""
        return self._lifecycle.get(agent_id)

    def pause_agent(self, agent_id: str) -> AgentState:
        return self._lifecycle.transition(agent_id, AgentStatus.PAUSED)

    def resume_agent(self, agent_id: str) -> AgentState:
        return self._lifecycle.transition(agent_id, AgentStatus.RUNNING)

    def stop_agent(self, agent_id: str) -> AgentState:
        return self._lifecycle.transition(agent_id, AgentStatus.STOPPED)

    # --- Step execution ---------------------------------------------------

    async def run_step(
        self,
        agent_id: str,
        query: str,
        *,
        tool_calls: list[ToolCall] | None = None,
    ) -> AgentStep:
        """Execute one agent step.

        Raises `AgentNotRunningError` if the agent is not in a runnable state.
        Raises `MaxStepsExceededError` and transitions to FAILED when the step
        budget is exhausted.
        """
        state = self._lifecycle.get(agent_id)
        if state.status not in _RUNNABLE:
            raise AgentNotRunningError(
                f"Agent {agent_id!r} is {state.status!r}; cannot start a step"
            )
        if len(state.steps) >= state.config.max_steps:
            self._lifecycle.transition(agent_id, AgentStatus.FAILED, error="max_steps exceeded")
            raise MaxStepsExceededError(
                f"Agent {agent_id!r} reached max_steps={state.config.max_steps}"
            )

        self._lifecycle.transition(agent_id, AgentStatus.RUNNING)
        now = datetime.now(UTC)

        context = await self._assembler.assemble(
            query,
            max_items=state.config.max_context_items,
            expand_hops=state.config.context_hops,
            now=now,
        )

        results: list[ToolResult] = []
        for call in tool_calls or []:
            result = await self._tools.invoke(call, context=context)
            results.append(result)

        step = AgentStep(
            step_id=uuid.uuid4().hex,
            agent_id=agent_id,
            query=query,
            context=context,
            tool_results=results,
            created_at=now,
        )
        state.steps.append(step)
        state.updated_at = now

        await self._persist_step(step, state.config.name)
        return step

    async def _persist_step(self, step: AgentStep, agent_name: str) -> None:
        """Write the step summary to MemoryCore as EPISODIC memory."""
        content = f"[agent:{agent_name}] step={step.step_id[:8]} query={step.query!r}"
        if step.tool_results:
            tool_names = ", ".join(r.tool_name for r in step.tool_results)
            content += f" tools=[{tool_names}]"
        if step.context.items:
            top = step.context.items[0]
            content += f" top_context={top.name!r}(trust={top.trust_score:.3f})"
        await self._memory.store(
            content,
            memory_type=MemoryType.EPISODIC,
            source_type=SourceType.AGENT,
        )
