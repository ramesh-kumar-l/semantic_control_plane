"""Enumerations for the Memory Core domain.

Kept separate from `models.py` so types stay small and single-responsibility
(`99-development-rules.md` §11).
"""

from __future__ import annotations

from enum import StrEnum


class MemoryType(StrEnum):
    """Initial memory taxonomy for Phase 1.

    SEMANTIC   — facts / knowledge.
    EPISODIC   — events / experiences with strong temporal context.
    PROCEDURAL — how-to / skills.
    WORKING    — short-lived scratch memory.
    """

    SEMANTIC = "semantic"
    EPISODIC = "episodic"
    PROCEDURAL = "procedural"
    WORKING = "working"


class SourceType(StrEnum):
    """Origin of a memory (`14-trust-model.md` — source tracking)."""

    AGENT = "agent"
    USER = "user"
    TOOL = "tool"
    SYSTEM = "system"
    INFERENCE = "inference"
    EXTERNAL = "external"


class VerificationStatus(StrEnum):
    """Verification state carried on every memory (`14-trust-model.md`)."""

    UNVERIFIED = "unverified"
    VERIFIED = "verified"
    CONTRADICTED = "contradicted"
    DISPUTED = "disputed"


class LifecycleState(StrEnum):
    """Persisted lifecycle state of a memory (`11-memory-model.md`).

    `Ingest` is a transient pre-storage step, not a persisted state.
    """

    ACTIVE = "active"
    CONSOLIDATED = "consolidated"
    COMPRESSED = "compressed"
    ARCHIVED = "archived"
    EXPIRED = "expired"


class ProvenanceOperation(StrEnum):
    """Operations recorded in a memory's provenance chain."""

    INGEST = "ingest"
    CONSOLIDATE = "consolidate"
    COMPRESS = "compress"
    ARCHIVE = "archive"
    EXPIRE = "expire"
    SUPERSEDE = "supersede"
