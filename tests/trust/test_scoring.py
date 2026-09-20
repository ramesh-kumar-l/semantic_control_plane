"""Unit tests for the pure trust-scoring math (deterministic + explainable)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from scp.memory import VerificationStatus
from scp.trust import HALF_LIFE_DAYS, TrustWeights, recency_factor, verification_factor
from scp.trust.scoring import assess

NOW = datetime(2026, 6, 20, tzinfo=UTC)


def test_recency_decays_by_half_life() -> None:
    assert recency_factor(NOW, NOW) == 1.0
    one_half_life_ago = NOW - timedelta(days=HALF_LIFE_DAYS)
    assert recency_factor(one_half_life_ago, NOW) == pytest.approx(0.5)
    # Future-dated assertions are not penalized.
    assert recency_factor(NOW + timedelta(days=10), NOW) == 1.0


def test_verification_factor_mapping() -> None:
    assert verification_factor(VerificationStatus.VERIFIED) == 1.0
    assert (
        verification_factor(VerificationStatus.UNVERIFIED)
        > verification_factor(VerificationStatus.DISPUTED)
        > verification_factor(VerificationStatus.CONTRADICTED)
    )


def test_assess_is_reproducible_and_records_components() -> None:
    weights = TrustWeights()
    first = assess(
        reliability=0.8,
        confidence=0.6,
        created_at=NOW,
        now=NOW,
        verification_status=VerificationStatus.VERIFIED,
        weights=weights,
    )
    second = assess(
        reliability=0.8,
        confidence=0.6,
        created_at=NOW,
        now=NOW,
        verification_status=VerificationStatus.VERIFIED,
        weights=weights,
    )
    assert first == second  # reproducible

    # base is the weight-normalized blend; recency == 1.0 here (created == now).
    total_w = weights.reliability + weights.confidence + weights.recency
    expected_base = (
        weights.reliability * 0.8 + weights.confidence * 0.6 + weights.recency * 1.0
    ) / total_w
    assert first.base == pytest.approx(expected_base)
    assert first.score == pytest.approx(expected_base)  # verified gate == 1.0
    assert first.components.reliability == pytest.approx(0.8)
    assert f"trust={first.score:.3f}" in first.explanation


def test_verification_gate_strongly_demotes_contradicted() -> None:
    weights = TrustWeights()
    verified = assess(
        reliability=0.9,
        confidence=0.9,
        created_at=NOW,
        now=NOW,
        verification_status=VerificationStatus.VERIFIED,
        weights=weights,
    )
    contradicted = assess(
        reliability=0.9,
        confidence=0.9,
        created_at=NOW,
        now=NOW,
        verification_status=VerificationStatus.CONTRADICTED,
        weights=weights,
    )
    assert verified.base == pytest.approx(contradicted.base)  # same signals
    assert contradicted.score < verified.score
    assert contradicted.score == pytest.approx(verified.base * 0.1)
