"""Memory Core (Phase 1) — storage, retrieval, consolidation, compression,
lifecycle, with trust metadata as a first-class property of every memory.

Public API surface (`02-system-architecture.md` boundary; protected by `99` §3).
"""

from __future__ import annotations

from .backends import InMemoryStore, SqliteStore
from .core import MemoryCore
from .enums import (
    LifecycleState,
    MemoryType,
    ProvenanceOperation,
    SourceType,
    VerificationStatus,
)
from .errors import (
    ConsolidationError,
    DuplicateMemoryError,
    InvalidLifecycleTransitionError,
    MemoryCoreError,
    MemoryNotFoundError,
)
from .models import (
    MemoryRecord,
    ProvenanceEntry,
    Source,
    TemporalContext,
    TrustMetadata,
)
from .store import MemoryQuery, MemoryStore

__all__ = [
    # Service
    "MemoryCore",
    # Port + adapters
    "MemoryStore",
    "MemoryQuery",
    "InMemoryStore",
    "SqliteStore",
    # Models
    "MemoryRecord",
    "TrustMetadata",
    "TemporalContext",
    "Source",
    "ProvenanceEntry",
    # Enums
    "MemoryType",
    "SourceType",
    "VerificationStatus",
    "LifecycleState",
    "ProvenanceOperation",
    # Errors
    "MemoryCoreError",
    "MemoryNotFoundError",
    "DuplicateMemoryError",
    "InvalidLifecycleTransitionError",
    "ConsolidationError",
]
