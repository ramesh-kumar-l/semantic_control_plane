"""Typed exceptions for the Memory Core.

Explicit, typed failures — no silent errors (`99-development-rules.md` §11).
"""

from __future__ import annotations


class MemoryCoreError(Exception):
    """Base class for all Memory Core errors."""


class MemoryNotFoundError(MemoryCoreError):
    """Raised when a memory id does not exist."""

    def __init__(self, memory_id: str) -> None:
        super().__init__(f"memory not found: {memory_id}")
        self.memory_id = memory_id


class DuplicateMemoryError(MemoryCoreError):
    """Raised when storing a record whose id already exists."""

    def __init__(self, memory_id: str) -> None:
        super().__init__(f"memory already exists: {memory_id}")
        self.memory_id = memory_id


class InvalidLifecycleTransitionError(MemoryCoreError):
    """Raised when a lifecycle transition is not permitted."""

    def __init__(self, current: str, target: str) -> None:
        super().__init__(f"invalid lifecycle transition: {current} -> {target}")
        self.current = current
        self.target = target


class ConsolidationError(MemoryCoreError):
    """Raised when a consolidation request is invalid (e.g. too few inputs)."""
