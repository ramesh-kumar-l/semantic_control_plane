"""Unit tests for GovernanceLayer service."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

from scp.governance import GovernanceLayer, PolicyAction, PolicyScope
from scp.governance.errors import PolicyNotFoundError
from scp.governance.models import Policy, PolicyCondition
from scp.memory.enums import VerificationStatus

from .conftest import make_agent_step, make_context_item, make_deny_policy, make_warn_policy


@pytest.fixture
def gov() -> GovernanceLayer:
    return GovernanceLayer()


async def test_add_and_list_policies(gov: GovernanceLayer) -> None:
    policy = make_deny_policy()
    await gov.add_policy(policy)
    policies = await gov.list_policies()
    assert any(p.policy_id == policy.policy_id for p in policies)


async def test_get_policy(gov: GovernanceLayer) -> None:
    policy = make_deny_policy()
    await gov.add_policy(policy)
    fetched = await gov.get_policy(policy.policy_id)
    assert fetched.policy_id == policy.policy_id


async def test_get_unknown_policy_raises(gov: GovernanceLayer) -> None:
    with pytest.raises(PolicyNotFoundError):
        await gov.get_policy("nonexistent")


async def test_disable_policy(gov: GovernanceLayer) -> None:
    policy = make_deny_policy()
    await gov.add_policy(policy)
    await gov.disable_policy(policy.policy_id)
    active = await gov.list_policies()
    assert all(p.policy_id != policy.policy_id for p in active)


async def test_govern_context_item_clean(gov: GovernanceLayer) -> None:
    """No policies → outcome ALLOW."""
    item = make_context_item(trust=0.9)
    event = await gov.govern_context_item(item, agent_id="a1", step_id="s1")
    assert event.outcome == PolicyAction.ALLOW
    assert event.entity_id == item.entity_id


async def test_govern_context_item_denied(gov: GovernanceLayer) -> None:
    await gov.add_policy(make_deny_policy(min_trust=0.7))
    item = make_context_item(trust=0.3)
    event = await gov.govern_context_item(item, agent_id="a1", step_id="s1")
    assert event.outcome == PolicyAction.DENY


async def test_govern_context_item_warn_on_contradicted(gov: GovernanceLayer) -> None:
    await gov.add_policy(make_warn_policy())
    item = make_context_item(trust=0.9)
    event = await gov.govern_context_item(
        item,
        agent_id="a1",
        step_id="s1",
        verification_status=VerificationStatus.CONTRADICTED,
    )
    assert event.outcome == PolicyAction.WARN


async def test_govern_step(gov: GovernanceLayer) -> None:
    step_policy = Policy(
        policy_id=uuid.uuid4().hex,
        name="avg-trust-gate",
        description="deny low average trust steps",
        scope=PolicyScope.AGENT_STEP,
        condition=PolicyCondition(min_average_trust=0.9),
        action=PolicyAction.DENY,
        created_at=datetime.now(UTC),
    )
    await gov.add_policy(step_policy)
    step = make_agent_step(items=[make_context_item(trust=0.2), make_context_item(trust=0.3)])
    event = await gov.govern_step(step)
    assert event.outcome == PolicyAction.DENY
    assert event.step_id == step.step_id


async def test_audit_trail_grows(gov: GovernanceLayer) -> None:
    await gov.add_policy(make_deny_policy())
    for i in range(3):
        item = make_context_item(entity_id=f"e{i}", trust=0.1)
        await gov.govern_context_item(item, agent_id="a1", step_id=f"s{i}")
    trail = await gov.get_audit_trail(agent_id="a1")
    assert len(trail) == 3


async def test_compliance_report(gov: GovernanceLayer) -> None:
    await gov.add_policy(make_deny_policy(min_trust=0.8))
    # one passing, one failing
    good = make_context_item(entity_id="good", trust=0.9)
    bad = make_context_item(entity_id="bad", trust=0.1)
    await gov.govern_context_item(good, agent_id="a1", step_id="s1")
    await gov.govern_context_item(bad, agent_id="a1", step_id="s2")
    report = await gov.compliance_report(agent_id="a1")
    assert report.compliant is False
    assert len(report.violations) == 1
    assert report.total_events == 2


async def test_get_audit_event_by_id(gov: GovernanceLayer) -> None:
    item = make_context_item(trust=0.9)
    event = await gov.govern_context_item(item, agent_id="a1", step_id="s1")
    fetched = await gov.get_audit_event(event.event_id)
    assert fetched.event_id == event.event_id
