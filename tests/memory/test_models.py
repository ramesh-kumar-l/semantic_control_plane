"""Unit tests for Memory Core models and their validation bounds."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from scp.memory import (
    LifecycleState,
    MemoryRecord,
    MemoryType,
    Source,
    SourceType,
    TemporalContext,
    TrustMetadata,
    VerificationStatus,
)

_NOW = datetime(2026, 6, 20, tzinfo=UTC)


def _record(confidence: float) -> MemoryRecord:
    return MemoryRecord(
        id="mem-1",
        type=MemoryType.SEMANTIC,
        content="the sky is blue",
        trust=TrustMetadata(source=Source(type=SourceType.USER), confidence=confidence),
        temporal=TemporalContext(created_at=_NOW, last_accessed=_NOW),
    )


def test_record_defaults() -> None:
    record = _record(0.5)
    assert record.lifecycle_state is LifecycleState.ACTIVE
    assert record.trust.verification_status is VerificationStatus.UNVERIFIED
    assert record.trust.provenance == ()


@pytest.mark.parametrize("bad", [-0.1, 1.1])
def test_confidence_must_be_normalized(bad: float) -> None:
    with pytest.raises(ValidationError):
        _record(bad)


def test_source_is_frozen() -> None:
    source = Source(type=SourceType.AGENT, identifier="agent-7")
    with pytest.raises(ValidationError):
        source.type = SourceType.USER  # type: ignore[misc]
