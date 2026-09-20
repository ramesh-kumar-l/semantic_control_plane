"""Source registry — reliability weighting per origin (`14-trust-model.md`).

Reliability answers *"how much do we trust this source?"* — distinct from an
assertion's own confidence. Defaults are per `SourceType`; specific origins can
be registered with an override (e.g. a vetted external API outranks an unknown
one). The registry is the authoritative owner of reliability (`Source.reliability`
is honored as a fallback when no override is registered).
"""

from __future__ import annotations

from scp.memory import Source, SourceType

# Documented default reliability per source kind (explainable, not opaque).
DEFAULT_RELIABILITY: dict[SourceType, float] = {
    SourceType.USER: 0.75,
    SourceType.TOOL: 0.85,
    SourceType.SYSTEM: 0.80,
    SourceType.AGENT: 0.65,
    SourceType.EXTERNAL: 0.55,
    SourceType.INFERENCE: 0.45,
}


class SourceRegistry:
    """Resolves a `Source` to a [0, 1] reliability weight."""

    def __init__(
        self,
        *,
        defaults: dict[SourceType, float] | None = None,
        overrides: dict[tuple[SourceType, str], float] | None = None,
    ) -> None:
        self._defaults = dict(defaults or DEFAULT_RELIABILITY)
        self._overrides = dict(overrides or {})

    def register(self, source_type: SourceType, identifier: str, reliability: float) -> None:
        """Pin a reliability weight for a specific (type, identifier) origin."""
        if not 0.0 <= reliability <= 1.0:
            raise ValueError("reliability must be in [0.0, 1.0]")
        self._overrides[(source_type, identifier)] = reliability

    def reliability(self, source: Source) -> float:
        """Reliability for a source: identifier override → attached value → type default.

        The type default falls back to 0.5 only for an unknown source kind.
        """
        if source.identifier is not None:
            override = self._overrides.get((source.type, source.identifier))
            if override is not None:
                return override
        if source.reliability is not None:
            return source.reliability
        return self._defaults.get(source.type, 0.5)
