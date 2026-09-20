"""Unit tests for PolicyEngine."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

from scp.governance.backends.in_memory import InMemoryPolicyStore
from scp.governance.engine import PolicyEngine, compute_outcome
from scp.governance.enums import PolicyAction, PolicyScope
from scp.governance.models import Policy, PolicyCondition
from scp.memory.enums import VerificationStatus

from .conftest import make_agent_step, make_context_item, make_deny_policy, make_warn_policy


@pytest.fixture
def store() -> InMemoryPolicyStore:
    return InMemoryPolicyStore()


@pytest.fixture
def engine(store: InMemoryPolicyStore) -> PolicyEngine:
    return PolicyEngine(store)


async def test_no_policies_returns_empty(engine: PolicyEngine) -> None:
    item = make_context_item(trust=0.1)
    evals = await engine.evaluate_context_item(item)
    assert evals == []


async def test_trust_threshold_policy_triggered(
    engine: PolicyEngine, store: InMemoryPolicyStore
) -> None:
    await store.add(make_deny_policy(min_trust=0.6))
    item = make_context_item(trust=0.3)
    evals = await engine.evaluate_context_item(item)
    assert len(evals) == 1
    assert evals[0].triggered is True
    assert evals[0].action == PolicyAction.DENY


async def test_trust_threshold_policy_not_triggered(
    engine: PolicyEngine, store: InMemoryPolicyStore
) -> None:
    await store.add(make_deny_policy(min_trust=0.6))
    item = make_context_item(trust=0.9)
    evals = await engine.evaluate_context_item(item)
    assert len(evals) == 1
    assert evals[0].triggered is False


async def test_verification_policy_triggered(
    engine: PolicyEngine, store: InMemoryPolicyStore
) -> None:
    await store.add(make_warn_policy(forbidden=VerificationStatus.CONTRADICTED))
    item = make_context_item(trust=0.9)
    evals = await engine.evaluate_context_item(
        item, verification_status=VerificationStatus.CONTRADICTED
    )
    assert len(evals) == 1
    assert evals[0].triggered is True
    assert evals[0].action == PolicyAction.WARN


async def test_verification_policy_not_triggered_when_ok(
    engine: PolicyEngine, store: InMemoryPolicyStore
) -> None:
    await store.add(make_warn_policy(forbidden=VerificationStatus.CONTRADICTED))
    item = make_context_item(trust=0.9)
    evals = await engine.evaluate_context_item(
        item, verification_status=VerificationStatus.VERIFIED
    )
    assert evals[0].triggered is False


async def test_disabled_policy_skipped(engine: PolicyEngine, store: InMemoryPolicyStore) -> None:
    policy = make_deny_policy(min_trust=0.9)
    await store.add(policy)
    await store.disable(policy.policy_id)
    item = make_context_item(trust=0.1)  # would trigger if enabled
    evals = await engine.evaluate_context_item(item)
    assert evals == []


async def test_scope_filtering(engine: PolicyEngine, store: InMemoryPolicyStore) -> None:
    step_policy = Policy(
        policy_id=uuid.uuid4().hex,
        name="step-policy",
        description="step scope",
        scope=PolicyScope.AGENT_STEP,
        condition=PolicyCondition(min_average_trust=0.9),
        action=PolicyAction.DENY,
        created_at=datetime.now(UTC),
    )
    await store.add(step_policy)
    # AGENT_STEP scope policy must not appear in context-item evaluations
    item = make_context_item(trust=0.1)
    evals = await engine.evaluate_context_item(item)
    assert all(e.policy_id != step_policy.policy_id for e in evals)


async def test_multiple_policies(engine: PolicyEngine, store: InMemoryPolicyStore) -> None:
    await store.add(make_deny_policy(min_trust=0.6))
    await store.add(make_warn_policy())
    item = make_context_item(trust=0.3)
    evals = await engine.evaluate_context_item(
        item, verification_status=VerificationStatus.CONTRADICTED
    )
    assert len(evals) == 2


async def test_evaluation_metadata(engine: PolicyEngine, store: InMemoryPolicyStore) -> None:
    policy = make_deny_policy(min_trust=0.6)
    await store.add(policy)
    item = make_context_item(entity_id="eid-99", trust=0.2)
    evals = await engine.evaluate_context_item(item)
    e = evals[0]
    assert e.policy_id == policy.policy_id
    assert e.policy_name == policy.name
    assert e.target_id == "eid-99"
    assert e.trust_score == pytest.approx(0.2)
    assert e.reason != ""


async def test_step_evaluation_triggered(engine: PolicyEngine, store: InMemoryPolicyStore) -> None:
    step_policy = Policy(
        policy_id=uuid.uuid4().hex,
        name="avg-trust",
        description="average trust gate",
        scope=PolicyScope.AGENT_STEP,
        condition=PolicyCondition(min_average_trust=0.8),
        action=PolicyAction.WARN,
        created_at=datetime.now(UTC),
    )
    await store.add(step_policy)
    step = make_agent_step(items=[make_context_item(trust=0.3), make_context_item(trust=0.4)])
    evals = await engine.evaluate_step(step)
    assert len(evals) == 1
    assert evals[0].triggered is True


async def test_compute_outcome_deny_wins() -> None:
    from .conftest import make_deny_policy, make_warn_policy

    deny_p = make_deny_policy()
    warn_p = make_warn_policy()

    from scp.governance.engine import _make_evaluation

    e_deny = _make_evaluation(deny_p, triggered=True, target_id="x", trust_score=0.1, reason="low")
    e_warn = _make_evaluation(
        warn_p, triggered=True, target_id="x", trust_score=0.1, reason="contradicted"
    )
    assert compute_outcome([e_deny, e_warn]) == PolicyAction.DENY


async def test_compute_outcome_allow_when_none_triggered() -> None:
    deny_p = make_deny_policy()
    from scp.governance.engine import _make_evaluation

    e = _make_evaluation(deny_p, triggered=False, target_id="x", trust_score=0.9, reason="ok")
    assert compute_outcome([e]) == PolicyAction.ALLOW
