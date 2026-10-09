"""Structural graph algorithms: BFS, shortest paths, DFS, cycles, topological order, components.

Everything here ignores edge evidence and weights (an uncertain edge is still an edge; BFS counts hops).
All algorithms must be ITERATIVE: a 2,000-node path must work under Python's default recursion limit (1000).

Determinism contract (the same input must give the same output, byte for byte, in Python and in the JS port)
------------------------------------------------------------------------------------------------------------
* "Node order" is ``g.nodes`` order. Whenever an algorithm has a choice between nodes, the node with the SMALLER
  ``g.index_of`` wins.
* Neighbours are always visited in ``g.neighbors(n)`` order (node order).
* Query nodes (``source``, ``target``) that are not in the graph raise :class:`MissingNodeError` -- asking
  about a node the graph does not contain is a contract violation, not "unreachable".
* Results are tuples (immutable) except the ``dict`` fields of :class:`BFSResult`.

Cycle witnesses
---------------
A cycle is a tuple ``(v0, v1, ..., vk)`` with ``vk == v0``, ``k >= 1``, and an edge between each consecutive pair
(``v_i -> v_{i+1}`` in a directed graph). ``v0 .. v(k-1)`` are distinct. A self-loop at ``u`` is ``(u, u)``.
In an UNDIRECTED graph a cycle may not reuse an edge, so ``(a, b, a)`` is NOT a cycle (it walks the single edge
a-b twice); the shortest undirected cycles are self-loops and triangles (``k >= 3``).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Hashable

from .model import Graph, GraphError, MissingNodeError


class CycleError(GraphError):
    """Raised by :func:`topological_order`. ``.cycle`` is a witness cycle in the format described above."""

    def __init__(self, cycle: tuple[Hashable, ...]) -> None:
        super().__init__(f"graph has a cycle: {' -> '.join(map(str, cycle))}")
        self.cycle = tuple(cycle)


@dataclass(frozen=True)
class BFSResult:
    """Result of :func:`bfs`.

    * ``source``   the start node.
    * ``distance`` ``{node: hops}`` for every node reachable from ``source`` (the source has 0). Unreachable
                   nodes are ABSENT (not infinity, not None).
    * ``parent``   ``{node: predecessor on a shortest path}`` for every reachable node; ``parent[source]`` is
                   ``None``. The parent is the node that FIRST discovered the node.
    * ``order``    reachable nodes in the order they were dequeued (discovery order).
    """

    source: Hashable
    distance: dict[Hashable, int]
    parent: dict[Hashable, Hashable | None]
    order: tuple[Hashable, ...]


def bfs(g: Graph, source: Hashable) -> BFSResult:
    """Breadth-first search from ``source`` with a FIFO queue.

    Start: enqueue ``source`` with distance 0 and parent ``None``. Repeatedly dequeue the oldest node ``u``
    (append it to ``order``); for each ``v`` in ``g.neighbors(u)`` (node order) that has no distance yet, set
    ``distance[v] = distance[u] + 1``, ``parent[v] = u``, enqueue ``v``. A node's parent is therefore the
    EARLIEST-dequeued node among its shallowest in-neighbours. Self-loops and duplicate edges change nothing.
    Directed graphs follow edge direction; undirected graphs go both ways.
    ``MissingNodeError`` if ``source`` is not a node. An isolated source gives distance ``{source: 0}``.
    """
    raise NotImplementedError


def shortest_path(g: Graph, source: Hashable, target: Hashable) -> tuple[Hashable, ...] | None:
    """A fewest-hops path ``(source, ..., target)`` or ``None`` if ``target`` is unreachable.

    The witness is obtained by following ``bfs(g, source).parent`` from ``target`` back to ``source`` (then
    reversing), which is what makes tie-breaking deterministic: on a diamond ``a->b, a->c, b->d, c->d`` with
    node order ``a, b, c, d`` the answer for ``(a, d)`` is ``(a, b, d)``. ``source == target`` gives
    ``(source,)`` (the empty walk) even if the node has a self-loop. ``MissingNodeError`` if either node is
    absent. Every consecutive pair of the result is an edge of ``g`` and ``len(path) - 1 == distance``.
    """
    raise NotImplementedError


def dfs_preorder(g: Graph, source: Hashable | None = None) -> tuple[Hashable, ...]:
    """Depth-first preorder, defined by this RECURSIVE description (implement it with an explicit stack):

        visit(u): mark u; append u to the output; for v in g.neighbors(u) in order: if v is unmarked: visit(v)

    ``source`` given: the order of ``visit(source)`` (only nodes reachable from it). ``source=None``: call
    ``visit(n)`` for each unmarked ``n`` in node order and concatenate (every node appears exactly once).
    The explicit stack must resume each node's neighbour iteration where it left off (push ``(node, iterator)``);
    pushing all neighbours at once gives a DIFFERENT order and is wrong. ``MissingNodeError`` for a bad source.
    """
    raise NotImplementedError


def dfs_postorder(g: Graph, source: Hashable | None = None) -> tuple[Hashable, ...]:
    """Same traversal as :func:`dfs_preorder`, but a node is appended when ``visit`` of it FINISHES (after all
    its recursive calls). Used by :func:`strongly_connected_components`."""
    raise NotImplementedError


def find_cycle(g: Graph) -> tuple[Hashable, ...] | None:
    """A witness cycle (format in the module docstring) or ``None`` if the graph is acyclic.

    Algorithm (fixed so the witness is deterministic): run the DFS of :func:`dfs_preorder` with ``source=None``
    (roots in node order, neighbours in order), keeping the current recursion stack (the path of nodes being
    visited) and each node's DFS parent. While scanning neighbour ``w`` of the node ``u`` on top of the stack:
    if ``w`` is ON the stack (and, for undirected graphs only, ``w`` is not ``u``'s DFS parent -- a self-loop
    ``w == u`` still counts), the cycle is ``stack[position of w:]`` followed by ``w``; return it immediately.
    The first such back edge in DFS order is the one reported. A node already finished (off the stack) is never a
    back edge. Directed self-loop at ``u``: ``(u, u)``. Undirected graphs have no duplicate edges (they were
    merged), so skipping the DFS parent is exactly right.
    """
    raise NotImplementedError


def topological_order(g: Graph) -> tuple[Hashable, ...]:
    """Kahn's algorithm with a deterministic tie-break; contains every node exactly once.

    Maintain ``indegree`` (self-loops count: a node with a self-loop never becomes ready) and the set of READY
    nodes (indegree 0). Repeatedly remove the ready node with the SMALLEST node-order index (use a heap of
    indices), append it, and decrement the indegree of each of its successors, making those that reach 0 ready.
    If fewer than ``len(g.nodes)`` nodes were emitted the graph has a cycle: raise
    ``CycleError(find_cycle(g))`` (the witness is a real cycle of ``g``).
    An UNDIRECTED graph raises :class:`GraphError` (a topological order needs directions; check this FIRST).
    Example: edges ``c->a, c->b`` with node order ``a, b, c`` gives ``(c, a, b)``.
    The empty graph gives ``()``.
    """
    raise NotImplementedError


def components(g: Graph) -> tuple[tuple[Hashable, ...], ...]:
    """(Weakly) connected components: direction is ignored, so for a directed graph ``a -> b`` joins a and b.

    Canonical output (independent of the algorithm): each component is a tuple of its nodes in node order, and
    the components are sorted by the node-order index of their first node. Isolated nodes are singleton
    components. The empty graph gives ``()``.
    """
    raise NotImplementedError


def strongly_connected_components(g: Graph) -> tuple[tuple[Hashable, ...], ...]:
    """Strongly connected components via KOSARAJU's algorithm (the chosen SCC algorithm):

    1. ``order = dfs_postorder(g)`` (roots in node order).
    2. Walk ``order`` in REVERSE; for each node not yet assigned, collect everything reachable from it in the
       REVERSED graph (``g.reverse()``) that is not yet assigned: that set is one component.

    Output uses the same CANONICAL form as :func:`components` (nodes in node order inside a component,
    components sorted by their first node's index), so the result does not depend on the algorithm. A
    self-loop never merges anything. Two nodes are
    in one component iff each reaches the other. For an UNDIRECTED graph the answer equals ``components(g)``.
    Must be iterative (2,000-node path / cycle).
    """
    raise NotImplementedError
