# 14 — Trust Model (Domain)

> Authoritative for trust scoring and verification. **Trust is first-class and never bolted on later.** Trust fields travel with every memory, fact, and relationship.

## Why Trust Is a First-Class Concern
SCP's defensibility rests on trustworthy cognition. Every stored item must be able to answer: *Where did this come from? How sure are we? Has it been verified? Does it conflict with anything?*

## Trust Primitives (carried on every item)
- **Source tracking** — the origin (agent, user, tool, external system, inference).
- **Provenance** — the derivation chain from origin to current form; survives consolidation/compression.
- **Confidence score** — normalized [0.0–1.0] certainty estimate.
- **Verification status** — `unverified` | `verified` | `contradicted` | `disputed`.
- **Temporal context** — when asserted and over what validity window (trust can decay with age).

## Trust Engine Responsibilities (Phase 4)
- **Trust Scores** — compute/maintain item-level trust from source reliability, confidence, verification, recency.
- **Confidence Models** — how raw signals map to confidence (documented and explainable).
- **Source Tracking** — registry of sources and their reliability weighting.
- **Verification** — workflows/signals that move items between verification states.
- **Contradiction Detection** — identify conflicting assertions; mark `contradicted`/`disputed`; surface for resolution.

## Cross-Module Contract
- **Memory Core (Phase 1):** stores and carries trust fields; accepts default/placeholder confidence before the Trust Engine exists.
- **Knowledge Graph (Phase 2):** entities/relationships carry the same trust primitives.
- **Semantic Query Engine (Phase 3):** ranking may incorporate trust/confidence.
- **Governance Layer (Phase 7):** policies may gate actions on verification status / trust thresholds.

## Explainability Requirement
Every trust score must be **explainable** — reconstructable from its inputs and reproducible via the Agent Flight Recorder. No opaque trust.
