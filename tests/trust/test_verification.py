"""Unit tests for the verification state machine."""

from __future__ import annotations

import pytest

from scp.memory import VerificationStatus
from scp.trust import InvalidVerificationTransitionError, TrustSignal, VerificationPolicy


def test_signal_moves_to_target_status() -> None:
    policy = VerificationPolicy()
    assert policy.apply(VerificationStatus.UNVERIFIED, TrustSignal.HUMAN_VERIFIED) == (
        VerificationStatus.VERIFIED
    )
    assert policy.apply(VerificationStatus.VERIFIED, TrustSignal.CONTRADICTED_BY_SOURCE) == (
        VerificationStatus.CONTRADICTED
    )


def test_contradicted_cannot_jump_straight_to_verified() -> None:
    policy = VerificationPolicy()
    with pytest.raises(InvalidVerificationTransitionError):
        policy.apply(VerificationStatus.CONTRADICTED, TrustSignal.HUMAN_VERIFIED)


def test_contradiction_is_overturned_by_reopening_first() -> None:
    policy = VerificationPolicy()
    disputed = policy.apply(VerificationStatus.CONTRADICTED, TrustSignal.REOPENED)
    assert disputed == VerificationStatus.DISPUTED
    assert policy.apply(disputed, TrustSignal.HUMAN_VERIFIED) == VerificationStatus.VERIFIED


def test_same_state_signal_is_idempotent() -> None:
    policy = VerificationPolicy()
    assert policy.apply(VerificationStatus.VERIFIED, TrustSignal.CORROBORATED) == (
        VerificationStatus.VERIFIED
    )
