# ADR-005 — Trust Engine: Explainable Scoring, Confidence Model & Verification

## Status
Accepted (2026-06-21)

## Context
Phase 4 (Trust Engine) turns the first-class trust *primitives* already carried on
every memory, entity, and relationship (source, confidence, verification status,
temporal context — ADR-002/003) into real, computed **trust scores** with confidence
models, source tracking, verification workflows, and contradiction detection
(`14-trust-model.md`, `04-roadmap.md`). It must replace the flat `0.5` confidence
placeholder used by Phase 1/2 and the inline `confidence * verification_factor` stopgap
used by Phase 3 ranking. The standing NFRs apply: offline-first, deterministic,
P95 < 150ms, and — critically here — **explainability**: no opaque trust; every score
must be reconstructable from its inputs (`99` §7).

## Problem
How do we compute trust that is (a) explainable and reproducible, (b) boundary-respecting
(the Trust Engine must not reach into Memory/Graph storage, and Phase 1/2 must not depend
on Phase 4), and (c) able to genuinely replace the `0.5` placeholder in the live path —
without a learned/opaque model or premature persistence?

## Decision
1. **New `scp/trust/` module — pure, synchronous, deterministic.** It performs no I/O and
   never accesses another module's storage; it reads the trust primitives items already
   carry. Purity directly serves the offline + reproducibility NFRs.
2. **Source registry** (`SourceRegistry`) — documented default reliability per `SourceType`
   with per-identifier overrides (a vetted external API outranks an unknown one). Authoritative
   for *source reliability* (distinct from an assertion's own confidence).
3. **Confidence model** (`ConfidenceModel`) — maps ingest signals (source kind, verification
   state) to a real initial confidence via a documented per-`SourceType` base. This is what
   **replaces the flat 0.5**.
4. **Explainable scoring** (`scoring.py`) — `base = (w_r·reliability + w_c·confidence +
   w_t·recency) / Σw`, then `score = base · verification_factor`. The weighted blend is
   transparent; verification acts as a multiplicative **gate** so a contradicted item is
   strongly demoted regardless of source. `recency` is exponential half-life decay. Every
   `TrustAssessment` retains its components, weights, and a human-readable explanation —
   reproducible to the digit. This generalizes the Phase 3 stopgap into a principled model.
5. **Verification policy** (`VerificationPolicy`) — a signal-driven state machine mapping
   `TrustSignal`s to target `VerificationStatus`. One deliberate guard: CONTRADICTED → VERIFIED
   is forbidden; a contradiction must be REOPENED (→ DISPUTED) first, keeping an auditable trail.
6. **Contradiction detection** (`ContradictionDetector`) — deterministic detection of value
   mismatches and polarity conflicts over (subject, predicate) claim groups; `reconcile()`
   recommends verification statuses (lower-reliability side → CONTRADICTED, otherwise DISPUTED).
7. **Replacement via additive injection (Extension > Modification, `99` §3).** `MemoryCore`
   and `KnowledgeGraph` gain an optional `confidence_model: Callable[[Source, VerificationStatus],
   float] | None = None`. When wired to `TrustEngine.initial_confidence`, the live path stores
   real source-aware confidence; with the default `None`, existing behavior (the `0.5` fallback)
   is unchanged. Phase 1/2 depend only on a callable abstraction — **no import of Phase 4** —
   so layering is preserved (dependency inversion; wiring happens at the composition root).
   Phase 3 ranking is left untouched: once stored confidence is real, its unchanged ranking
   automatically improves.

## Alternatives
- **Learned / probabilistic trust model now** — higher fidelity but opaque, non-reproducible,
  and dependency-heavy; violates the explainability NFR. Deferrable.
- **Multiplicative aggregation of all signals** — defensible but harder to read and explain than
  a weighted blend; we keep the blend explainable and use verification as the one explicit gate.
- **Hard-wire `TrustEngine` into `MemoryCore`/`KnowledgeGraph`** — would make Phase 1/2 depend on
  Phase 4 and collapse layering. Rejected in favor of callable injection.
- **Persist trust scores** — scores are cheap, pure functions of stored primitives; recomputing
  on demand keeps a single source of truth. Persistence/caching is a future ADR if it becomes hot.
- **Mutate Memory/Graph from the Trust Engine** (e.g. auto-apply reconciliation) — breaks
  boundaries. The engine *recommends*; callers apply via the owning module's API.

## Tradeoffs
- **Gain:** explainable, reproducible, deterministic, offline trust; real varied confidence
  replacing 0.5; clean boundaries; Phase 3 improves with zero changes.
- **Give up:** hand-tuned (not learned) weights and heuristic contradiction detection (exact
  string/polarity over (subject, predicate)). Both are documented and replaceable behind the
  module's API when richer signals or semantic contradiction detection are needed.

## Consequences
- The `TrustEngine` public API + the `confidence_model` injection points on `MemoryCore` /
  `KnowledgeGraph` become protected architecture (changes require approval + an ADR, `99` §3).
- The `0.5` constant remains only as a backward-compatible fallback when no model is wired.
- Trust scores are computed on demand; no new storage or schema.

## Follow-up Actions
- Consider routing Phase 3 ranking's trust signal through `TrustEngine.assess` (so ranking also
  factors recency/source reliability), once Phase 4 is gate-approved (new ADR / extension).
- Add a learned confidence/trust model or semantic contradiction detection when signals demand it.
- Add trust-score caching only if profiling shows recomputation is hot.
