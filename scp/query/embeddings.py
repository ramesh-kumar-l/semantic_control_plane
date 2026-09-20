"""Deterministic, offline text embeddings for the Semantic Query Engine.

The default `HashingEmbedder` maps token frequencies into a fixed-dimension,
L2-normalized vector using a *stable* hash (blake2b — not Python's salted
``hash()``). This keeps embeddings deterministic across processes and fully
offline (no external model/API), satisfying the offline-first + deterministic
NFRs (`02-system-architecture.md`). A learned/model-based embedder can later be
dropped in behind the `Embedder` port without touching the engine
(`adr/ADR-004-semantic-query-engine.md`).
"""

from __future__ import annotations

import hashlib
import math
import re
from abc import ABC, abstractmethod

_TOKEN_RE = re.compile(r"[a-z0-9]+")

# Embedding vectors are immutable tuples of floats.
Vector = tuple[float, ...]


def tokenize(text: str) -> list[str]:
    """Lowercase, split on non-alphanumeric runs. Deterministic."""
    return _TOKEN_RE.findall(text.lower())


def cosine(a: Vector, b: Vector) -> float:
    """Cosine similarity in [0.0, 1.0] for non-negative vectors; 0.0 if either is zero."""
    if len(a) != len(b):
        raise ValueError(f"vector dimension mismatch: {len(a)} != {len(b)}")
    dot = 0.0
    norm_a = 0.0
    norm_b = 0.0
    for x, y in zip(a, b, strict=True):
        dot += x * y
        norm_a += x * x
        norm_b += y * y
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / math.sqrt(norm_a * norm_b)


class Embedder(ABC):
    """Port: turn text into a fixed-dimension vector."""

    @property
    @abstractmethod
    def dimension(self) -> int:
        """The fixed dimensionality of produced vectors."""

    @abstractmethod
    def embed(self, text: str) -> Vector:
        """Return the embedding for `text` (zero vector if no tokens)."""


class HashingEmbedder(Embedder):
    """Hashing (feature-hashing) bag-of-words embedder. Deterministic & offline."""

    def __init__(self, dimension: int = 256) -> None:
        if dimension < 1:
            raise ValueError(f"dimension must be >= 1, got {dimension}")
        self._dimension = dimension

    @property
    def dimension(self) -> int:
        return self._dimension

    def embed(self, text: str) -> Vector:
        buckets = [0.0] * self._dimension
        for token in tokenize(text):
            buckets[self._bucket(token)] += 1.0
        norm = math.sqrt(sum(v * v for v in buckets))
        if norm == 0.0:
            return tuple(buckets)
        return tuple(v / norm for v in buckets)

    def _bucket(self, token: str) -> int:
        digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
        return int.from_bytes(digest, "big") % self._dimension
