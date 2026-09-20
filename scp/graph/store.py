"""The `GraphStore` port — the storage seam the Knowledge Graph depends on.

Concrete adapters live in `backends/` (`adr/ADR-003-knowledge-graph-storage.md`).
Changing this interface is a protected-architecture change (`99` §3).
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from pydantic import BaseModel, Field

from .enums import EntityType, RelationType, TraversalDirection
from .models import Entity, Relationship


class EntityQuery(BaseModel):
    """Retrieval filter for entities (by type / name / recency)."""

    type: EntityType | None = None
    name: str | None = None
    newest_first: bool = True
    limit: int = Field(default=100, ge=1, le=10_000)
    offset: int = Field(default=0, ge=0)


class RelationshipQuery(BaseModel):
    """Retrieval filter for relationships (by type / endpoints / recency)."""

    type: RelationType | None = None
    source_id: str | None = None
    target_id: str | None = None
    newest_first: bool = True
    limit: int = Field(default=100, ge=1, le=10_000)
    offset: int = Field(default=0, ge=0)


class GraphStore(ABC):
    """Persistence port for graph entities and relationships."""

    # --- Entities ---------------------------------------------------------
    @abstractmethod
    async def add_entity(self, entity: Entity) -> None:
        """Persist a new entity. Raises `DuplicateEntityError` if id exists."""

    @abstractmethod
    async def get_entity(self, entity_id: str) -> Entity | None:
        """Return the entity, or None if absent."""

    @abstractmethod
    async def update_entity(self, entity: Entity) -> None:
        """Overwrite an entity. Raises `EntityNotFoundError` if absent."""

    @abstractmethod
    async def delete_entity(self, entity_id: str) -> bool:
        """Hard-delete an entity, cascading its incident relationships.

        Returns True if an entity was removed.
        """

    @abstractmethod
    async def query_entities(self, query: EntityQuery) -> list[Entity]:
        """Return entities matching the filter, ordered by recency."""

    # --- Relationships ----------------------------------------------------
    @abstractmethod
    async def add_relationship(self, relationship: Relationship) -> None:
        """Persist a new relationship. Raises `DuplicateRelationshipError`."""

    @abstractmethod
    async def get_relationship(self, relationship_id: str) -> Relationship | None:
        """Return the relationship, or None if absent."""

    @abstractmethod
    async def update_relationship(self, relationship: Relationship) -> None:
        """Overwrite a relationship. Raises `RelationshipNotFoundError`."""

    @abstractmethod
    async def delete_relationship(self, relationship_id: str) -> bool:
        """Hard-delete a relationship. Returns True if one was removed."""

    @abstractmethod
    async def query_relationships(self, query: RelationshipQuery) -> list[Relationship]:
        """Return relationships matching the filter, ordered by recency."""

    # --- Adjacency primitive (basis for traversal) ------------------------
    @abstractmethod
    async def neighbors(
        self,
        entity_id: str,
        *,
        direction: TraversalDirection = TraversalDirection.OUTBOUND,
        relation_type: RelationType | None = None,
    ) -> list[Relationship]:
        """Return relationships incident to `entity_id` in `direction`.

        Undirected relationships count as incident for any direction.
        """

    async def close(self) -> None:
        """Release resources. Default no-op; adapters override as needed."""
        return None
