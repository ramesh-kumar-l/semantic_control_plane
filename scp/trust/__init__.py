"""Trust Engine (Phase 4) — real trust scores, confidence models, source tracking,
verification, and contradiction detection over the first-class trust primitives
that every memory, entity, and relationship already carries (`14-trust-model.md`).

Pure, deterministic, and explainable: no I/O, no storage access, fully
reproducible scores. Public API surface (`02-system-architecture.md`; protected
by `99` §3). See `adr/ADR-005-trust-engine.md`.
"""

from __future__ import annotations

from .confidence import BASE_CONFIDENCE, ConfidenceModel
from .contradiction import ContradictionDetector
from .engine import TrustEngine
from .enums import ContradictionKind, TrustSignal
from .errors import InvalidVerificationTransitionError, TrustEngineError
from .models import (
    Claim,
    Contradiction,
    TrustAssessment,
    TrustBearing,
    TrustComponents,
    TrustWeights,
)
from .registry import DEFAULT_RELIABILITY, SourceRegistry
from .scoring import HALF_LIFE_DAYS, recency_factor, verification_factor
from .verification import VerificationPolicy

__all__ = [
    # Service
    "TrustEngine",
    # Components
    "SourceRegistry",
    "ConfidenceModel",
    "VerificationPolicy",
    "ContradictionDetector",
    # Models
    "TrustWeights",
    "TrustComponents",
    "TrustAssessment",
    "TrustBearing",
    "Claim",
    "Contradiction",
    # Enums
    "TrustSignal",
    "ContradictionKind",
    # Errors
    "TrustEngineError",
    "InvalidVerificationTransitionError",
    # Documented constants / pure helpers
    "DEFAULT_RELIABILITY",
    "BASE_CONFIDENCE",
    "HALF_LIFE_DAYS",
    "recency_factor",
    "verification_factor",
]
