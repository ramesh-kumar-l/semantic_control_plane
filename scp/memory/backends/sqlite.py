"""SQLite `MemoryStore` adapter (via aiosqlite) — durable, offline-first, ACID.

Indexed columns support id/type/recency/lifecycle queries; the full pydantic
record is round-tripped through a JSON `data` column (ADR-002).
"""

from __future__ import annotations

import aiosqlite

from ..errors import DuplicateMemoryError, MemoryNotFoundError
from ..models import MemoryRecord
from ..store import MemoryQuery, MemoryStore

_SCHEMA = """
CREATE TABLE IF NOT EXISTS memories (
    id              TEXT PRIMARY KEY,
    type            TEXT NOT NULL,
    lifecycle_state TEXT NOT NULL,
    created_at      TEXT NOT NULL,
    last_accessed   TEXT NOT NULL,
    data            TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_memories_type ON memories(type);
CREATE INDEX IF NOT EXISTS idx_memories_state ON memories(lifecycle_state);
CREATE INDEX IF NOT EXISTS idx_memories_created ON memories(created_at);
"""


class SqliteStore(MemoryStore):
    """Durable store backed by a single SQLite database file (or ``:memory:``)."""

    def __init__(self, connection: aiosqlite.Connection) -> None:
        self._db = connection

    @classmethod
    async def connect(cls, path: str = ":memory:") -> SqliteStore:
        """Open the database, apply the schema, and return a ready store."""
        connection = await aiosqlite.connect(path)
        await connection.executescript(_SCHEMA)
        await connection.commit()
        return cls(connection)

    async def add(self, record: MemoryRecord) -> None:
        try:
            await self._db.execute(
                "INSERT INTO memories "
                "(id, type, lifecycle_state, created_at, last_accessed, data) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                self._row(record),
            )
        except aiosqlite.IntegrityError as exc:
            raise DuplicateMemoryError(record.id) from exc
        await self._db.commit()

    async def get(self, memory_id: str) -> MemoryRecord | None:
        async with self._db.execute(
            "SELECT data FROM memories WHERE id = ?", (memory_id,)
        ) as cursor:
            row = await cursor.fetchone()
        return MemoryRecord.model_validate_json(row[0]) if row is not None else None

    async def update(self, record: MemoryRecord) -> None:
        cursor = await self._db.execute(
            "UPDATE memories SET "
            "type = ?, lifecycle_state = ?, created_at = ?, last_accessed = ?, data = ? "
            "WHERE id = ?",
            (*self._row(record)[1:], record.id),
        )
        await self._db.commit()
        if cursor.rowcount == 0:
            raise MemoryNotFoundError(record.id)

    async def query(self, query: MemoryQuery) -> list[MemoryRecord]:
        clauses: list[str] = []
        params: list[str] = []
        if query.type is not None:
            clauses.append("type = ?")
            params.append(query.type.value)
        if query.lifecycle_state is not None:
            clauses.append("lifecycle_state = ?")
            params.append(query.lifecycle_state.value)
        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        order = "DESC" if query.newest_first else "ASC"
        sql = f"SELECT data FROM memories{where} ORDER BY created_at {order} LIMIT ? OFFSET ?"
        async with self._db.execute(sql, (*params, query.limit, query.offset)) as cursor:
            rows = await cursor.fetchall()
        return [MemoryRecord.model_validate_json(row[0]) for row in rows]

    async def delete(self, memory_id: str) -> bool:
        cursor = await self._db.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
        await self._db.commit()
        return cursor.rowcount > 0

    async def close(self) -> None:
        await self._db.close()

    @staticmethod
    def _row(record: MemoryRecord) -> tuple[str, str, str, str, str, str]:
        return (
            record.id,
            record.type.value,
            record.lifecycle_state.value,
            record.temporal.created_at.isoformat(),
            record.temporal.last_accessed.isoformat(),
            record.model_dump_json(),
        )
