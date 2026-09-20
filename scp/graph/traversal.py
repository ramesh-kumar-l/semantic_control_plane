"""Pure graph traversal — breadth-first search over an adjacency function.

No storage dependency: callers pass an async `neighbors_fn` (the `GraphStore`
adjacency primitive). This keeps traversal backend-agnostic, deterministic, and
unit-testable in isolation (`adr/ADR-003-knowledge-graph-storage.md`).
"""

from __future__ import annotations

from collections import deque
from collections.abc import Awaitable, Callable

from pydantic import BaseModel

from .enums import RelationType, TraversalDirection
from .errors import InvalidTraversalError
from .models import Relationship

# (entity_id, direction, relation_type) -> incident relationships.
NeighborsFn = Callable[
    [str, TraversalDirection, RelationType | None],
    Awaitable[list[Relationship]],
]


class TraversalStep(BaseModel):
    """One visited node and the depth (hops) at which it was first reached."""

    entity_id: str
    depth: int


class TraversalResult(BaseModel):
    """Outcome of a BFS: visited nodes (with depth) and traversed edges."""

    steps: list[TraversalStep]
    relationships: list[Relationship]


def _other_endpoint(relationship: Relationship, entity_id: str) -> str:
    """Return the endpoint of `relationship` that is not `entity_id`."""
    if relationship.source_id == entity_id:
        return relationship.target_id
    return relationship.source_id


async def breadth_first(
    start_id: str,
    *,
    neighbors_fn: NeighborsFn,
    direction: TraversalDirection = TraversalDirection.OUTBOUND,
    max_depth: int = 2,
    relation_type: RelationType | None = None,
) -> TraversalResult:
    """BFS from `start_id` up to `max_depth` hops.

    Visits each node once; records the first (shortest) depth it was reached at
    and every edge actually traversed. Deterministic given a deterministic
    `neighbors_fn` ordering.
    """
    if max_depth < 1:
        raise InvalidTraversalError(f"max_depth must be >= 1, got {max_depth}")

    seen: set[str] = {start_id}
    steps: list[TraversalStep] = [TraversalStep(entity_id=start_id, depth=0)]
    edges: list[Relationship] = []
    queue: deque[tuple[str, int]] = deque([(start_id, 0)])

    while queue:
        node, depth = queue.popleft()
        if depth >= max_depth:
            continue
        for relationship in await neighbors_fn(node, direction, relation_type):
            edges.append(relationship)
            neighbor = _other_endpoint(relationship, node)
            if neighbor in seen:
                continue
            seen.add(neighbor)
            steps.append(TraversalStep(entity_id=neighbor, depth=depth + 1))
            queue.append((neighbor, depth + 1))

    return TraversalResult(steps=steps, relationships=edges)


async def shortest_path(
    source_id: str,
    target_id: str,
    *,
    neighbors_fn: NeighborsFn,
    direction: TraversalDirection = TraversalDirection.OUTBOUND,
    max_depth: int = 6,
    relation_type: RelationType | None = None,
) -> list[Relationship] | None:
    """Return the relationships forming a shortest path, or None if unreachable.

    BFS guarantees the first path found is shortest by hop count.
    """
    if max_depth < 1:
        raise InvalidTraversalError(f"max_depth must be >= 1, got {max_depth}")
    if source_id == target_id:
        return []

    seen: set[str] = {source_id}
    # node -> edge used to first reach it (for path reconstruction).
    came_from: dict[str, Relationship] = {}
    queue: deque[tuple[str, int]] = deque([(source_id, 0)])

    while queue:
        node, depth = queue.popleft()
        if depth >= max_depth:
            continue
        for relationship in await neighbors_fn(node, direction, relation_type):
            neighbor = _other_endpoint(relationship, node)
            if neighbor in seen:
                continue
            seen.add(neighbor)
            came_from[neighbor] = relationship
            if neighbor == target_id:
                return _reconstruct(came_from, source_id, target_id)
            queue.append((neighbor, depth + 1))

    return None


def _reconstruct(
    came_from: dict[str, Relationship], source_id: str, target_id: str
) -> list[Relationship]:
    """Walk `came_from` edges back from target to source, returning them in order."""
    path: list[Relationship] = []
    node = target_id
    while node != source_id:
        edge = came_from[node]
        path.append(edge)
        node = _other_endpoint(edge, node)
    path.reverse()
    return path
