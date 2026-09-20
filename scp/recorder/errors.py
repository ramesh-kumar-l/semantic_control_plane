"""Typed exceptions for the Agent Flight Recorder."""

from __future__ import annotations


class RecorderError(Exception):
    """Base class for all Flight Recorder errors."""


class RecordNotFoundError(RecorderError):
    """Raised when a record_id or step_id is not found in the store."""

    def __init__(self, identifier: str) -> None:
        super().__init__(f"Record not found: {identifier!r}")
        self.identifier = identifier


class ReplayError(RecorderError):
    """Raised when a replay operation cannot be completed."""


class TraceError(RecorderError):
    """Raised when a trace operation fails."""


class DebugError(RecorderError):
    """Raised when a root-cause analysis cannot be completed."""
