# Semantic Control Plane (SCP)

**The cognitive control layer for AI systems.**

SCP is to AI cognition what Kubernetes is to cloud infrastructure: the neutral control plane
that manages Memory, Knowledge, Trust, Governance, and Observability so your agents don't
have to.

> SCP is **not** a chatbot, RAG framework, or agent framework.
> It is the infrastructure layer that sits *beneath* them.

---

## Why SCP?

Every agent builder today improvises the same fragile cognitive stack:

- Vector stores with no provenance — *who created this memory? How confident?*
- Prompt-stuffed context with no lifecycle — *old facts never expire; contradictions accumulate*
- No audit trail — *when an agent makes a wrong decision, there's no replay path*
- No governance — *compliance teams can't answer "what did the agent remember?"*

SCP externalises these concerns as production-grade infrastructure.

---

## Features

| Capability | Module |
|---|---|
| Durable memory with full lifecycle (consolidation, compression, archive) | `scp.memory` |
| Knowledge graph with trust-bearing entities and relationships | `scp.graph` |
| Hybrid semantic retrieval — vector + graph expansion, trust-aware ranking | `scp.query` |
| Explainable trust scoring, source registry, contradiction detection | `scp.trust` |
| Agent runtime with context assembly, tool registry, EPISODIC persistence | `scp.agent` |
| Decision replay, entity tracing, root-cause debugging | `scp.recorder` |
| Policy-based governance, immutable audit trail, compliance reporting | `scp.governance` |

---

## Quick Start

```bash
pip install semantic-control-plane
```

```python
import asyncio
from scp.memory import MemoryCore
from scp.graph import KnowledgeGraph
from scp.query import SemanticQueryEngine
from scp.trust import TrustEngine
from scp.agent import AgentRuntime, AgentConfig
from scp.governance import GovernanceLayer, Policy, PolicyCondition, PolicyAction, PolicyScope
from scp.recorder import FlightRecorder
from datetime import datetime, UTC

async def main():
    # Build the cognitive stack
    memory = MemoryCore()
    kg = KnowledgeGraph()
    trust = TrustEngine()
    query = SemanticQueryEngine(kg, memory, trust)
    runtime = AgentRuntime(query, memory, trust, kg)

    # Add governance
    gov = GovernanceLayer()
    await gov.add_policy(Policy(
        policy_id="p1",
        name="Block low-trust sources",
        description="Deny context items below 0.4 trust score",
        scope=PolicyScope.CONTEXT_ITEM,
        condition=PolicyCondition(min_trust_score=0.4),
        action=PolicyAction.DENY,
        created_at=datetime.now(UTC),
    ))

    # Add replay capability
    recorder = FlightRecorder()

    # Run an agent step
    config = AgentConfig(agent_id="agent-1", max_steps=10)
    agent_id = await runtime.create_agent(config)
    step = await runtime.run_step(agent_id, "What do we know about Project X?")

    # Record and govern (pull-based — explicit, not magic)
    await recorder.record(step)
    audit_event = await gov.govern_step(step)

    # Full compliance report
    report = await gov.compliance_report(agent_id="agent-1")
    print(f"Compliant: {report.compliant}")
    print(f"Violations: {len(report.violations)}")

asyncio.run(main())
```

---

## Architecture

### Hexagonal (ports & adapters) throughout

Swap any backend without touching domain code:

```python
# Dev/test: in-memory (default, zero infra)
memory = MemoryCore()

# Single-node durable
from scp.memory.backends.sqlite import SqliteStore
memory = MemoryCore(store=SqliteStore("memory.db"))

# Future: Postgres / ANN vector search (zero domain code change)
```

### Design principles

1. **Trust first** — every fact carries provenance and confidence *at write time*, not at query time
2. **Additive only** — 7 phases; each extends without modifying prior phases; zero regressions
3. **Ports & adapters** — every storage boundary is swappable via `@runtime_checkable Protocol`
4. **Pull-based cross-cutting** — Governance and Flight Recorder are explicit, never auto-wired
5. **Immutable records** — all domain models are `frozen=True`; audit trail is tamper-evident

---

## Examples

| Example | Description |
|---|---|
| `examples/basic_agent.py` | Minimal agent with memory + trust |
| `examples/governed_agent.py` | Agent with policy gates and audit trail |
| `examples/replay_session.py` | Post-hoc replay of an agent decision |
| `examples/compliance_report.py` | Generate a compliance report across all agents |

---

## Quality

- **221 tests** — unit + integration + regression; 0 failures
- **`mypy --strict`** — type-safe across all domain code
- **`ruff`** — lint + format; CI-enforced
- **8 ADRs** — every significant decision documented with alternatives and rationale
- **Phase Gate Protocol** — 7 gates, each requiring test passage before the next phase begins

---

## Roadmap

| Phase | Status | Capability |
|---|---|---|
| 1 Memory Core | Complete | Storage, lifecycle, consolidation, compression |
| 2 Knowledge Graph | Complete | Entities, relationships, graph traversal |
| 3 Semantic Query Engine | Complete | Hybrid retrieval, trust-aware ranking |
| 4 Trust Engine | Complete | Confidence scoring, verification, contradiction detection |
| 5 Agent Runtime | Complete | Context assembly, tool invocation, EPISODIC memory |
| 6 Flight Recorder | Complete | Replay, tracing, root-cause debugging |
| 7 Governance Layer | Complete | Policy gates, audit trail, compliance reporting |
| 8 Observability Engine | Planned | Metrics, traces, system health |
| 9 Developer Console | Planned | Web UI over all SCP capabilities |

---

## Contributing

See `CONTRIBUTING.md`. The most valuable contributions are storage adapters — if you have a
production deployment using pgvector, Qdrant, Postgres, or a cloud KV store, your adapter
benefits every SCP user.

---

