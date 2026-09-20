"""Knowledge Graph (Phase 2) — entities, relationships, graph storage, traversal,
and basic graph queries, with trust metadata first-class on every fact.

Builds on Memory Core's trust primitives (`adr/ADR-003-knowledge-graph-storage.md`).
Public API surface (`02-system-architecture.md` boundary; protected by `99` §3).
"""

from __future__ import annotations

from .backends import InMemoryGraphStore, SqliteGraphStore
from .core import KnowledgeGraph
from .enums import EntityType, RelationType, TraversalDirection
from .errors import (
    DanglingRelationshipError,
    DuplicateEntityError,
    DuplicateRelationshipError,
    EntityNotFoundError,
    InvalidTraversalError,
    KnowledgeGraphError,
    RelationshipNotFoundError,
)
from .models import Entity, Relationship
from .store import EntityQuery, GraphStore, RelationshipQuery
from .traversal import TraversalResult, TraversalStep

__all__ = [
    # Service
    "KnowledgeGraph",
    # Port + adapters
    "GraphStore",
    "EntityQuery",
    "RelationshipQuery",
    "InMemoryGraphStore",
    "SqliteGraphStore",
    # Models
    "Entity",
    "Relationship",
    "TraversalResult",
    "TraversalStep",
    # Enums
    "EntityType",
    "RelationType",
    "TraversalDirection",
    # Errors
    "KnowledgeGraphError",
    "EntityNotFoundError",
    "DuplicateEntityError",
    "RelationshipNotFoundError",
    "DuplicateRelationshipError",
    "DanglingRelationshipError",
    "InvalidTraversalError",
]
