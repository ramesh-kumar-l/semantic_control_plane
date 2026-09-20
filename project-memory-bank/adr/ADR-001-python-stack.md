# ADR-001 — Python as Implementation Stack

## Status
Accepted (2026-06-20)

## Context
SCP is greenfield — the repository had no code at the time of this decision. Before any implementation (starting with Phase 1 Memory Core), a primary implementation language/stack must be chosen so that architecture (`02-system-architecture.md`) and development rules (`99-development-rules.md`) can be made concrete.

## Problem
Which language and core stack should SCP be built on?

## Decision
**Python** as the primary implementation language.
- Python 3.12+, **async-first** for I/O-bound cognitive workloads.
- `pydantic` v2 for models and validation.
- `FastAPI`-style boundaries for service surfaces.
- Tooling: `ruff` (lint + format), `mypy --strict`, `pytest`.

## Alternatives
- **TypeScript/Node** — strong for a unified UI + backend language; less native AI/ML ecosystem fit.
- **Rust/Go** — best raw performance and edge/robotics fit; slower iteration, smaller AI ecosystem, higher build cost for early phases.

## Tradeoffs
- **Gain:** richest AI/ML ecosystem, fast iteration, strong typing via pydantic/mypy, broad hiring pool, natural fit for cognitive-infra components.
- **Give up:** raw runtime performance vs Rust/Go; will need care to hit the P95 < 150ms target and edge/deterministic goals (mitigated by async design and later optimization, and the option of native/edge components in future ADRs).

## Consequences
- `02-system-architecture.md` and `99-development-rules.md` now specify Python conventions.
- Storage backends (vector/graph/KV) remain **unselected** — to be decided in a future ADR during Phase 1+ design.
- Edge/robotics performance-critical paths may later warrant a separate component-level stack decision (new ADR), without changing the primary stack.

## Follow-up Actions
- On Phase 1 start (INIT-002): scaffold the Python project (`pyproject.toml`, package layout, ruff/mypy/pytest config).
- Author a storage-backend ADR before implementing Memory Core persistence.
