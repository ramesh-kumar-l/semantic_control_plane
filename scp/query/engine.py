"""`SemanticQueryEngine` — the public service API for Phase 3.

Hybrid retrieval over the Knowledge Graph: a query is embedded, matched against a
vector index to find lexical *seed* entities, then expanded along graph edges
(Phase 2 traversal) to surface related-but-lexically-dissimilar entities. Results
are fused and ranked with a trust-aware, explainable scorer.

Boundaries (`02-system-architecture.md`): the engine uses only the `KnowledgeGraph`
public API and the `VectorStore` port — it never reaches into another module's
storage. The vector index is a derived structure rebuilt via `reindex`.
"""

from __future__ import annotations

from scp.graph import Entity, EntityNotFoundError, KnowledgeGraph, TraversalDirection

from . import planner, ranking
from .embeddings import Embedder, HashingEmbedder, Vector, cosine, tokenize
from .enums import RetrievalStrategy
from .errors import EmptyQueryError
from .models import QueryPlan, RankingWeights, RetrievalResult
from .ranking import Candidate
from .vector_store import VectorStore


class SemanticQueryEngine:
    """Hybrid vector + graph retrieval with trust-aware ranking."""

    def __init__(
        self,
        graph: KnowledgeGraph,
        vector_store: VectorStore,
        *,
        embedder: Embedder | None = None,
        weights: RankingWeights | None = None,
    ) -> None:
        self._graph = graph
        self._vectors = vector_store
        self._embedder = embedder if embedder is not None else HashingEmbedder()
        self._weights = weights if weights is not None else RankingWeights()

    async def close(self) -> None:
        """Release the vector index's resources."""
        await self._vectors.close()

    # --- Indexing ---------------------------------------------------------
    async def index_entity(self, entity: Entity, *, extra_text: str = "") -> None:
        """Embed an entity's searchable text and upsert it into the index.

        `extra_text` lets callers fold in referenced memory content so it
        influences semantic matching without the engine reading Memory storage.
        """
        vector = self._embedder.embed(_entity_text(entity, extra_text))
        await self._vectors.upsert(entity.id, vector)

    async def remove_entity(self, entity_id: str) -> bool:
        """Drop an entity from the index. Returns True if it was present."""
        return await self._vectors.delete(entity_id)

    async def reindex(self, *, batch: int = 1000) -> int:
        """Rebuild the whole index from the current graph. Returns entity count."""
        await self._vectors.clear()
        count = 0
        offset = 0
        while True:
            entities = await self._graph.query_entities(limit=batch, offset=offset)
            if not entities:
                break
            for entity in entities:
                await self.index_entity(entity)
            count += len(entities)
            offset += len(entities)
        return count

    # --- Retrieval --------------------------------------------------------
    async def search(
        self,
        text: str,
        *,
        top_k: int = 10,
        expand_hops: int = 1,
        strategy: RetrievalStrategy | None = None,
    ) -> RetrievalResult:
        """Run a hybrid query and return ranked, explainable results."""
        if not tokenize(text):
            raise EmptyQueryError(text)

        query_plan = planner.plan(
            top_k=top_k, expand_hops=expand_hops, decay=0.5, strategy=strategy
        )
        query_vector = self._embedder.embed(text)

        candidates = await self._collect(query_vector, query_plan)
        weights = _effective_weights(self._weights, query_plan.strategy)
        ranked = ranking.rank(list(candidates.values()), weights, top_k=query_plan.top_k)
        return RetrievalResult(query=text, strategy=query_plan.strategy, results=ranked)

    # --- Internals --------------------------------------------------------
    async def _collect(self, query_vector: Vector, plan: QueryPlan) -> dict[str, Candidate]:
        """Gather seed (vector) and expanded (graph) candidates by entity id."""
        candidates: dict[str, Candidate] = {}

        seeds = await self._vectors.search(query_vector, plan.seed_k)
        for match in seeds:
            entity = await self._safe_entity(match.id)
            if entity is not None:
                candidates[match.id] = Candidate(entity=entity, semantic=match.score)

        if plan.expand_hops > 0:
            for match in seeds:
                await self._expand(match.id, match.score, query_vector, plan, candidates)
        return candidates

    async def _expand(
        self,
        seed_id: str,
        seed_score: float,
        query_vector: Vector,
        plan: QueryPlan,
        candidates: dict[str, Candidate],
    ) -> None:
        """Add graph-reachable entities, scoring proximity by hop-decayed seed score."""
        if seed_score == 0.0:
            return  # a zero-similarity seed can never contribute graph proximity
        if seed_id not in candidates:
            return  # seed entity vanished from the graph; skip its expansion
        result = await self._graph.traverse(
            seed_id, direction=TraversalDirection.BOTH, max_depth=plan.expand_hops
        )
        for step in result.steps:
            if step.depth == 0:
                continue
            proximity = seed_score * (plan.decay**step.depth)
            existing = candidates.get(step.entity_id)
            if existing is not None:
                if proximity > existing.graph:
                    existing.graph = proximity
                    existing.hops = step.depth
                continue
            entity = await self._safe_entity(step.entity_id)
            if entity is None:
                continue
            semantic = await self._semantic(step.entity_id, query_vector)
            candidates[step.entity_id] = Candidate(
                entity=entity, semantic=semantic, graph=proximity, hops=step.depth
            )

    async def _semantic(self, entity_id: str, query_vector: Vector) -> float:
        """Cosine of an entity's indexed vector to the query (0 if not indexed)."""
        stored = await self._vectors.get(entity_id)
        return cosine(query_vector, stored) if stored is not None else 0.0

    async def _safe_entity(self, entity_id: str) -> Entity | None:
        try:
            return await self._graph.get_entity(entity_id)
        except EntityNotFoundError:
            return None


def _entity_text(entity: Entity, extra_text: str = "") -> str:
    """The searchable text for an entity: its name, property values, and extras."""
    parts = [entity.name, *entity.properties.values()]
    if extra_text:
        parts.append(extra_text)
    return " ".join(parts)


def _effective_weights(weights: RankingWeights, strategy: RetrievalStrategy) -> RankingWeights:
    """Mask signal weights to match the strategy."""
    if strategy is RetrievalStrategy.VECTOR_ONLY:
        return weights.model_copy(update={"graph": 0.0})
    if strategy is RetrievalStrategy.GRAPH_ONLY:
        return weights.model_copy(update={"semantic": 0.0})
    return weights
