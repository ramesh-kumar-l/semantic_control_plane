"""Concrete `VectorStore` adapters (`adr/ADR-004-semantic-query-engine.md`)."""

from __future__ import annotations

from .in_memory import InMemoryVectorStore

__all__ = ["InMemoryVectorStore"]
