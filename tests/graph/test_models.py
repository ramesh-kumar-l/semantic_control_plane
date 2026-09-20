"""Unit tests for Knowledge Graph models — trust/temporal carried on every fact."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from scp.graph import Entity, EntityType, Relationship, RelationType
from scp.memory import Source, SourceType, TemporalContext, TrustMetadata


def _trust(confidence: float = 0.5) -> TrustMetadata:
    return TrustMetadata(source=Source(type=SourceType.USER), confidence=confidence)


def _temporal() -> TemporalContext:
    now = datetime(2026, 6, 20, tzinfo=UTC)
    return TemporalContext(created_at=now, last_accessed=now)


def test_entity_carries_trust_and_temporal() -> None:
    entity = Entity(
        id="e1",
        type=EntityType.PERSON,
        name="Ada Lovelace",
        trust=_trust(),
        temporal=_temporal(),
    )
    assert entity.trust.source.type is SourceType.USER
    assert entity.temporal.created_at.year == 2026
    assert entity.properties == {}
    assert entity.memory_refs == ()


def test_relationship_defaults_directed() -> None:
    rel = Relationship(
        id="r1",
        type=RelationType.IS_A,
        source_id="e1",
        target_id="e2",
        trust=_trust(),
        temporal=_temporal(),
    )
    assert rel.directed is True


def test_confidence_out_of_range_rejected() -> None:
    with pytest.raises(ValidationError):
        _trust(confidence=1.5)
