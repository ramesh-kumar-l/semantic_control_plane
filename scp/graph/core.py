"""`KnowledgeGraph` — the public service API for Phase 2 Knowledge Graph.

Owns entity & relationship management, graph queries, and traversal. Depends only
on the `GraphStore` port (`store.py`), so the backend is swappable (ADR-003). Pure
BFS lives in `traversal.py`; this module wires it to persistence and attaches
first-class trust metadata to every entity and relationship (`99` §8).
"""

from __future__ import annotations

import uuid
from collections.abc import Callable, Mapping
from datetime import UTC, datetime

# Trust primitives reused from Memory Core (one cross-cutting concept).
from scp.memory import (
    ProvenanceEntry,
    ProvenanceOperation,
    Source,
    SourceType,
    TemporalContext,
    TrustMetadata,
    VerificationStatus,
)

from . import traversal
from .enums import EntityType, RelationType, TraversalDirection
from .errors import (
    DanglingRelationshipError,
    EntityNotFoundError,
    RelationshipNotFoundError,
)
from .models import Entity, Relationship
from .store import EntityQuery, GraphStore, RelationshipQuery
from .traversal import TraversalResult

# Fallback confidence when neither an explicit value nor a confidence model is given.
DEFAULT_CONFIDENCE = 0.5

# A source-aware confidence model (the Trust Engine's `initial_confidence`, Phase 4).
ConfidenceModel = Callable[[Source, VerificationStatus], float]


def _utcnow() -> datetime:
    return datetime.now(UTC)


class KnowledgeGraph:
    """High-level Knowledge Graph API over a pluggable `GraphStore`.

    `clock` and `id_factory` are injectable for deterministic behaviour/tests.
    """

    def __init__(
        self,
        store: GraphStore,
        *,
        clock: Callable[[], datetime] = _utcnow,
        id_factory: Callable[[], str] = lambda: uuid.uuid4().hex,
        default_confidence: float = DEFAULT_CONFIDENCE,
        confidence_model: ConfidenceModel | None = None,
    ) -> None:
        self._store = store
        self._clock = clock
        self._new_id = id_factory
        self._default_confidence = default_confidence
        # When wired, the Trust Engine computes real source-aware confidence,
        # replacing the flat `default_confidence` placeholder (`14-trust-model.md`).
        self._confidence_model = confidence_model

    async def close(self) -> None:
        """Release the underlying store's resources."""
        await self._store.close()

    # --- Entities ---------------------------------------------------------
    async def add_entity(
        self,
        name: str,
        *,
        entity_type: EntityType,
        source_type: SourceType,
        source_identifier: str | None = None,
        properties: Mapping[str, str] | None = None,
        memory_refs: tuple[str, ...] = (),
        confidence: float | None = None,
        verification_status: VerificationStatus = VerificationStatus.UNVERIFIED,
        valid_from: datetime | None = None,
        valid_to: datetime | None = None,
    ) -> Entity:
        """Create and persist a new entity with full trust metadata attached."""
        now = self._clock()
        entity = Entity(
            id=self._new_id(),
            type=entity_type,
            name=name,
            properties=dict(properties or {}),
            memory_refs=memory_refs,
            trust=self._trust(now, source_type, source_identifier, confidence, verification_status),
            temporal=self._temporal(now, valid_from, valid_to),
        )
        await self._store.add_entity(entity)
        return entity

    async def get_entity(self, entity_id: str) -> Entity:
        """Return an entity. Raises `EntityNotFoundError` if absent."""
        entity = await self._store.get_entity(entity_id)
        if entity is None:
            raise EntityNotFoundError(entity_id)
        return entity

    async def query_entities(
        self,
        *,
        entity_type: EntityType | None = None,
        name: str | None = None,
        newest_first: bool = True,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Entity]:
        """Retrieve entities by type / name / recency."""
        return await self._store.query_entities(
            EntityQuery(
                type=entity_type,
                name=name,
                newest_first=newest_first,
                limit=limit,
                offset=offset,
            )
        )

    async def delete_entity(self, entity_id: str) -> bool:
        """Delete an entity and cascade its incident relationships."""
        return await self._store.delete_entity(entity_id)

    # --- Relationships ----------------------------------------------------
    async def add_relationship(
        self,
        source_id: str,
        target_id: str,
        *,
        relation_type: RelationType,
        source_type: SourceType,
        source_identifier: str | None = None,
        directed: bool = True,
        properties: Mapping[str, str] | None = None,
        confidence: float | None = None,
        verification_status: VerificationStatus = VerificationStatus.UNVERIFIED,
        valid_from: datetime | None = None,
        valid_to: datetime | None = None,
    ) -> Relationship:
        """Create a relationship between two existing entities.

        Both endpoints must exist or `DanglingRelationshipError` is raised.
        """
        relationship_id = self._new_id()
        await self._require_entity(source_id, relationship_id)
        await self._require_entity(target_id, relationship_id)
        now = self._clock()
        relationship = Relationship(
            id=relationship_id,
            type=relation_type,
            source_id=source_id,
            target_id=target_id,
            directed=directed,
            properties=dict(properties or {}),
            trust=self._trust(now, source_type, source_identifier, confidence, verification_status),
            temporal=self._temporal(now, valid_from, valid_to),
        )
        await self._store.add_relationship(relationship)
        return relationship

    async def get_relationship(self, relationship_id: str) -> Relationship:
        """Return a relationship. Raises `RelationshipNotFoundError` if absent."""
        relationship = await self._store.get_relationship(relationship_id)
        if relationship is None:
            raise RelationshipNotFoundError(relationship_id)
        return relationship

    async def query_relationships(
        self,
        *,
        relation_type: RelationType | None = None,
        source_id: str | None = None,
        target_id: str | None = None,
        newest_first: bool = True,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Relationship]:
        """Retrieve relationships by type / endpoints / recency."""
        return await self._store.query_relationships(
            RelationshipQuery(
                type=relation_type,
                source_id=source_id,
                target_id=target_id,
                newest_first=newest_first,
                limit=limit,
                offset=offset,
            )
        )

    async def delete_relationship(self, relationship_id: str) -> bool:
        """Delete a single relationship."""
        return await self._store.delete_relationship(relationship_id)

    # --- Traversal & queries ---------------------------------------------
    async def neighbors(
        self,
        entity_id: str,
        *,
        direction: TraversalDirection = TraversalDirection.OUTBOUND,
        relation_type: RelationType | None = None,
    ) -> list[Relationship]:
        """Return relationships incident to an entity. Validates it exists."""
        await self.get_entity(entity_id)
        return await self._store.neighbors(
            entity_id, direction=direction, relation_type=relation_type
        )

    async def traverse(
        self,
        start_id: str,
        *,
        direction: TraversalDirection = TraversalDirection.OUTBOUND,
        max_depth: int = 2,
        relation_type: RelationType | None = None,
    ) -> TraversalResult:
        """Breadth-first traversal from a start entity up to `max_depth` hops."""
        await self.get_entity(start_id)
        return await traversal.breadth_first(
            start_id,
            neighbors_fn=self._neighbors_fn,
            direction=direction,
            max_depth=max_depth,
            relation_type=relation_type,
        )

    async def find_path(
        self,
        source_id: str,
        target_id: str,
        *,
        direction: TraversalDirection = TraversalDirection.OUTBOUND,
        max_depth: int = 6,
        relation_type: RelationType | None = None,
    ) -> list[Relationship] | None:
        """Return a shortest (fewest-hop) path of relationships, or None."""
        await self.get_entity(source_id)
        await self.get_entity(target_id)
        return await traversal.shortest_path(
            source_id,
            target_id,
            neighbors_fn=self._neighbors_fn,
            direction=direction,
            max_depth=max_depth,
            relation_type=relation_type,
        )

    # --- Internals --------------------------------------------------------
    async def _neighbors_fn(
        self,
        entity_id: str,
        direction: TraversalDirection,
        relation_type: RelationType | None,
    ) -> list[Relationship]:
        return await self._store.neighbors(
            entity_id, direction=direction, relation_type=relation_type
        )

    async def _require_entity(self, entity_id: str, relationship_id: str) -> None:
        if await self._store.get_entity(entity_id) is None:
            raise DanglingRelationshipError(relationship_id, entity_id)

    def _trust(
        self,
        now: datetime,
        source_type: SourceType,
        source_identifier: str | None,
        confidence: float | None,
        verification_status: VerificationStatus,
    ) -> TrustMetadata:
        ingest = ProvenanceEntry(operation=ProvenanceOperation.INGEST, timestamp=now)
        source = Source(type=source_type, identifier=source_identifier)
        if confidence is not None:
            resolved = confidence
        elif self._confidence_model is not None:
            resolved = self._confidence_model(source, verification_status)
        else:
            resolved = self._default_confidence
        return TrustMetadata(
            source=source,
            confidence=resolved,
            verification_status=verification_status,
            provenance=(ingest,),
        )

    @staticmethod
    def _temporal(
        now: datetime, valid_from: datetime | None, valid_to: datetime | None
    ) -> TemporalContext:
        return TemporalContext(
            created_at=now, last_accessed=now, valid_from=valid_from, valid_to=valid_to
        )
