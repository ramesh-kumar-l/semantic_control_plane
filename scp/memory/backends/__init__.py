"""Concrete `MemoryStore` adapters (`adr/ADR-002-memory-core-storage.md`)."""

from .in_memory import InMemoryStore
from .sqlite import SqliteStore

__all__ = ["InMemoryStore", "SqliteStore"]
