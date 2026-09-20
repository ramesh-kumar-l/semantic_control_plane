"""Unit tests for AuditLogger."""

from __future__ import annotations

from scp.governance.audit import AuditLogger
from scp.governance.backends.in_memory import InMemoryAuditStore
from scp.governance.engine import PolicyEngine
from scp.governance.enums import AuditEventType, PolicyAction
from scp.memory.enums import VerificationStatus

from .conftest import (
    InMemoryPolicyStore,
    make_context_item,
    make_deny_policy,
    make_warn_policy,
)


async def _build_logger_with_policies(
    *policies,
) -> tuple[AuditLogger, PolicyEngine, InMemoryAuditStore]:
    ps = InMemoryPolicyStore()
    for p in policies:
        await ps.add(p)
    as_ = InMemoryAuditStore()
    return AuditLogger(as_), PolicyEngine(ps), as_


async def test_log_stores_event() -> None:
    logger, engine, store = await _build_logger_with_policies(make_deny_policy())
    item = make_context_item(trust=0.1)
    evals = await engine.evaluate_context_item(item)
    event = await logger.log(
        event_type=AuditEventType.CONTEXT_ITEM_GOVERNED,
        agent_id="agent-1",
        step_id="step-1",
        entity_id=item.entity_id,
        evaluations=evals,
    )
    assert event.event_id != ""
    assert event.agent_id == "agent-1"
    assert event.outcome == PolicyAction.DENY


async def test_retrieve_event_by_id() -> None:
    logger, engine, _ = await _build_logger_with_policies(make_deny_policy())
    item = make_context_item(trust=0.1)
    evals = await engine.evaluate_context_item(item)
    event = await logger.log(
        event_type=AuditEventType.CONTEXT_ITEM_GOVERNED,
        agent_id="a1",
        step_id="s1",
        entity_id=item.entity_id,
        evaluations=evals,
    )
    fetched = await logger.get_event(event.event_id)
    assert fetched.event_id == event.event_id


async def test_query_by_agent_id() -> None:
    logger, engine, _ = await _build_logger_with_policies(make_deny_policy())
    for agent in ["alpha", "beta"]:
        item = make_context_item(entity_id=agent, trust=0.1)
        evals = await engine.evaluate_context_item(item)
        await logger.log(
            event_type=AuditEventType.CONTEXT_ITEM_GOVERNED,
            agent_id=agent,
            step_id="s1",
            entity_id=item.entity_id,
            evaluations=evals,
        )
    trail = await logger.trail(agent_id="alpha")
    assert len(trail) == 1
    assert trail[0].agent_id == "alpha"


async def test_compliance_report_clean() -> None:
    logger, _, _ = await _build_logger_with_policies()
    report = await logger.compliance_report()
    assert report.compliant is True
    assert report.total_events == 0
    assert report.violations == []


async def test_compliance_report_with_deny() -> None:
    logger, engine, _ = await _build_logger_with_policies(make_deny_policy(min_trust=0.8))
    item = make_context_item(trust=0.2)
    evals = await engine.evaluate_context_item(item)
    await logger.log(
        event_type=AuditEventType.CONTEXT_ITEM_GOVERNED,
        agent_id="a1",
        step_id="s1",
        entity_id=item.entity_id,
        evaluations=evals,
    )
    report = await logger.compliance_report()
    assert report.compliant is False
    assert len(report.violations) == 1


async def test_warn_outcome_does_not_violate() -> None:
    logger, engine, _ = await _build_logger_with_policies(make_warn_policy())
    item = make_context_item(trust=0.9)
    evals = await engine.evaluate_context_item(
        item, verification_status=VerificationStatus.CONTRADICTED
    )
    await logger.log(
        event_type=AuditEventType.CONTEXT_ITEM_GOVERNED,
        agent_id="a1",
        step_id="s1",
        entity_id=item.entity_id,
        evaluations=evals,
    )
    report = await logger.compliance_report()
    assert report.compliant is True
    assert len(report.warnings) == 1


async def test_outcome_deny_beats_warn() -> None:
    deny_p = make_deny_policy(min_trust=0.8)
    warn_p = make_warn_policy()
    logger, engine, _ = await _build_logger_with_policies(deny_p, warn_p)
    item = make_context_item(trust=0.2)
    evals = await engine.evaluate_context_item(
        item, verification_status=VerificationStatus.CONTRADICTED
    )
    event = await logger.log(
        event_type=AuditEventType.CONTEXT_ITEM_GOVERNED,
        agent_id="a1",
        step_id="s1",
        entity_id=item.entity_id,
        evaluations=evals,
    )
    assert event.outcome == PolicyAction.DENY


async def test_no_triggered_policies_outcome_allow() -> None:
    deny_p = make_deny_policy(min_trust=0.5)
    logger, engine, _ = await _build_logger_with_policies(deny_p)
    item = make_context_item(trust=0.9)  # passes policy — won't trigger
    evals = await engine.evaluate_context_item(item)
    event = await logger.log(
        event_type=AuditEventType.CONTEXT_ITEM_GOVERNED,
        agent_id="a1",
        step_id="s1",
        entity_id=item.entity_id,
        evaluations=evals,
    )
    assert event.outcome == PolicyAction.ALLOW
