"""Agent Runtime enums — lifecycle states and tool statuses."""

from __future__ import annotations

from enum import StrEnum


class AgentStatus(StrEnum):
    IDLE = "idle"  # created, not yet run
    RUNNING = "running"  # actively processing
    PAUSED = "paused"  # execution suspended
    STOPPED = "stopped"  # terminated normally
    FAILED = "failed"  # terminated with error


class ToolStatus(StrEnum):
    SUCCESS = "success"
    ERROR = "error"
    TIMEOUT = "timeout"
