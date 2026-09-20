# 11 — Memory Model (Domain)

> Design spec for the **Memory Core** (Phase 1). Authoritative for memory architecture and lifecycle. Implementation follows this spec; deviations require updating this file.

## Purpose
Memory Core owns how SCP stores, retrieves, consolidates, compresses, and ages cognitive memory — with **trust metadata as a first-class, inseparable property of every memory** (never bolted on later).

## Memory Record (conceptual shape)
Every memory carries, at minimum:
- **content** — the stored information (text/structured payload).
- **id / type** — stable identifier and memory type.
- **source** — where it came from (agent, user, tool, system).
- **provenance** — chain of how it was derived/ingested.
- **confidence** — score reflecting certainty (see `14-trust-model.md`).
- **verification status** — unverified / verified / contradicted.
- **temporal context** — created-at, valid-from/valid-to, last-accessed.
- **lifecycle state** — active / consolidated / compressed / archived / expired.

## Lifecycle
```
Ingest → Active → Consolidate → Compress → Archive → Expire
```
- **Storage:** durable write with full trust metadata attached.
- **Retrieval:** by id, type, recency, and (later, via Semantic Query Engine) by similarity/graph.
- **Consolidation:** merge/relate related memories; resolve duplicates; preserve provenance.
- **Compression:** reduce footprint of aged memories while retaining recoverable essence and trust fields.
- **Lifecycle management:** age-out / archive / expire per policy (Governance Layer integrates here later).

## Boundaries
- Memory Core does **not** perform semantic ranking (that is the Semantic Query Engine, Phase 3) or graph relationship logic (Knowledge Graph, Phase 2). It exposes interfaces those modules build on.
- Trust *scoring* logic lives in the Trust Engine (Phase 4); Memory Core *stores and carries* the trust fields and accepts scores via interface.

## Phase 1 Scope (first vertical slice)
Storage + retrieval + lifecycle state, with trust metadata fields present and populated (even if some scores are placeholder-default until the Trust Engine exists). Consolidation/compression designed now, implemented within Phase 1 per the roadmap's capability list.

## Implemented Semantics (Phase 1)
- **Allowed transitions:** ACTIVE → {CONSOLIDATED, COMPRESSED, ARCHIVED, EXPIRED};
  CONSOLIDATED → {COMPRESSED, ARCHIVED, EXPIRED}; COMPRESSED → {ARCHIVED, EXPIRED};
  ARCHIVED → {EXPIRED}; EXPIRED is terminal. Illegal transitions raise.
- **Consolidation:** merging ≥2 memories produces one new `CONSOLIDATED` record;
  highest-confidence input is primary (its source/verification win), confidence is the
  max, distinct contents are merged, full provenance is preserved with a CONSOLIDATE
  entry listing parent ids. The original memories are moved to `ARCHIVED` with a
  "superseded by <id>" provenance entry.
- **Compression:** deterministic truncation to an essence (default 280 chars) with a
  marker, retaining all trust fields. Semantic (LLM) summarisation is deferred.
- Code: `scp/memory/lifecycle.py` (pure) + `scp/memory/core.py` (orchestration).
