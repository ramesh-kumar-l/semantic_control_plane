# ADR-007 — Agent Flight Recorder Architecture

**Date:** 2026-06-20  
**Status:** Accepted  
**Phase:** 6

## Context

Phase 5 introduced `AgentRuntime`, which records each step to `MemoryCore` as EPISODIC
memory. That gives us a searchable prose log, but it does not support:
- Ordered step-by-step **replay** of an agent's history
- **Tracing** a context entity across multiple steps ("what did the agent know about X and when?")
- **Root-cause analysis** explaining why a specific step produced its outcome

## Problem

How do we make every agent decision reconstructable, debuggable, and traceable from
recorded evidence — without modifying Phase 5 code or coupling the recorder to agent internals?

## Decision

Implement `scp/recorder/` as a standalone Phase 6 module with a **three-engine decomposition**:

| Engine | Responsibility |
|---|---|
| `ReplayEngine` | Reconstructs ordered step histories from the `RecordStore` |
| `TraceEngine` | Links entity_ids to the steps that referenced them |
| `DebugEngine` | Synthesises `RootCauseReport` from step evidence |

`FlightRecorder` composes all three behind a single service entry point.

**Decoupling mechanism:** `FlightRecorder.record(step, *, agent_name, step_index)` accepts
the `AgentStep` returned by `AgentRuntime.run_step()` and snapshots it into a `RecordedStep`.
The caller (application layer) decides when to record — the recorder never touches the runtime.

**`RecordStore` port:** same hexagonal pattern as Phase 1–4 stores. `InMemoryRecordStore`
ships for dev/test; a durable adapter (SQLite/Postgres) is deferred.

## Alternatives Rejected

| Alternative | Why rejected |
|---|---|
| Modify `AgentRuntime` to auto-record inside `run_step` | Violates Phase 5 boundary; couples recorder lifecycle to runtime |
| Derive replay from EPISODIC `MemoryCore` records | Prose strings can't reconstruct typed context/trust/tool data reliably |
| Single monolithic `FlightRecorder` class | Exceeds 300-line limit; harder to test each concern in isolation |

## Models

- `RecordedStep` — immutable snapshot of one `AgentStep` (frozen pydantic).
- `ReplaySession` — ordered list of `RecordedStep` with index bounds.
- `TraceAppearance` — one occurrence of an entity in a step's context window.
- `Trace` — all appearances of an entity, optionally scoped to one agent.
- `RootCauseReport` — top context items (by trust), tool outcomes, trust signals,
  related step_ids that share at least one context entity.

## Tradeoffs

| + | - |
|---|---|
| Recorder fully independent of runtime — can be added/removed without side effects | Caller must explicitly call `recorder.record()` after each step |
| Three-engine split keeps each file < 120 lines | Three separate classes vs one class (more files) |
| `RecordStore` port allows future durable adapter | In-memory store loses data on restart |
| Conditional `trace_entity` assertion in integration test handles retrieval variability | Integration tests slightly weaker for trace when hash embedder doesn't overlap |

## Consequences

- `FlightRecorder`, `ReplayEngine`, `TraceEngine`, `DebugEngine`, `RecordStore`,
  `InMemoryRecordStore`, and all models join the protected API surface (`99` §3).
- Phase 5 code is **unchanged** — additive only.
- Durable `RecordStore` adapter (e.g., `SqliteRecordStore`) is a future ADR.

## Follow-up

- Durable `SqliteRecordStore` backend (ADR-008 candidate).
- `FlightRecorder` integration with `AgentRuntime` via optional hook parameter (ADR candidate).
- Export replay sessions and root-cause reports as structured JSON for tooling.
