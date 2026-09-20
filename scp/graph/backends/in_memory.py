"""In-memory `GraphStore` adapter — deterministic, no I/O. For tests/dev."""

from __future__ import annotations

from ..enums import RelationType, TraversalDirection
from ..errors import (
    DuplicateEntityError,
    DuplicateRelationshipError,
    EntityNotFoundError,
    RelationshipNotFoundError,
)
from ..models import Entity, Relationship
from ..store import EntityQuery, GraphStore, RelationshipQuery


class InMemoryGraphStore(GraphStore):
    """Dict-backed store. Returns deep copies so callers can't mutate state."""

    def __init__(self) -> None:
        self._entities: dict[str, Entity] = {}
        self._relationships: dict[str, Relationship] = {}

    # --- Entities ---------------------------------------------------------
    async def add_entity(self, entity: Entity) -> None:
        if entity.id in self._entities:
            raise DuplicateEntityError(entity.id)
        self._entities[entity.id] = entity.model_copy(deep=True)

    async def get_entity(self, entity_id: str) -> Entity | None:
        entity = self._entities.get(entity_id)
        return entity.model_copy(deep=True) if entity is not None else None

    async def update_entity(self, entity: Entity) -> None:
        if entity.id not in self._entities:
            raise EntityNotFoundError(entity.id)
        self._entities[entity.id] = entity.model_copy(deep=True)

    async def delete_entity(self, entity_id: str) -> bool:
        if self._entities.pop(entity_id, None) is None:
            return False
        incident = [
            rid
            for rid, rel in self._relationships.items()
            if entity_id in (rel.source_id, rel.target_id)
        ]
        for rid in incident:
            del self._relationships[rid]
        return True

    async def query_entities(self, query: EntityQuery) -> list[Entity]:
        matches = [
            entity
            for entity in self._entities.values()
            if (query.type is None or entity.type == query.type)
            and (query.name is None or entity.name == query.name)
        ]
        matches.sort(key=lambda e: e.temporal.created_at, reverse=query.newest_first)
        window = matches[query.offset : query.offset + query.limit]
        return [entity.model_copy(deep=True) for entity in window]

    # --- Relationships ----------------------------------------------------
    async def add_relationship(self, relationship: Relationship) -> None:
        if relationship.id in self._relationships:
            raise DuplicateRelationshipError(relationship.id)
        self._relationships[relationship.id] = relationship.model_copy(deep=True)

    async def get_relationship(self, relationship_id: str) -> Relationship | None:
        rel = self._relationships.get(relationship_id)
        return rel.model_copy(deep=True) if rel is not None else None

    async def update_relationship(self, relationship: Relationship) -> None:
        if relationship.id not in self._relationships:
            raise RelationshipNotFoundError(relationship.id)
        self._relationships[relationship.id] = relationship.model_copy(deep=True)

    async def delete_relationship(self, relationship_id: str) -> bool:
        return self._relationships.pop(relationship_id, None) is not None

    async def query_relationships(self, query: RelationshipQuery) -> list[Relationship]:
        matches = [
            rel
            for rel in self._relationships.values()
            if (query.type is None or rel.type == query.type)
            and (query.source_id is None or rel.source_id == query.source_id)
            and (query.target_id is None or rel.target_id == query.target_id)
        ]
        matches.sort(key=lambda r: r.temporal.created_at, reverse=query.newest_first)
        window = matches[query.offset : query.offset + query.limit]
        return [rel.model_copy(deep=True) for rel in window]

    # --- Adjacency --------------------------------------------------------
    async def neighbors(
        self,
        entity_id: str,
        *,
        direction: TraversalDirection = TraversalDirection.OUTBOUND,
        relation_type: RelationType | None = None,
    ) -> list[Relationship]:
        matches = [
            rel
            for rel in self._relationships.values()
            if _is_incident(rel, entity_id, direction)
            and (relation_type is None or rel.type == relation_type)
        ]
        matches.sort(key=lambda r: r.temporal.created_at)
        return [rel.model_copy(deep=True) for rel in matches]


def _is_incident(relationship: Relationship, entity_id: str, direction: TraversalDirection) -> bool:
    """Whether `relationship` should be followed from `entity_id` in `direction`."""
    is_source = relationship.source_id == entity_id
    is_target = relationship.target_id == entity_id
    if not (is_source or is_target):
        return False
    if not relationship.directed or direction is TraversalDirection.BOTH:
        return True
    if direction is TraversalDirection.OUTBOUND:
        return is_source
    return is_target  # INBOUND
