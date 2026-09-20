# ADR-004 — Semantic Query Engine: Embeddings, Vector Index & Hybrid Retrieval

## Status
Accepted (2026-06-20)

## Context
Phase 3 (Semantic Query Engine) introduces **hybrid retrieval**: vector (semantic)
search + graph search, with ranking and query planning (`04-roadmap.md`,
`02-system-architecture.md`). It builds on Phase 2 traversal and must keep the same
NFRs: offline-first, deterministic, P95 < 150ms, and trust travelling *with* facts —
here meaning ranking **may** incorporate trust (`14-trust-model.md` cross-module
contract). Module boundaries hold: the engine owns retrieval/ranking/planning and uses
only the `KnowledgeGraph` public API + a vector-index port; it never reaches into
another module's storage.

## Problem
How should text be embedded, vectors indexed, and signals fused for Phase 3 without
(a) breaking offline-first/determinism by calling an external embedding model, or
(b) prematurely adopting a heavyweight ANN library / vector database before scale
demands it — while staying consistent with the port/adapter pattern (ADR-002/003)?

## Decision
1. Define an **`Embedder` port** with a default **`HashingEmbedder`**: feature-hashing
   bag-of-words into a fixed-dimension, L2-normalized vector using a **stable** hash
   (`blake2b`, not Python's salted `hash()`). Deterministic across processes, fully
   offline, zero dependencies. A learned/model-based embedder can replace it behind the
   port without touching the engine.
2. Define a **`VectorStore` port** with an **`InMemoryVectorStore`** adapter doing
   brute-force cosine top-k (ties broken by ascending id for determinism). The index is
   a **derived** structure — Memory Core / the Knowledge Graph remain the source of
   truth — so it is rebuilt via `reindex()` rather than being a system of record.
3. **Hybrid retrieval** = vector *seeds* + graph *expansion*. The query embeds to a
   vector; top-k lexical seed entities come from the index; Phase 2 `traverse` (BFS,
   direction BOTH) expands to neighbours whose **graph proximity** is the seed score
   decayed per hop (`seed_score * decay**hops`). This surfaces relevant entities that
   are graph-adjacent but lexically dissimilar — exactly what vector-only misses.
4. **Trust-aware, explainable ranking.** Final score is a weighted sum of three
   normalized signals — `semantic` (cosine), `graph` (proximity), `trust` (confidence
   scaled by a documented verification factor). Every `ScoredResult` carries the raw
   component values so the score is reconstructable (`14-trust-model.md` explainability,
   `99` §7).
5. **Rule-based query planner** chooses `VECTOR_ONLY | GRAPH_ONLY | HYBRID` and sizes the
   seed set; the strategy masks ranking weights (e.g. GRAPH_ONLY zeroes the semantic
   weight). VECTOR_ONLY is the explicit **baseline** the hybrid path is measured against.

## Alternatives
- **External embedding API/model (OpenAI, sentence-transformers) now** — higher semantic
  quality, but breaks offline-first/determinism and adds a heavy dependency for a phase
  that only needs to demonstrate hybrid retrieval. Deferrable behind the `Embedder` port.
- **ANN library / vector DB (FAISS, pgvector, Qdrant) now** — needed at large scale, but
  premature; brute-force cosine is exact, dependency-free, and well under 150ms at Phase
  3 scale. Deferrable behind the `VectorStore` port.
- **Recursive-SQL graph join for expansion** — couples retrieval to SQL dialect and
  duplicates Phase 2's deterministic, tested BFS. Rejected; reuse `KnowledgeGraph`.
- **Cost-based query planner now** — over-engineered before we have index statistics or
  a workload to optimize. Rule-based planning suffices; cost-based is a follow-up.

## Tradeoffs
- **Gain:** offline, deterministic, exact, dependency-free retrieval; explainable
  trust-aware ranking; clean seams to swap in a learned embedder or ANN index later.
- **Give up:** lexical (not learned) semantics, so similarity is bag-of-words quality;
  brute-force search is O(N) per query. Both are bounded by the ports and replaceable
  via follow-up ADRs when quality or scale demands it.

## Consequences
- The `Embedder` + `VectorStore` ports and the `SemanticQueryEngine` public API become
  protected architecture (changes require approval + an ADR, `99` §3).
- The vector index is rebuildable and need not be durable in Phase 3; persistence is a
  future ADR when index rebuild cost matters.
- Real trust *scores* remain Phase 4; ranking consumes the placeholder confidence + the
  verification factor defined here until then.

## Follow-up Actions
- Add a learned/model-based `Embedder` adapter when retrieval quality demands it (new ADR).
- Add an ANN / pgvector `VectorStore` adapter when single-node brute force is too slow
  or the index must be durable (new ADR).
- Revisit ranking weights / add cost-based planning once a real query workload exists.
