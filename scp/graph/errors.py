"""Typed exceptions for the Knowledge Graph.

Explicit, typed failures — no silent errors (`99-development-rules.md` §11).
"""

from __future__ import annotations


class KnowledgeGraphError(Exception):
    """Base class for all Knowledge Graph errors."""


class EntityNotFoundError(KnowledgeGraphError):
    """Raised when an entity id does not exist."""

    def __init__(self, entity_id: str) -> None:
        super().__init__(f"entity not found: {entity_id}")
        self.entity_id = entity_id


class DuplicateEntityError(KnowledgeGraphError):
    """Raised when adding an entity whose id already exists."""

    def __init__(self, entity_id: str) -> None:
        super().__init__(f"entity already exists: {entity_id}")
        self.entity_id = entity_id


class RelationshipNotFoundError(KnowledgeGraphError):
    """Raised when a relationship id does not exist."""

    def __init__(self, relationship_id: str) -> None:
        super().__init__(f"relationship not found: {relationship_id}")
        self.relationship_id = relationship_id


class DuplicateRelationshipError(KnowledgeGraphError):
    """Raised when adding a relationship whose id already exists."""

    def __init__(self, relationship_id: str) -> None:
        super().__init__(f"relationship already exists: {relationship_id}")
        self.relationship_id = relationship_id


class DanglingRelationshipError(KnowledgeGraphError):
    """Raised when a relationship references an entity that does not exist."""

    def __init__(self, relationship_id: str, missing_entity_id: str) -> None:
        super().__init__(
            f"relationship {relationship_id} references missing entity: {missing_entity_id}"
        )
        self.relationship_id = relationship_id
        self.missing_entity_id = missing_entity_id


class InvalidTraversalError(KnowledgeGraphError):
    """Raised when a traversal request is invalid (e.g. non-positive depth)."""
