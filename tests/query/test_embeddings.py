"""Unit tests for deterministic embeddings + cosine similarity."""

from __future__ import annotations

import math

from scp.query import HashingEmbedder
from scp.query.embeddings import cosine, tokenize


def test_tokenize_lowercases_and_splits() -> None:
    assert tokenize("Python, Django 3.0!") == ["python", "django", "3", "0"]


def test_embedding_is_deterministic_across_instances() -> None:
    a = HashingEmbedder(dimension=64).embed("python web framework")
    b = HashingEmbedder(dimension=64).embed("python web framework")
    assert a == b


def test_embedding_dimension_and_unit_norm() -> None:
    embedder = HashingEmbedder(dimension=128)
    vector = embedder.embed("trust aware ranking")
    assert len(vector) == 128
    assert math.isclose(math.sqrt(sum(v * v for v in vector)), 1.0, rel_tol=1e-9)


def test_empty_text_yields_zero_vector() -> None:
    vector = HashingEmbedder(dimension=32).embed("!!! ??? ...")
    assert vector == tuple([0.0] * 32)


def test_cosine_identical_overlap_and_disjoint() -> None:
    embedder = HashingEmbedder(dimension=256)
    python = embedder.embed("python programming language")
    query = embedder.embed("python language")
    unrelated = embedder.embed("atlantic ocean tides")

    assert math.isclose(cosine(python, python), 1.0, rel_tol=1e-9)
    assert cosine(python, unrelated) == 0.0
    # Partial lexical overlap sits strictly between disjoint and identical.
    assert 0.0 < cosine(python, query) < 1.0
