"""Enumerations for the Knowledge Graph domain.

Kept separate from `models.py` so types stay small and single-responsibility
(`99-development-rules.md` §11).
"""

from __future__ import annotations

from enum import StrEnum


class EntityType(StrEnum):
    """Initial entity taxonomy for Phase 2.

    CONCEPT      — an idea / topic / abstract thing.
    PERSON       — an individual.
    ORGANIZATION — a company / group / institution.
    LOCATION     — a place.
    EVENT        — something that happened.
    ARTIFACT     — a document / tool / object.
    OTHER        — unclassified.
    """

    CONCEPT = "concept"
    PERSON = "person"
    ORGANIZATION = "organization"
    LOCATION = "location"
    EVENT = "event"
    ARTIFACT = "artifact"
    OTHER = "other"


class RelationType(StrEnum):
    """Initial relationship taxonomy for Phase 2."""

    RELATED_TO = "related_to"
    IS_A = "is_a"
    PART_OF = "part_of"
    HAS_PART = "has_part"
    CAUSES = "causes"
    PRECEDES = "precedes"
    MENTIONS = "mentions"
    DERIVED_FROM = "derived_from"
    OTHER = "other"


class TraversalDirection(StrEnum):
    """Direction to follow edges from a node during traversal.

    OUTBOUND — follow edges where the node is the source.
    INBOUND  — follow edges where the node is the target.
    BOTH     — follow incident edges in either direction.

    Undirected relationships are always treated as incident regardless of direction.
    """

    OUTBOUND = "outbound"
    INBOUND = "inbound"
    BOTH = "both"
