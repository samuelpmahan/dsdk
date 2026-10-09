"""Reachability with epistemic status: "a missing edge is not proof of impossibility".

``reachable`` answers "is there a path from s to t?" with a :class:`dsdk.core.Judgment`, not a bool, because a
bool cannot say "I do not know". Edge evidence follows the mapping in ``dsdk.graph.model``: KNOWN = observed;
UNKNOWN / NOT_OBSERVED = uncertain (inferred / candidate).

Decision table for ``reachable(g, source, target)`` (checked in this order)
---------------------------------------------------------------------------
1. ``source`` or ``target`` not a node of ``g``  ->  ``Judgment(Status.INVALID, reason=...)`` (a Judgment, NOT an
   exception: the question was ill-posed). The reason names the missing node with ``repr``:
   ``"node 'x' is not in the graph"`` (if both are missing, name the source).
2. A path exists using ONLY KNOWN edges (``source == target`` always counts: the empty path)
   ->  ``Judgment(Status.KNOWN, True, "known path: a -> b -> c")``. The path is ``shortest_path`` of
   ``known_subgraph(g)``; nodes are rendered with ``str`` and joined by ``" -> "`` (also for undirected graphs).
3. No known path, but a path exists when uncertain edges are counted
   ->  ``Judgment(Status.UNKNOWN, None, reason)`` with reason
   ``"uncertain edges on best candidate path: a->b (unknown), c->d (not_observed)"``: the uncertain edges of
   :func:`candidate_path`, in path order, each as ``f"{u}->{v} ({edge.evidence.value})"`` where ``u->v`` is the
   direction in which the path walks it, joined by ``", "``.
4. No path at all, even counting every edge, and ``g.closed_world`` is True
   ->  ``Judgment(Status.KNOWN, False, "closed world: no path from a to b even counting uncertain edges")``
   (``a`` / ``b`` are ``str(source)`` / ``str(target)``).
5. No path at all and the world is open
   ->  ``Judgment(Status.UNKNOWN, None, "open world: no path found, but absence of an edge is not proof of impossibility")``.

So KNOWN False is possible ONLY in a closed world, and KNOWN True never needs the world flag.
"""
from __future__ import annotations

import heapq
from typing import Hashable

from dsdk.core import Judgment, Status

from .model import Graph
from .traverse import shortest_path

UNCERTAIN: tuple[Status, ...] = (Status.UNKNOWN, Status.NOT_OBSERVED)
"""The edge statuses that do not count as observed."""


def known_subgraph(g: Graph) -> Graph:
    """A graph with the same ``nodes`` (same order, so isolated nodes survive), the same ``directed`` and
    ``closed_world`` flags, and only the edges whose evidence is ``Status.KNOWN``."""
    return g._cached(
        "_known_subgraph",
        lambda: Graph.from_edges(
            [e for e in g.edges if e.evidence is Status.KNOWN],
            g.nodes,
            directed=g.directed,
            closed_world=g.closed_world,
        ),
    )


def candidate_path(g: Graph, source: Hashable, target: Hashable) -> tuple[Hashable, ...] | None:
    """The best path from ``source`` to ``target`` when ALL edges (of any evidence) may be used, or ``None``.

    "Best" is the path minimising, in this order:
      1. the number of uncertain (non-KNOWN) edges on it,
      2. its number of edges (hops),
      3. its sequence of node-order indices, compared lexicographically (smaller first).
    ``source == target`` gives ``(source,)``. ``MissingNodeError`` if either node is absent.
    Because the key is a total order on paths the answer is unique. Suggested algorithm: Dijkstra over states
    ``(uncertain_count, hops, index_path)``: push ``(0, 0, (index_of(source),))``; pop the smallest; the first
    pop that ends at ``target`` is the answer; a node already settled is skipped; extending by one edge adds 1 to
    hops, adds 1 to the uncertain count iff the edge is not KNOWN, and appends the neighbour's index. (Extending
    two equal-length paths cannot reorder them, so this is exact.)
    """
    start = g.index_of(source)
    goal = g.index_of(target)
    heap: list[tuple[int, int, tuple[int, ...]]] = [(0, 0, (start,))]
    settled: set[int] = set()
    while heap:
        uncertain, hops, path = heapq.heappop(heap)
        last = path[-1]
        if last in settled:
            continue
        settled.add(last)
        if last == goal:
            return tuple(g.nodes[i] for i in path)
        u = g.nodes[last]
        for v in g.neighbors(u):
            j = g.index_of(v)
            if j in settled:
                continue
            edge = g.get_edge(u, v)
            extra = 1 if edge is not None and edge.evidence is not Status.KNOWN else 0
            heapq.heappush(heap, (uncertain + extra, hops + 1, path + (j,)))
    return None


def reachable(g: Graph, source: Hashable, target: Hashable) -> Judgment:
    """Is ``target`` reachable from ``source``? See the decision table in the module docstring (exact reason
    strings included). Directed graphs follow edge direction. Must not raise for any pair of query nodes."""
    for node in (source, target):
        if not g.has_node(node):
            return Judgment(Status.INVALID, None, f"node {node!r} is not in the graph")

    known_path = shortest_path(known_subgraph(g), source, target)
    if known_path is not None:
        return Judgment(Status.KNOWN, True, "known path: " + " -> ".join(str(n) for n in known_path))

    best = candidate_path(g, source, target)
    if best is not None:
        parts = []
        for u, v in zip(best, best[1:]):
            edge = g.get_edge(u, v)
            if edge is not None and edge.evidence is not Status.KNOWN:
                parts.append(f"{u}->{v} ({edge.evidence.value})")
        return Judgment(Status.UNKNOWN, None, "uncertain edges on best candidate path: " + ", ".join(parts))

    if g.closed_world:
        return Judgment(Status.KNOWN, False,
                        f"closed world: no path from {source} to {target} even counting uncertain edges")
    return Judgment(Status.UNKNOWN, None,
                    "open world: no path found, but absence of an edge is not proof of impossibility")
