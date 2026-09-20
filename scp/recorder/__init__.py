"""Agent Flight Recorder (Phase 6) — replay, traceability, root-cause analysis.

Every agent decision is reconstructable from recorded evidence.

Public API surface (`02-system-architecture.md`; protected by `99` §3).
See `adr/ADR-007-flight-recorder.md`.
"""

from __future__ import annotations

from .backends.in_memory import InMemoryRecordStore
from .debug import DebugEngine
from .errors import DebugError, RecorderError, RecordNotFoundError, ReplayError, TraceError
from .models import (
    RecordedStep,
    RecordQuery,
    ReplaySession,
    RootCauseReport,
    Trace,
    TraceAppearance,
)
from .recorder import FlightRecorder
from .replay import ReplayEngine
from .store import RecordStore
from .trace import TraceEngine

__all__ = [
    # Primary service
    "FlightRecorder",
    # Supporting engines
    "ReplayEngine",
    "TraceEngine",
    "DebugEngine",
    # Port
    "RecordStore",
    # Backend
    "InMemoryRecordStore",
    # Models
    "RecordedStep",
    "RecordQuery",
    "ReplaySession",
    "Trace",
    "TraceAppearance",
    "RootCauseReport",
    # Errors
    "RecorderError",
    "RecordNotFoundError",
    "ReplayError",
    "TraceError",
    "DebugError",
]
