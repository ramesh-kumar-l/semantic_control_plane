"""Integration tests: GovernanceLayer with real SCP stack (Phases 1–5)."""

from __future__ import annotations

import uuid

from scp.agent.runtime import AgentRuntime
from scp.governance import GovernanceLayer, PolicyAction
from scp.graph.enums import EntityType
from scp.memory.enums import SourceType, VerificationStatus

from .conftest import make_context_item, make_deny_policy, make_warn_policy


async def test_govern_real_agent_step(
    runtime: AgentRuntime,
    kg,
    query_engine,
) -> None:
    """Record a real AgentStep then govern it — governance independent of runtime."""
    entity = await kg.add_entity(
        "quantum computing",
        entity_type=EntityType.CONCEPT,
        source_type=SourceType.USER,
    )
    await query_engine.index_entity(entity)

    config_id = uuid.uuid4().hex
    from scp.agent.models import AgentConfig

    config = AgentConfig(agent_id=config_id, name="test-agent")
    state = runtime.create_agent(config)
    step = await runtime.run_step(state.agent_id, query="what is quantum computing?")

    gov = GovernanceLayer()
    event = await gov.govern_step(step)
    assert event.step_id == step.step_id
    assert event.agent_id == step.agent_id
    assert event.outcome in PolicyAction.__members__.values()


async def test_trust_threshold_blocks_low_trust_item() -> None:
    """DENY policy fires on a low-trust context item."""
    gov = GovernanceLayer()
    await gov.add_policy(make_deny_policy(min_trust=0.6))

    low_trust_item = make_context_item(entity_id="low-e", trust=0.2)
    event = await gov.govern_context_item(low_trust_item, agent_id="a1", step_id="s1")
    assert event.outcome == PolicyAction.DENY

    high_trust_item = make_context_item(entity_id="high-e", trust=0.9)
    event2 = await gov.govern_context_item(high_trust_item, agent_id="a1", step_id="s2")
    assert event2.outcome == PolicyAction.ALLOW


async def test_verification_status_gate() -> None:
    """WARN policy fires when verification status is CONTRADICTED."""
    gov = GovernanceLayer()
    await gov.add_policy(make_warn_policy(forbidden=VerificationStatus.CONTRADICTED))

    item = make_context_item(trust=0.9)
    event = await gov.govern_context_item(
        item,
        agent_id="a1",
        step_id="s1",
        verification_status=VerificationStatus.CONTRADICTED,
    )
    assert event.outcome == PolicyAction.WARN

    event2 = await gov.govern_context_item(
        item,
        agent_id="a1",
        step_id="s2",
        verification_status=VerificationStatus.VERIFIED,
    )
    assert event2.outcome == PolicyAction.ALLOW


async def test_audit_trail_complete(runtime: AgentRuntime, kg, query_engine) -> None:
    """Audit trail accumulates one event per governed subject."""
    entity = await kg.add_entity(
        "neural networks",
        entity_type=EntityType.CONCEPT,
        source_type=SourceType.USER,
    )
    await query_engine.index_entity(entity)

    from scp.agent.models import AgentConfig

    config = AgentConfig(agent_id=uuid.uuid4().hex, name="trail-agent")
    runtime.create_agent(config)

    gov = GovernanceLayer()
    await gov.add_policy(make_deny_policy(min_trust=0.0))  # always triggers

    for i in range(3):
        item = make_context_item(entity_id=f"e{i}", trust=0.1)
        await gov.govern_context_item(item, agent_id=config.agent_id, step_id=f"s{i}")

    trail = await gov.get_audit_trail(agent_id=config.agent_id)
    assert len(trail) == 3
    assert all(e.agent_id == config.agent_id for e in trail)


async def test_compliance_report_identifies_violations() -> None:
    """ComplianceReport marks agent as non-compliant when DENY events exist."""
    gov = GovernanceLayer()
    await gov.add_policy(make_deny_policy(min_trust=0.7))

    agent_id = "compliance-agent"
    good = make_context_item(entity_id="g1", trust=0.9)
    bad = make_context_item(entity_id="b1", trust=0.2)

    await gov.govern_context_item(good, agent_id=agent_id, step_id="s1")
    await gov.govern_context_item(bad, agent_id=agent_id, step_id="s2")

    report = await gov.compliance_report(agent_id=agent_id)
    assert report.compliant is False
    assert len(report.violations) == 1
    assert report.violations[0].agent_id == agent_id


async def test_governance_independent_of_runtime() -> None:
    """GovernanceLayer works without an AgentRuntime — decoupled."""
    gov = GovernanceLayer()
    await gov.add_policy(make_warn_policy())

    for i in range(5):
        item = make_context_item(entity_id=f"e{i}", trust=0.8)
        await gov.govern_context_item(
            item,
            agent_id="standalone-agent",
            step_id=f"step-{i}",
            verification_status=VerificationStatus.VERIFIED,
        )

    trail = await gov.get_audit_trail(agent_id="standalone-agent")
    assert len(trail) == 5
    report = await gov.compliance_report(agent_id="standalone-agent")
    assert report.compliant is True  # WARN policy, not DENY
