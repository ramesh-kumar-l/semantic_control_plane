# 04 — Roadmap

> Work strictly phase-by-phase. Never implement future-phase features. Each phase ends with the **Phase Gate Protocol**.

## Phase Status Overview
| Phase | Name | Status |
|---|---|---|
| 0 | Memory Bank Bootstrap | **Complete** |
| 1 | Memory Core | **Complete — Phase Gate approved** |
| 2 | Knowledge Graph | **Complete — Phase Gate approved** |
| 3 | Semantic Query Engine | **Complete — Phase Gate approved** |
| 4 | Trust Engine | **Complete — Phase Gate approved** |
| 5 | Agent Runtime | **Complete — Phase Gate approved** |
| 6 | Agent Flight Recorder | **Complete — Phase Gate approved** |
| 7 | Governance Layer | **Implemented — awaiting Phase Gate approval** |

## Phase 1 — Memory Core
Capabilities: Memory Storage · Retrieval · Consolidation · Compression · Lifecycle Management.
Trust metadata (source, provenance, confidence, verification, temporal context) is built in from
the start. Implemented under `scp/memory/` (ADR-002).

## Phase 2 — Knowledge Graph
Entity Management · Relationship Management · Graph Storage · Graph Traversal · Graph Query Engine.
Implemented under `scp/graph/` behind a `GraphStore` port (ADR-003); entities and
relationships carry the same first-class trust primitives as memories. Traversal is
application-side BFS (`breadth_first`, `shortest_path`).

## Phase 3 — Semantic Query Engine
Hybrid Retrieval · Vector Search · Graph Search · Ranking · Query Planning.
Implemented under `scp/query/` (ADR-004): deterministic offline `HashingEmbedder` behind
an `Embedder` port; `InMemoryVectorStore` behind a `VectorStore` port; hybrid retrieval =
vector seeds expanded via Phase 2 `traverse`; trust-aware explainable ranking; rule-based
planner. Exit met: hybrid recall@5 = 1.0 vs vector-only 0.0.

## Phase 4 — Trust Engine
Trust Scores · Confidence Models · Source Tracking · Verification · Contradiction Detection.
Implemented under `scp/trust/` (ADR-005) as a pure, synchronous, deterministic engine:
`SourceRegistry`, `ConfidenceModel` (real per-source confidence — replaces 0.5 placeholder),
explainable weighted-blend scoring, `VerificationPolicy` state machine, `ContradictionDetector`.
Injected additively into Phase 1/2 via `confidence_model` callable.
Exit met: scores explainable/reproducible; placeholder gone when engine is wired.

## Phase 5 — Agent Runtime
Context Assembly · Tool Invocation · Memory Access · Agent Lifecycle.
Implemented under `scp/agent/` (ADR-006): `ContextAssembler` (semantic search + trust
assessment per result), `ToolRegistry` (structural `Tool` protocol; non-fatal errors),
`AgentLifecycle` (enforces transition graph), `AgentRuntime` service (run_step persists to
EPISODIC memory; full lifecycle management). Uses Phases 1–4 exclusively via public APIs.
Exit criteria: agent reads graph, writes memory, carries real trust scores, full lifecycle
exercised, 35 agent tests pass; **awaiting Phase Gate approval**.

## Phase 6 — Agent Flight Recorder
Replay · Debugging · Traceability · Root Cause Analysis.
Every agent decision reconstructable from recorded evidence.
Implemented under `scp/recorder/` (ADR-007): `ReplayEngine` (ordered step replay),
`TraceEngine` (entity → step linkage), `DebugEngine` (root-cause reports),
`FlightRecorder` service (single entry point). Additive — Phase 5 unchanged.
Exit criteria: any agent decision replayable from recorded steps; root-cause debuggable;
all tests pass; **awaiting Phase Gate approval**.

## Phase 7 — Governance Layer
Policies · Compliance · Controls · Auditing.
Exit criteria: policy gates enforced on trust thresholds/verification status; full audit
trail; compliance controls implemented; all tests pass; gate approved.

## Phase Gate Protocol
At the end of every phase, STOP and produce:
**What Was Implemented · Design Review · Risks · Technical Debt · Test Results · Documentation Updates · Recommended Next Steps**, then ask **"Approve Phase Completion?"** and wait for approval before continuing.
