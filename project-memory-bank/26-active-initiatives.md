# 26 — Active Initiatives

> This file is the canonical **active-context** record for SCP.

_Last updated: 2026-06-20 (Phase 6)_

## Active
### INIT-008 — Phase 7 Governance Layer
- **Status:** Implemented — **awaiting Phase Gate approval.**
- **Delivered:** `scp/governance/` package; `PolicyEngine` (trust threshold + verification status
  conditions; AND logic; CONTEXT_ITEM + AGENT_STEP scope); `AuditLogger` (immutable
  `AuditEvent` records; compliance report); `GovernanceLayer` service (single entry point:
  policy CRUD + govern_context_item + govern_step + audit trail + compliance_report);
  `PolicyStore` + `AuditStore` ports + `InMemoryPolicyStore` + `InMemoryAuditStore` backends.
- **Decoupling:** accepts Phase 5 public models (`ContextItem`, `AgentStep`); verification
  status passed explicitly by caller. No Phase 1–6 code modified.
- **Exit met:** policy gates enforced on trust thresholds + verification status; full audit
  trail; compliance report (DENY=violation, WARN=warning, REQUIRE_REVIEW=review_required);
  37 governance tests (engine ×11, audit ×7, governance ×10, integration ×5); 221 total; 0
  regressions.
- **Decision recorded:** ADR-008.

## Completed
### INIT-007 — Phase 6 Agent Flight Recorder
- **Status:** Complete (Phase Gate approved by user directing Phase 7).
- `scp/recorder/` package; `ReplayEngine` + `TraceEngine` + `DebugEngine` + `FlightRecorder`;
  `RecordStore` port + `InMemoryRecordStore`. Additive — Phase 5 unchanged. ADR-007.
### INIT-006 — Phase 5 Agent Runtime
- **Status:** Complete (Phase Gate approved by user directing Phase 6).
- `scp/agent/` package; `ContextAssembler` + `ToolRegistry` + `AgentLifecycle` + `AgentRuntime`;
  EPISODIC memory persistence per step; real TrustEngine scores in every ContextItem. ADR-006.
### INIT-005 — Phase 4 Trust Engine
- **Status:** Complete (Phase Gate approved by user proceeding to Phase 5).
- `scp/trust/` package; `SourceRegistry`; `ConfidenceModel` (replaces 0.5); explainable
  weighted-blend scoring; `VerificationPolicy` state machine; `ContradictionDetector`;
  `TrustEngine` service (pure, synchronous, no I/O). 0.5 placeholder replaced additively
  via `confidence_model` callable on `MemoryCore`/`KnowledgeGraph`. ADR-005.
### INIT-004 — Phase 3 Semantic Query Engine
- **Status:** Complete (Phase Gate approved). `scp/query/` package; `Embedder` port +
  `HashingEmbedder`; `VectorStore` port + `InMemoryVectorStore`; rule-based planner;
  trust-aware explainable ranking; `SemanticQueryEngine` hybrid retrieval. Exit met:
  hybrid recall@5 = 1.0 vs vector-only baseline 0.0. ADR-004.
### INIT-003 — Phase 2 Knowledge Graph
- **Status:** Complete (Phase Gate approved). `GraphStore` port + adapters; `Entity` +
  `Relationship` reusing Phase 1 trust/temporal; pure BFS traversal; `KnowledgeGraph`
  service with cascade-delete. ADR-003.
### INIT-002 — Phase 1 Memory Core: Scaffold & First Slice
- **Status:** Complete (Phase Gate approved). `MemoryStore` port + adapters; `MemoryCore`
  service; trust + temporal on every record. ADR-002.
### INIT-001 — Bootstrap Memory Bank
- **Status:** Complete. Established the memory bank + Python stack. ADR-001.

## Next Candidate (awaiting approval)
### INIT-009 — Future phases (Observability Engine, Developer Console, etc.)
- **Status:** Not planned — SCP phases 0-7 are now complete pending gate approvals.
- Durable backend adapters (SqliteAuditStore, SqliteRecordStore, SqliteAgentStore).
- Role-based access control on governance API.
- Pre-built compliance policy bundles (GDPR baseline, high-trust-only).

## Backlog (not scheduled)
- Learned `Embedder`, ANN/pgvector `VectorStore`, Postgres / native-graph adapters (future ADRs).
- Tool timeout enforcement (follow-up from ADR-006).
- Durable `AgentStore` port + adapter (follow-up from ADR-006).
- `SqliteRecordStore` durable backend (follow-up from ADR-007).
- Auto-record hook on `AgentRuntime` (follow-up from ADR-007).
