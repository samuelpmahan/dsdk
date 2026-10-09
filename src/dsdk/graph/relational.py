"""The same question asked two ways: "which pairs (a, c) are two hops apart?"

Relational view: edges are rows ``{"source": a, "target": b}`` in a table; "two hops" is a SELF-JOIN,

    SELECT e1.source, e2.target FROM edges e1 JOIN edges e2 ON e1.target = e2.source

Graph view: build a :class:`Graph` and COMPOSE adjacency (the square of the adjacency relation).

Both define a *walk of length exactly 2*: ``a -> b -> c`` for some middle node ``b``. Walks need not be simple:
``a == c`` is allowed (``a -> b -> a``), and a self-loop ``a -> a`` gives ``a -> a -> c`` for every edge ``a -> c``.

Why the answers agree as SETS but not as COUNTS
-----------------------------------------------
A table is a BAG (multiset): the same row may appear twice. A join multiplies: if ``a -> b`` appears ``m1`` times
and ``b -> c`` appears ``m2`` times, the join emits ``(a, c)`` ``m1 * m2`` times through ``b`` -- one output row per
PAIR OF ROWS. ``Graph.from_records`` MERGES duplicate rows into one edge (``dsdk.graph.model``), so the graph view
counts one per distinct middle node ``b``. Projecting the join with ``DISTINCT`` (taking ``set(...)``) throws
the multiplicities away, and then both views contain exactly the pairs that have at least one middle node. So:
pair SETS always agree; pair COUNTS agree only when no row is duplicated (every multiplicity is 1).

All functions here are about DIRECTED records (rows are ordered pairs); for an undirected graph the graph-side
functions use ``neighbors`` as given, which is symmetric.
"""
from __future__ import annotations

from typing import Any, Hashable, Mapping, Sequence

from .model import Graph, GraphError

Pair = tuple[Hashable, Hashable]


def two_hop_join(
    records: Sequence[Mapping[str, Any]], source: str = "source", target: str = "target"
) -> list[Pair]:
    """The self-join as a LIST (bag), duplicates preserved.

    For ``r1`` in ``records`` (outer loop, in order) and ``r2`` in ``records`` (inner loop, in order): if
    ``r1[target] == r2[source]`` append ``(r1[source], r2[target])``. Exactly one output row per matching pair of
    rows, so ``records = [a->b, a->b, b->c]`` gives ``[(a, c), (a, c)]``. A record missing ``source`` or ``target``
    raises :class:`GraphError`. Empty input gives ``[]``.
    """
    pairs: list[Pair] = []
    keyed: list[tuple[Hashable, Hashable]] = []
    for record in records:
        try:
            keyed.append((record[source], record[target]))
        except KeyError as exc:
            raise GraphError(f"record {record!r} is missing key {exc.args[0]!r}") from exc
    for r1_source, r1_target in keyed:
        for r2_source, r2_target in keyed:
            if r1_target == r2_source:
                pairs.append((r1_source, r2_target))
    return pairs


def two_hop_pairs(
    records: Sequence[Mapping[str, Any]], source: str = "source", target: str = "target"
) -> frozenset[Pair]:
    """``DISTINCT`` of :func:`two_hop_join`: the SET of pairs ``(a, c)`` joined by at least one middle node."""
    return frozenset(two_hop_join(records, source, target))


def two_hop_pairs_graph(g: Graph) -> frozenset[Pair]:
    """The graph version: ``{(a, c) : b in g.neighbors(a), c in g.neighbors(b)}`` (adjacency composition).

    On ``Graph.from_records(records)`` (directed) this equals ``two_hop_pairs(records)`` for every list of
    records, duplicates or not."""
    return frozenset((a, c) for a in g.nodes for b in g.neighbors(a) for c in g.neighbors(b))


def two_hop_counts_graph(g: Graph) -> dict[Pair, int]:
    """``{(a, c): number of DISTINCT middle nodes b}`` for every pair with at least one. This is the nonzero part
    of the square of ``g.adjacency_matrix()``. Differs from ``Counter(two_hop_join(records))`` exactly when some
    record is duplicated."""
    matrix = two_hop_matrix(g)
    nodes = g.nodes
    return {
        (nodes[i], nodes[j]): count
        for i, row in enumerate(matrix)
        for j, count in enumerate(row)
        if count
    }


def two_hop_matrix(g: Graph) -> tuple[tuple[int, ...], ...]:
    """The matrix product ``A @ A`` of ``g.adjacency_matrix()`` with itself, computed with plain loops (rows and
    columns in node order). Entry ``[i][j]`` equals ``two_hop_counts_graph(g).get((nodes[i], nodes[j]), 0)``."""
    a = g.adjacency_matrix()
    n = len(a)
    result: list[list[int]] = [[0] * n for _ in range(n)]
    for i in range(n):
        for k in range(n):
            if a[i][k]:
                for j in range(n):
                    result[i][j] += a[i][k] * a[k][j]
    return tuple(tuple(row) for row in result)
