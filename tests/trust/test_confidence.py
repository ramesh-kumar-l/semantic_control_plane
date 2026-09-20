"""Unit tests for the confidence model that replaces the 0.5 placeholder."""

from __future__ import annotations

import pytest

from scp.memory import Source, SourceType, VerificationStatus
from scp.trust import ConfidenceModel


def test_initial_confidence_varies_by_source_and_is_not_flat_half() -> None:
    model = ConfidenceModel()
    user = model.initial(Source(type=SourceType.USER))
    inference = model.initial(Source(type=SourceType.INFERENCE))
    assert user == pytest.approx(0.70)
    assert inference == pytest.approx(0.40)
    assert user != 0.5 and inference != 0.5
    assert user > inference


def test_verification_adjusts_initial_confidence() -> None:
    model = ConfidenceModel()
    source = Source(type=SourceType.USER)
    verified = model.initial(source, VerificationStatus.VERIFIED)
    unverified = model.initial(source, VerificationStatus.UNVERIFIED)
    contradicted = model.initial(source, VerificationStatus.CONTRADICTED)
    assert verified > unverified > contradicted


def test_initial_confidence_is_clamped() -> None:
    model = ConfidenceModel(base={SourceType.USER: 0.95})
    # 0.95 * 1.15 would exceed 1.0 -> clamped.
    assert model.initial(Source(type=SourceType.USER), VerificationStatus.VERIFIED) == 1.0
