"""Trust test fixtures: a factory for trust-bearing items at a fixed instant."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from scp.memory import Source, SourceType, TemporalContext, TrustMetadata, VerificationStatus

NOW = datetime(2026, 6, 20, tzinfo=UTC)


@pytest.fixture
def make_item() -> Callable[..., SimpleNamespace]:
    """Build a minimal object satisfying the `TrustBearing` protocol."""

    def _make(
        *,
        source_type: SourceType = SourceType.USER,
        identifier: str | None = None,
        reliability: float | None = None,
        confidence: float = 0.6,
        verification: VerificationStatus = VerificationStatus.UNVERIFIED,
        created_at: datetime = NOW,
    ) -> SimpleNamespace:
        trust = TrustMetadata(
            source=Source(type=source_type, identifier=identifier, reliability=reliability),
            confidence=confidence,
            verification_status=verification,
        )
        temporal = TemporalContext(created_at=created_at, last_accessed=created_at)
        return SimpleNamespace(trust=trust, temporal=temporal)

    return _make
