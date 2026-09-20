"""Unit tests for the source reliability registry."""

from __future__ import annotations

import pytest

from scp.memory import Source, SourceType
from scp.trust import DEFAULT_RELIABILITY, SourceRegistry


def test_default_reliability_by_type() -> None:
    registry = SourceRegistry()
    expected = DEFAULT_RELIABILITY[SourceType.TOOL]
    assert registry.reliability(Source(type=SourceType.TOOL)) == expected
    assert registry.reliability(Source(type=SourceType.INFERENCE)) == pytest.approx(0.45)


def test_identifier_override_wins() -> None:
    registry = SourceRegistry()
    registry.register(SourceType.EXTERNAL, "vetted-api", 0.95)
    vetted = Source(type=SourceType.EXTERNAL, identifier="vetted-api")
    unknown = Source(type=SourceType.EXTERNAL, identifier="random")
    assert registry.reliability(vetted) == pytest.approx(0.95)
    assert registry.reliability(unknown) == pytest.approx(0.55)


def test_attached_reliability_is_fallback_below_override() -> None:
    registry = SourceRegistry()
    # No registered override -> the value attached on the Source is honored.
    source = Source(type=SourceType.AGENT, identifier="a1", reliability=0.9)
    assert registry.reliability(source) == pytest.approx(0.9)


def test_register_rejects_out_of_range() -> None:
    registry = SourceRegistry()
    with pytest.raises(ValueError):
        registry.register(SourceType.USER, "u", 1.5)
