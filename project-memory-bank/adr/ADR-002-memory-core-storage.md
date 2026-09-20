# ADR-002 — Memory Core Storage Backend

## Status
Accepted (2026-06-20)

## Context
Phase 1 (Memory Core) needs durable storage for memory records with full trust
metadata (`11-memory-model.md`, `14-trust-model.md`). The system architecture
(`02-system-architecture.md`) mandates offline-first, deterministic behaviour and
horizontal scalability, while keeping module boundaries intact: Memory Core stores
and retrieves by id / type / recency / lifecycle state — it does **not** perform
semantic ranking (Phase 3) or graph traversal (Phase 2). ADR-001 left storage
backends unselected.

## Problem
Which storage backend should Phase 1 Memory Core persist to, without prematurely
committing the whole platform to a vector/graph database before those phases exist?

## Decision
1. Define a **`MemoryStore` port** (abstract interface) that Memory Core depends on.
   Memory Core never talks to a concrete database directly.
2. Ship two adapters in Phase 1:
   - **`InMemoryStore`** — for tests and ephemeral/dev use (deterministic, no I/O).
   - **`SqliteStore`** (via `aiosqlite`) — the durable, default backend.
3. **SQLite** is the Phase 1 durable backend: embedded, offline-first, ACID,
   deterministic, zero-ops, and production-stable for single-node deployments.

Records are stored with indexed columns (`id`, `type`, `lifecycle_state`,
`created_at`, `last_accessed`) for queryability plus a JSON `data` column for full
fidelity round-tripping of the pydantic model.

## Alternatives
- **PostgreSQL now** — better multi-node scaling, but adds an ops dependency and
  network non-determinism the Phase 1 vertical slice does not need yet.
- **A vector DB (e.g. Qdrant/pgvector) now** — premature: belongs to the Semantic
  Query Engine (Phase 3); would blur module boundaries.
- **Flat files / JSON on disk** — no ACID guarantees, weak concurrent-access story.

## Tradeoffs
- **Gain:** zero-config, offline-first, deterministic, fast to build/test, ACID,
  and — because Memory Core depends on the port, not SQLite — fully swappable later.
- **Give up:** single-node write scaling. Acceptable for Phase 1; a future ADR can
  add a Postgres adapter behind the same port when horizontal scale is needed.

## Consequences
- Phase 1 has a clean seam (`MemoryStore`) for adding Postgres / vector / graph
  adapters in later phases without changing Memory Core's public API.
- The port becomes part of the protected architecture — changing it requires
  approval + an ADR (`99-development-rules.md` §3).

## Follow-up Actions
- Add a Postgres adapter behind `MemoryStore` when multi-node scale is required (new ADR).
- Vector/graph storage decisions remain owned by Phases 2–3 (separate ADRs).
