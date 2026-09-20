# 02 — System Architecture (Canonical)

> Canonical module boundaries. **Never merge responsibilities. Never collapse layers.** Changes here require explicit approval and an ADR.

## Module Map
```
SCP
├── Memory Core            # storage, retrieval, consolidation, compression, lifecycle
├── Knowledge Graph        # entities, relationships, graph storage & traversal
├── Semantic Query Engine  # hybrid retrieval, vector + graph search, ranking, planning
├── Trust Engine           # trust scores, confidence, source tracking, verification, contradiction
├── Agent Runtime          # context assembly, tool invocation, memory access, lifecycle
├── Agent Flight Recorder  # replay, debugging, traceability, root-cause analysis
├── Governance Layer       # policies, compliance, controls, auditing
├── Policy Engine          # policy evaluation & enforcement
├── Observability Engine   # metrics, traces, logs, system health
└── Developer Console      # UI surfaces over all of the above
```

## Boundary Rules
- Each module owns one responsibility. No module reaches into another's storage directly — cross-module interaction is via defined interfaces only.
- Trust is not a module add-on; trust metadata travels *with* memories and facts (see `11-memory-model.md`, `14-trust-model.md`).
- Observability and Governance are cross-cutting but remain distinct modules with their own boundaries.

## Technology Stack (DECIDED — see `adr/ADR-001-python-stack.md`)
- **Language:** Python 3.12+, async-first.
- **Models/validation:** `pydantic` v2.
- **Service layer:** `FastAPI`-style boundaries for any service surface.
- **Testing:** `pytest`. **Tooling:** `ruff` (lint/format), `mypy --strict`.
- Storage choices (vector DB, graph store, KV) are **deferred** to Phase 1+ design and will be recorded via ADR when selected.

## Non-Functional Requirements (targets)
- **Performance:** P95 query latency < 150ms; predictable memory usage; horizontal scalability.
- **Availability/Edge:** offline-first support; deterministic behaviour.
- **Security:** encryption, authentication, authorization, auditability, least privilege, privacy by default.
- **Explainability:** every decision reconstructable via the Flight Recorder.

> Optimize only after correctness. Performance work follows working, tested code.
