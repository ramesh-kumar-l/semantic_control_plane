# ADR-008 — Governance Layer Architecture

**Date:** 2026-06-20  
**Status:** Accepted  
**Phase:** 7

## Context

Phase 6 gave us a full audit trail of agent decisions via `FlightRecorder`. That proves
*what happened*, but it does not *control* what is allowed to happen. We need:
- Policy gates enforced before/after agent steps (trust thresholds, verification status)
- A persistent audit trail that records every governance evaluation
- A compliance view that answers "is this agent operating within policy?"

## Problem

How do we layer governance enforcement over Phases 1–6 without modifying any existing code
and without coupling policies to agent internals?

## Decision

Implement `scp/governance/` as a standalone Phase 7 module with a two-component design:

| Component | Responsibility |
|---|---|
| `PolicyEngine` | Evaluates active policies against ContextItems and AgentSteps |
| `AuditLogger` | Persists every governance evaluation as an immutable AuditEvent |

`GovernanceLayer` composes both behind a single service entry point.

**Decoupling:** `govern_context_item(item, ...)` and `govern_step(step)` accept public
models from Phase 5 (`ContextItem`, `AgentStep`) — governance never reaches into the
runtime or assembler. Verification status is passed explicitly by the caller.

**`PolicyStore` + `AuditStore` ports:** same hexagonal pattern as Phases 1–6. Both ship
with `InMemoryPolicyStore` and `InMemoryAuditStore` for dev/test; durable adapters deferred.

**Pull-based (same as Phase 6):** the application layer calls governance explicitly; the
engine is never auto-wired into AgentRuntime. This preserves Phase 5 boundary integrity.

## Policy Semantics

A `Policy` has a `scope` (CONTEXT_ITEM or AGENT_STEP) and a `PolicyCondition`:
- `min_trust_score` — fires if `ContextItem.trust_score < threshold`
- `forbidden_verification_status` — fires if the item's status matches the forbidden value
- `min_average_trust` — fires if average trust across a step's items falls below threshold

Multiple sub-conditions use **AND logic**: all present fields must fire for the policy
to trigger. For OR logic, create separate policies.

`PolicyAction` severity: ALLOW < WARN < REQUIRE_REVIEW < DENY.
`AuditEvent.outcome` is the most severe triggered action across all evaluated policies.

## Alternatives Rejected

| Alternative | Why rejected |
|---|---|
| Modify `ContextAssembler` to check policies inline | Violates Phase 5 boundary; couples trust engine to governance |
| Single monolithic `GovernanceService` | Exceeds 300-line limit; mixes evaluation logic with persistence |
| Policy conditions as code/lambda | Unpicklable, untestable, security risk |

## Models

- `Policy` + `PolicyCondition` — frozen pydantic; what to check and what to do.
- `PolicyEvaluation` — immutable result of one policy against one subject.
- `AuditEvent` — immutable record: who/what/when/outcome, full evaluations list.
- `ComplianceReport` — summary: violations (DENY), warnings (WARN), review_required.

## Tradeoffs

| + | - |
|---|---|
| Governance fully independent of runtime | Caller must explicitly call govern_*() |
| Verification status is explicit parameter — no coupling to KG | Caller must supply it from their context |
| Two-component split keeps each file < 100 lines | More files vs monolith |
| `PolicyStore` port allows durable adapter | In-memory store loses state on restart |

## Consequences

- `GovernanceLayer`, `PolicyEngine`, `AuditLogger`, `PolicyStore`, `AuditStore`,
  and all governance models join the protected API surface (`99` §3).
- Phases 1–6 code is **unchanged** — additive only.
- Durable `SqliteGovernanceStore` adapter is a future ADR.

## Follow-up

- Durable `SqliteAuditStore` + `SqlitePolicyStore` backends (ADR-009 candidate).
- Integration of `GovernanceLayer` with `AgentRuntime` via optional hook parameter.
- Role-based access control on policy management API.
- Pre-built compliance policy bundles (e.g., "GDPR baseline", "high-trust-only").
