"""Unit tests for the TrustEngine service (composition + reconciliation)."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest

from scp.memory import Source, SourceType, VerificationStatus
from scp.trust import Claim, InvalidVerificationTransitionError, TrustEngine, TrustSignal

NOW = datetime(2026, 6, 20, tzinfo=UTC)


def test_assess_combines_signals_and_is_reproducible(
    make_item: Callable[..., SimpleNamespace],
) -> None:
    engine = TrustEngine()
    item = make_item(source_type=SourceType.TOOL, confidence=0.8)
    first = engine.assess(item, now=NOW)
    second = engine.assess(item, now=NOW)
    assert first == second
    # TOOL reliability (0.85) flows into the score via the registry.
    assert first.components.reliability == pytest.approx(0.85)
    assert 0.0 < first.score <= 1.0


def test_recency_lowers_trust_for_older_items(make_item: Callable[..., SimpleNamespace]) -> None:
    engine = TrustEngine()
    fresh = make_item(created_at=NOW)
    old = make_item(created_at=NOW - timedelta(days=360))
    assert engine.assess(old, now=NOW).score < engine.assess(fresh, now=NOW).score


def test_initial_confidence_delegates_to_model() -> None:
    engine = TrustEngine()
    assert engine.initial_confidence(Source(type=SourceType.INFERENCE)) == pytest.approx(0.40)


def test_verify_delegates_and_enforces_policy() -> None:
    engine = TrustEngine()
    assert engine.verify(VerificationStatus.UNVERIFIED, TrustSignal.HUMAN_VERIFIED) == (
        VerificationStatus.VERIFIED
    )
    with pytest.raises(InvalidVerificationTransitionError):
        engine.verify(VerificationStatus.CONTRADICTED, TrustSignal.HUMAN_VERIFIED)


def _claim(cid: str, obj: str, source_type: SourceType) -> Claim:
    return Claim(
        id=cid,
        subject="paris",
        predicate="capital_of",
        object=obj,
        source=Source(type=source_type),
    )


def test_reconcile_contradicts_the_less_reliable_claim() -> None:
    engine = TrustEngine()
    claims = [
        _claim("trusted", "france", SourceType.TOOL),  # reliability 0.85
        _claim("weak", "italy", SourceType.INFERENCE),  # reliability 0.45
    ]
    recommendations = engine.reconcile(claims)
    assert recommendations["trusted"] == VerificationStatus.DISPUTED
    assert recommendations["weak"] == VerificationStatus.CONTRADICTED


def test_reconcile_disputes_both_on_equal_reliability() -> None:
    engine = TrustEngine()
    claims = [
        _claim("a", "france", SourceType.USER),
        _claim("b", "italy", SourceType.USER),
    ]
    recommendations = engine.reconcile(claims)
    assert recommendations == {
        "a": VerificationStatus.DISPUTED,
        "b": VerificationStatus.DISPUTED,
    }


def test_reconcile_ignores_non_conflicting_claims() -> None:
    engine = TrustEngine()
    claims = [
        _claim("a", "france", SourceType.USER),
        _claim("b", "france", SourceType.USER),  # agrees -> no conflict
    ]
    assert engine.reconcile(claims) == {}
