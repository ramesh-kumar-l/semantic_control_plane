# 99 — Development Rules (Governance)

> **Highest-priority file.** Load this first in every session. These rules override convenience.

## 1. Source of Truth
- The `project-memory-bank/` is the primary source of truth. **Never assume. Never invent context.**
- Before planning or implementing, load the minimum required memory files (see loading priority below).
- If reality and the memory bank disagree, fix the memory bank and call out the discrepancy.

### Loading Priority (read the minimum necessary)
1. `99-development-rules.md` (this file)
2. `03-current-state.md`
3. Relevant architecture file (`02-system-architecture.md`)
4. Relevant domain file (`11-memory-model.md`, `14-trust-model.md`, `18-ui-design-system.md`)
5. `30-session-handoff.md`

## 2. Development Philosophy
Always follow: **Understand → Design → Review → Implement → Validate → Document.**
Never jump straight to implementation. Never code before understanding context.

## 3. Architecture Protection
- Protect architecture aggressively. Preference order: **Extension > Modification > Rewrite.**
- Never (without explicit approval): rewrite large sections, replace implementations, change module boundaries, rename core modules, change public interfaces, or introduce breaking changes.
- Assume current code is correct unless proven otherwise. Prefer additive changes.

## 4. Phase Discipline
- Work strictly phase-by-phase (see `04-roadmap.md`). Never implement future-phase features.
- **Phase Gate Protocol** — at the end of every phase, STOP and produce:
  What Was Implemented · Design Review · Risks · Technical Debt · Test Results · Documentation Updates · Recommended Next Steps — then ask **"Approve Phase Completion?"** and wait.

## 5. Engineering Standards
Every implementation must satisfy: Correctness · Reliability · Maintainability · Observability · Testability · Security · Performance · Explainability. No shortcuts.

## 6. Testing Requirements
Every feature requires Unit + Integration + Regression tests and Performance validation. No implementation is complete without validation.

## 7. Reliability Requirements
Every subsystem must answer: What happened? Why? What evidence supports it? Can it be reproduced? Can it be audited? If not — redesign.

## 8. Trust Requirements
Trust is first-class. Every memory, fact, relationship, and decision supports: source tracking, provenance, confidence scores, verification status, temporal context. **Trust is never bolted on later.**

## 9. Security Requirements
Design for: encryption, authentication, authorization, auditability, least privilege, privacy by default. Security is mandatory, not optional.

## 10. Documentation & ADRs
- Every implementation updates: Architecture, API, Design, Operational docs, and Decision Records.
- Significant architectural decisions get an `adr/ADR-XXX-Title.md` (Context · Problem · Decision · Alternatives · Tradeoffs · Consequences · Follow-up).

## 11. Python Coding Conventions (chosen stack)
- **Language:** Python 3.12+. Async-first for I/O. `pydantic` v2 for models/validation. `FastAPI`-style service boundaries.
- **Style:** `ruff` (lint + format), `mypy --strict` for typed modules. PEP 8 naming: `snake_case` functions/vars, `PascalCase` classes, `UPPER_SNAKE` constants.
- **Structure:** one module = one responsibility; respect SCP module boundaries (`02-system-architecture.md`). No cross-layer imports that collapse boundaries.
- **Errors:** explicit, typed exceptions; no silent failures. No error handling for impossible scenarios.
- **Tests:** `pytest`. Test files mirror source paths.

## 12. Token Efficiency
Prefer targeted changes, diffs, design reviews, incremental updates. Avoid large rewrites, full-file regeneration, repository-wide scans, and unnecessary explanation. Read only the code needed for the task.

## 13. Simplicity
Minimum code that solves the problem. No speculative features, single-use abstractions, or unrequested configurability. If 200 lines could be 50, rewrite it.
