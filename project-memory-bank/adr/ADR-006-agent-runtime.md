# ADR-006 — Agent Runtime Architecture

**Status:** Accepted  
**Date:** 2026-06-20  
**Phase:** 5

---

## Context

Phase 5 requires an Agent Runtime capable of:
1. **Context assembly** — pulling relevant knowledge from the graph, ranked and trust-assessed.
2. **Tool invocation** — dispatching named tools with the assembled context.
3. **Memory access** — reading from and writing to persistent memory.
4. **Agent lifecycle** — managing agent state (IDLE / RUNNING / PAUSED / STOPPED / FAILED).

The runtime sits above Phases 1–4 and must consume them exclusively via public APIs.

---

## Problem

How to design a runtime that:
- Uses Phases 1–4 (Memory, Graph, Query, Trust) without collapsing their boundaries.
- Supports structured tool invocation without coupling tools to the runtime.
- Persists agent activity to memory for auditability and future retrieval.
- Enforces a safe lifecycle state machine that prevents invalid transitions.

---

## Decision

### 1. Three-layer decomposition
- **`ContextAssembler`** — single responsibility: semantic search + trust assessment per result.
  Receives `SemanticQueryEngine`, `TrustEngine`, and `KnowledgeGraph`; returns `AgentContext`.
- **`ToolRegistry`** — a structural protocol (`Tool`) + registry. Tools are pure async callables.
  Errors are non-fatal: captured in `ToolResult(status=ERROR)`.
- **`AgentLifecycle`** — enforces the documented transition graph:
  `IDLE→RUNNING`, `RUNNING→{PAUSED,STOPPED,FAILED}`, `PAUSED→{RUNNING,STOPPED}`.
- **`AgentRuntime`** — composes the three, implements `run_step`, and persists steps to MemoryCore.

### 2. All cross-module access via public APIs
`ContextAssembler` calls `SemanticQueryEngine.search()`, then `KnowledgeGraph.get_entity()` for
each result, then `TrustEngine.assess()`. No boundary crossing (`02-system-architecture.md`).

### 3. Step persistence as EPISODIC memory
Each `run_step` writes a structured summary to `MemoryCore` with `MemoryType.EPISODIC` and
`SourceType.AGENT`. This makes agent activity retrievable by the Query Engine in future steps.

### 4. In-memory lifecycle for Phase 5
`AgentLifecycle` is pure in-memory. A durable `AgentStore` port can be introduced in a
future phase behind the same `AgentRuntime` API (Extension > Modification, `99` §3).

### 5. Tool errors are non-fatal
`ToolRegistry.invoke()` catches all tool exceptions and converts them to `ToolResult(ERROR)`.
The step completes; the error is observable in `step.tool_results`.

---

## Alternatives Considered

| Alternative | Why Rejected |
|---|---|
| Single monolithic `AgentRuntime` class | Violates one-class-one-responsibility; untestable in isolation |
| Agent writes directly to graph store | Boundary violation — storage access must go through service APIs |
| Raise on tool error | Agents should be resilient; individual tool failure ≠ step failure |
| Persist steps to a separate AgentStore | Overkill for Phase 5; EPISODIC memory already exists and is query-able |

---

## Tradeoffs

- **In-memory lifecycle**: simple and fast, but does not survive process restart. Acceptable for
  Phase 5; a durable store is a follow-up behind the same API.
- **EPISODIC persistence**: step summaries are compact strings; full structured step data is
  held in `AgentState.steps`. If the process restarts, in-flight state is lost (same caveat).
- **Non-fatal tool errors**: reduces observability (must inspect `tool_results`), but prevents
  one flaky tool from halting the agent step.

---

## Consequences

- `AgentRuntime`, `ContextAssembler`, `ToolRegistry`, `AgentLifecycle` public APIs are now
  **protected** — changes require an ADR (`99` §3).
- All agent activity is auditable via `MemoryCore` EPISODIC query.
- Trust scores in context items use `TrustEngine.assess()` — the full weighted blend with
  recency and verification gate, not the flat 0.5 placeholder.

---

## Follow-up

- Durable `AgentStore` port + adapter (Phase 6 or beyond).
- Agent-to-agent communication (future ADR).
- Tool timeout enforcement (currently no deadline; add in a follow-up).
- Context ranking could weight by recency of the entity's memory reference.
