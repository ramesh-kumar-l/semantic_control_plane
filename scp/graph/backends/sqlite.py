"""SQLite `GraphStore` adapter (via aiosqlite) — durable, offline-first, ACID.

Two indexed tables (`entities`, `relationships`); the full pydantic record is
round-tripped through a JSON `data` column (`adr/ADR-003-knowledge-graph-storage.md`).
Traversal is done in application code via `neighbors` (no recursive SQL).
"""

from __future__ import annotations

import aiosqlite

from ..enums import RelationType, TraversalDirection
from ..errors import (
    DuplicateEntityError,
    DuplicateRelationshipError,
    EntityNotFoundError,
    RelationshipNotFoundError,
)
from ..models import Entity, Relationship
from ..store import EntityQuery, GraphStore, RelationshipQuery

_SCHEMA = """
CREATE TABLE IF NOT EXISTS entities (
    id          TEXT PRIMARY KEY,
    type        TEXT NOT NULL,
    name        TEXT NOT NULL,
    created_at  TEXT NOT NULL,
    data        TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_entities_type ON entities(type);
CREATE INDEX IF NOT EXISTS idx_entities_name ON entities(name);
CREATE INDEX IF NOT EXISTS idx_entities_created ON entities(created_at);

CREATE TABLE IF NOT EXISTS relationships (
    id          TEXT PRIMARY KEY,
    type        TEXT NOT NULL,
    source_id   TEXT NOT NULL,
    target_id   TEXT NOT NULL,
    directed    INTEGER NOT NULL,
    created_at  TEXT NOT NULL,
    data        TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_rel_type ON relationships(type);
CREATE INDEX IF NOT EXISTS idx_rel_source ON relationships(source_id);
CREATE INDEX IF NOT EXISTS idx_rel_target ON relationships(target_id);
CREATE INDEX IF NOT EXISTS idx_rel_created ON relationships(created_at);
"""


class SqliteGraphStore(GraphStore):
    """Durable graph store backed by a single SQLite database (or ``:memory:``)."""

    def __init__(self, connection: aiosqlite.Connection) -> None:
        self._db = connection

    @classmethod
    async def connect(cls, path: str = ":memory:") -> SqliteGraphStore:
        """Open the database, apply the schema, and return a ready store."""
        connection = await aiosqlite.connect(path)
        await connection.executescript(_SCHEMA)
        await connection.commit()
        return cls(connection)

    # --- Entities ---------------------------------------------------------
    async def add_entity(self, entity: Entity) -> None:
        try:
            await self._db.execute(
                "INSERT INTO entities (id, type, name, created_at, data) VALUES (?, ?, ?, ?, ?)",
                (
                    entity.id,
                    entity.type.value,
                    entity.name,
                    entity.temporal.created_at.isoformat(),
                    entity.model_dump_json(),
                ),
            )
        except aiosqlite.IntegrityError as exc:
            raise DuplicateEntityError(entity.id) from exc
        await self._db.commit()

    async def get_entity(self, entity_id: str) -> Entity | None:
        async with self._db.execute(
            "SELECT data FROM entities WHERE id = ?", (entity_id,)
        ) as cursor:
            row = await cursor.fetchone()
        return Entity.model_validate_json(row[0]) if row is not None else None

    async def update_entity(self, entity: Entity) -> None:
        cursor = await self._db.execute(
            "UPDATE entities SET type = ?, name = ?, created_at = ?, data = ? WHERE id = ?",
            (
                entity.type.value,
                entity.name,
                entity.temporal.created_at.isoformat(),
                entity.model_dump_json(),
                entity.id,
            ),
        )
        await self._db.commit()
        if cursor.rowcount == 0:
            raise EntityNotFoundError(entity.id)

    async def delete_entity(self, entity_id: str) -> bool:
        await self._db.execute(
            "DELETE FROM relationships WHERE source_id = ? OR target_id = ?",
            (entity_id, entity_id),
        )
        cursor = await self._db.execute("DELETE FROM entities WHERE id = ?", (entity_id,))
        await self._db.commit()
        return cursor.rowcount > 0

    async def query_entities(self, query: EntityQuery) -> list[Entity]:
        clauses: list[str] = []
        params: list[str] = []
        if query.type is not None:
            clauses.append("type = ?")
            params.append(query.type.value)
        if query.name is not None:
            clauses.append("name = ?")
            params.append(query.name)
        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        order = "DESC" if query.newest_first else "ASC"
        sql = f"SELECT data FROM entities{where} ORDER BY created_at {order} LIMIT ? OFFSET ?"
        async with self._db.execute(sql, (*params, query.limit, query.offset)) as cursor:
            rows = await cursor.fetchall()
        return [Entity.model_validate_json(row[0]) for row in rows]

    # --- Relationships ----------------------------------------------------
    async def add_relationship(self, relationship: Relationship) -> None:
        try:
            await self._db.execute(
                "INSERT INTO relationships "
                "(id, type, source_id, target_id, directed, created_at, data) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                self._rel_row(relationship),
            )
        except aiosqlite.IntegrityError as exc:
            raise DuplicateRelationshipError(relationship.id) from exc
        await self._db.commit()

    async def get_relationship(self, relationship_id: str) -> Relationship | None:
        async with self._db.execute(
            "SELECT data FROM relationships WHERE id = ?", (relationship_id,)
        ) as cursor:
            row = await cursor.fetchone()
        return Relationship.model_validate_json(row[0]) if row is not None else None

    async def update_relationship(self, relationship: Relationship) -> None:
        cursor = await self._db.execute(
            "UPDATE relationships SET "
            "type = ?, source_id = ?, target_id = ?, directed = ?, created_at = ?, data = ? "
            "WHERE id = ?",
            (*self._rel_row(relationship)[1:], relationship.id),
        )
        await self._db.commit()
        if cursor.rowcount == 0:
            raise RelationshipNotFoundError(relationship.id)

    async def delete_relationship(self, relationship_id: str) -> bool:
        cursor = await self._db.execute(
            "DELETE FROM relationships WHERE id = ?", (relationship_id,)
        )
        await self._db.commit()
        return cursor.rowcount > 0

    async def query_relationships(self, query: RelationshipQuery) -> list[Relationship]:
        clauses: list[str] = []
        params: list[str] = []
        if query.type is not None:
            clauses.append("type = ?")
            params.append(query.type.value)
        if query.source_id is not None:
            clauses.append("source_id = ?")
            params.append(query.source_id)
        if query.target_id is not None:
            clauses.append("target_id = ?")
            params.append(query.target_id)
        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        order = "DESC" if query.newest_first else "ASC"
        sql = f"SELECT data FROM relationships{where} ORDER BY created_at {order} LIMIT ? OFFSET ?"
        async with self._db.execute(sql, (*params, query.limit, query.offset)) as cursor:
            rows = await cursor.fetchall()
        return [Relationship.model_validate_json(row[0]) for row in rows]

    # --- Adjacency --------------------------------------------------------
    async def neighbors(
        self,
        entity_id: str,
        *,
        direction: TraversalDirection = TraversalDirection.OUTBOUND,
        relation_type: RelationType | None = None,
    ) -> list[Relationship]:
        # Incident, then apply direction unless the edge is undirected.
        clauses = ["(source_id = ? OR target_id = ?)"]
        params: list[str] = [entity_id, entity_id]
        if direction is TraversalDirection.OUTBOUND:
            clauses.append("(directed = 0 OR source_id = ?)")
            params.append(entity_id)
        elif direction is TraversalDirection.INBOUND:
            clauses.append("(directed = 0 OR target_id = ?)")
            params.append(entity_id)
        if relation_type is not None:
            clauses.append("type = ?")
            params.append(relation_type.value)
        sql = (
            f"SELECT data FROM relationships WHERE {' AND '.join(clauses)} ORDER BY created_at ASC"
        )
        async with self._db.execute(sql, params) as cursor:
            rows = await cursor.fetchall()
        return [Relationship.model_validate_json(row[0]) for row in rows]

    async def close(self) -> None:
        await self._db.close()

    @staticmethod
    def _rel_row(rel: Relationship) -> tuple[str, str, str, str, int, str, str]:
        return (
            rel.id,
            rel.type.value,
            rel.source_id,
            rel.target_id,
            int(rel.directed),
            rel.temporal.created_at.isoformat(),
            rel.model_dump_json(),
        )
