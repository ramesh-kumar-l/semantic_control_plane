"""Pydantic models for the Knowledge Graph.

Entities and relationships carry the **same** first-class trust and temporal
primitives as memories (`TrustMetadata`, `TemporalContext`) — trust travels *with*
facts and is never duplicated or bolted on (`02` boundary rules, `99` §8,
`adr/ADR-003-knowledge-graph-storage.md`).
"""

from __future__ import annotations

from pydantic import BaseModel, Field

# Trust primitives are reused from Memory Core (one cross-cutting concept).
from scp.memory import TemporalContext, TrustMetadata

from .enums import EntityType, RelationType


class Entity(BaseModel):
    """A typed node in the graph with its trust and temporal context.

    `properties` are free-form string key/values for Phase 2; structured/typed
    property schemas are deferred. `memory_refs` link back to Memory Core records
    by id only (no cross-module storage access).
    """

    id: str
    type: EntityType
    name: str
    properties: dict[str, str] = Field(default_factory=dict)
    memory_refs: tuple[str, ...] = ()
    trust: TrustMetadata
    temporal: TemporalContext


class Relationship(BaseModel):
    """A typed, optionally directed edge between two entities.

    Carries trust + temporal context exactly like an entity. `directed=False`
    marks a symmetric relationship traversable from either endpoint.
    """

    id: str
    type: RelationType
    source_id: str
    target_id: str
    directed: bool = True
    properties: dict[str, str] = Field(default_factory=dict)
    trust: TrustMetadata
    temporal: TemporalContext
