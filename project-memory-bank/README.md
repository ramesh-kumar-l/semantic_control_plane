# Project Memory Bank

The **primary source of truth** for the Semantic Control Plane (SCP). Never assume — retrieve context here before planning or implementing.

## Loading Protocol
1. Determine what information the task requires and which files contain it.
2. Load **only** the minimum required files (token efficiency is mandatory).
3. Summarize findings, then plan.

## Loading Priority
1. `99-development-rules.md` — mandatory rules (load first, always).
2. `03-current-state.md` — what exists right now.
3. `02-system-architecture.md` — canonical module boundaries.
4. Relevant domain file — `11-memory-model.md` / `14-trust-model.md` / `18-ui-design-system.md`.
5. `30-session-handoff.md` — continuity & next actions.

## Index
### Strategic Layer
- `00-project-vision.md` — vision, mission, customers, long-term goals.
- `01-strategic-thesis.md` — core thesis & market reasoning.
- `02-system-architecture.md` — canonical architecture & module boundaries (Python stack).
- `04-roadmap.md` — 7-phase roadmap, status, phase-gate protocol.

### Execution Layer
- `03-current-state.md` — current implementation status.
- `26-active-initiatives.md` — current & next workstreams.
- `30-session-handoff.md` — session continuity & next actions.

### Domain Layer
- `11-memory-model.md` — memory architecture & lifecycle.
- `14-trust-model.md` — trust scoring & verification.
- `18-ui-design-system.md` — frontend/UX standards.

### Governance Layer
- `99-development-rules.md` — engineering/testing/architecture/security/phase-gate standards.

### Decision Records
- `adr/ADR-000-template.md` — ADR template.
- `adr/ADR-001-python-stack.md` — Python chosen as implementation stack.
- `adr/ADR-002-memory-core-storage.md` — SQLite behind a `MemoryStore` port (Phase 1).
- `adr/ADR-003-knowledge-graph-storage.md` — SQLite + app-side BFS behind a `GraphStore` port (Phase 2).
- `adr/ADR-004-semantic-query-engine.md` — hashing embedder + cosine index + hybrid retrieval behind `Embedder`/`VectorStore` ports (Phase 3).
- `adr/ADR-005-trust-engine.md` — explainable trust scoring + confidence model + verification policy + contradiction detection; replaces the 0.5 placeholder via additive `confidence_model` injection (Phase 4).

> Keep these files synchronized with implementation progress. Update `03`, `26`, and `30` at the end of each session.
