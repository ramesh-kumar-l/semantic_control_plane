"""Typed exceptions for the Semantic Query Engine.

Explicit, typed failures — no silent errors (`99-development-rules.md` §11).
"""

from __future__ import annotations


class SemanticQueryError(Exception):
    """Base class for all Semantic Query Engine errors."""


class EmptyQueryError(SemanticQueryError):
    """Raised when a query has no usable tokens to embed."""

    def __init__(self, text: str) -> None:
        super().__init__(f"query has no searchable tokens: {text!r}")
        self.text = text
