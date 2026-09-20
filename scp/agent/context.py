"""`ContextAssembler` — builds the context window for each agent step.

Retrieves relevant entities via the Semantic Query Engine, fetches each
entity from the Knowledge Graph for trust assessment, then assembles an
ordered `AgentContext` with real, explainable trust scores.

Boundary: all access is via public APIs (SemanticQueryEngine, KnowledgeGraph,
TrustEngine). The assembler never reaches into storage directly
(`02-system-architecture.md`).
"""

from __future__ import annotations

from datetime import UTC, datetime

from scp.graph import EntityNotFoundError, KnowledgeGraph
from scp.query import SemanticQueryEngine
from scp.trust import TrustEngine

from .errors import ContextAssemblyError
from .models import AgentContext, ContextItem


class ContextAssembler:
    """Assembles an `AgentContext` from retrieval + trust assessment."""

    def __init__(
        self,
        query_engine: SemanticQueryEngine,
        trust_engine: TrustEngine,
        graph: KnowledgeGraph,
    ) -> None:
        self._query = query_engine
        self._trust = trust_engine
        self._graph = graph

    async def assemble(
        self,
        query: str,
        *,
        max_items: int = 10,
        expand_hops: int = 1,
        now: datetime | None = None,
    ) -> AgentContext:
        """Search, assess trust for each result, return a ranked AgentContext.

        Items are ordered by retrieval rank (highest semantic + graph + trust score
        first). Trust assessment uses TrustEngine for explainability and recency.
        """
        moment = now if now is not None else datetime.now(UTC)

        try:
            result = await self._query.search(query, top_k=max_items, expand_hops=expand_hops)
        except Exception as exc:
            raise ContextAssemblyError(f"Retrieval failed for {query!r}: {exc}") from exc

        items: list[ContextItem] = []
        for scored in result.results:
            try:
                entity = await self._graph.get_entity(scored.entity_id)
            except EntityNotFoundError:
                continue  # entity removed after indexing — skip silently
            assessment = self._trust.assess(entity, now=moment)
            items.append(
                ContextItem(
                    entity_id=scored.entity_id,
                    name=scored.name,
                    content_summary=_summarize(entity.name, entity.properties),
                    trust_score=assessment.score,
                    explanation=assessment.explanation,
                )
            )

        return AgentContext(query=query, items=items, assembled_at=moment)


def _summarize(name: str, properties: dict[str, str]) -> str:
    """Short human-readable summary of an entity for context display."""
    parts = [name]
    for k, v in list(properties.items())[:3]:
        parts.append(f"{k}={v}")
    return "; ".join(parts)
