# ADR-003 — Knowledge Graph Storage & Traversal

## Status
Accepted (2026-06-20)

## Context
Phase 2 (Knowledge Graph) introduces **entities** and **relationships** with graph
storage, traversal, and a basic query surface (`04-roadmap.md`,
`02-system-architecture.md`). It builds on Memory Core's interfaces and must keep the
same NFRs: offline-first, deterministic, ACID, P95 < 150ms, and trust metadata
travelling *with* every fact (`99` §8). Module boundaries hold: the Knowledge Graph
owns entities/relationships and graph traversal; it does **not** do semantic ranking
or vector search (Phase 3, Semantic Query Engine).

## Problem
How should the graph be persisted and traversed for Phase 2 without prematurely
adopting a native graph database before scale demands it, while staying consistent
with the `MemoryStore` port pattern (ADR-002)?

## Decision
1. Define a **`GraphStore` port** (abstract interface) the Knowledge Graph depends on.
   The service never talks to a concrete database directly (mirrors ADR-002).
2. Model the graph as two record types behind that port:
   - **`Entity`** — typed node with `name`, free-form string `properties`, optional
     `memory_refs` linking back to Memory Core records by id (no cross-module storage
     access — only id references).
   - **`Relationship`** — typed, optionally directed edge with `source_id`/`target_id`
     and string `properties`.
3. Ship two adapters in Phase 2:
   - **`InMemoryGraphStore`** — deterministic, no I/O, for tests/dev.
   - **`SqliteGraphStore`** (via `aiosqlite`) — durable default: two indexed tables
     (`entities`, `relationships`) plus a JSON `data` column for full-fidelity
     round-tripping, matching ADR-002's storage style.
4. **Traversal runs in application code** as breadth-first search over an adjacency
   primitive (`neighbors`) exposed by the port — *not* recursive SQL CTEs. This keeps
   traversal backend-agnostic, deterministic, depth-bounded, and unit-testable in
   isolation (pure `traversal.py` taking an async neighbour function).
5. **Trust primitives are reused, not duplicated.** `Entity`/`Relationship` carry the
   Phase 1 `TrustMetadata`/`TemporalContext`/`Source`/`ProvenanceEntry` value objects.
   Trust is one cross-cutting concept that travels with facts (`99` §8); duplicating
   it would violate that. These types are currently homed in `scp.memory`; a future
   refactor (Phase 4, Trust Engine) may relocate them to a shared trust package behind
   the same names.

## Alternatives
- **Native graph DB (Neo4j / Memgraph) now** — best traversal ergonomics at scale, but
  adds a heavyweight ops dependency and breaks offline-first/zero-config for a phase
  that needs neither yet.
- **Recursive SQL CTEs for traversal** — keeps traversal in the DB, but couples
  traversal logic to SQLite's dialect, complicates the in-memory adapter, and is harder
  to make deterministic/testable per-hop. Deferred until profiling demands it.
- **Reuse the `MemoryStore` table for edges** — collapses the Memory Core / Knowledge
  Graph boundary; forbidden by `02-system-architecture.md`.

## Tradeoffs
- **Gain:** consistent port pattern, offline-first, deterministic, ACID, fully testable
  traversal, and a clean seam to swap in a native graph store later.
- **Give up:** application-side BFS does N adjacency reads per hop; fine at Phase 2
  scale and well under the 150ms NFR, but a future ADR can add a CTE-based or native
  graph adapter behind the same `GraphStore` port when deep/wide traversals dominate.

## Consequences
- The `GraphStore` port and `KnowledgeGraph` public API become protected architecture
  (changes require approval + an ADR, `99` §3).
- `delete_entity` cascades to incident relationships so the graph never holds dangling
  edges; this is part of the port contract.
- Vector/semantic retrieval over the graph remains owned by Phase 3 (separate ADR).

## Follow-up Actions
- Add a native-graph or CTE-traversal adapter behind `GraphStore` when traversal depth
  or width demands it (new ADR).
- Relocate shared trust primitives to a dedicated trust package when the Trust Engine
  (Phase 4) lands (new ADR).
