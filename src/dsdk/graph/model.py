"""Immutable graphs with per-edge evidence status.

A :class:`Graph` is a finite set of nodes (any hashable values) plus edges. It is directed or undirected,
edges may carry a numeric weight, and EVERY edge carries an evidence status taken from
:class:`dsdk.core.Status`. Build graphs ONLY with :meth:`Graph.from_edges` / :meth:`Graph.from_records`;
their output satisfies every invariant below (constructing ``Graph(...)`` directly bypasses validation and is
not part of the contract).

Evidence mapping (the curriculum lesson: "a missing edge is not proof of impossibility")
----------------------------------------------------------------------------------------
Only three Status members may label an edge (anything else is ``ValueError``):

* ``Status.KNOWN``        the edge was OBSERVED. This is the default.
* ``Status.UNKNOWN``      the edge is INFERRED / hypothesised: some evidence exists, but not enough to settle it.
* ``Status.NOT_OBSERVED`` the edge is a CANDIDATE nobody has looked at (no evidence either way).

``UNKNOWN`` and ``NOT_OBSERVED`` are called *uncertain*. Strength order, strongest first:
``KNOWN`` > ``UNKNOWN`` > ``NOT_OBSERVED`` (see :data:`EVIDENCE_RANK`). Structural algorithms in
``dsdk.graph.traverse`` IGNORE evidence (an uncertain edge is still an edge); only ``dsdk.graph.evidence`` reads it.

``Graph.closed_world`` is a flag about the whole graph: True means "the edge list is complete, so a missing edge
really is absent"; False (default, the open world) means missing edges prove nothing.

Invariants of every graph produced by ``from_edges`` / ``from_records``
-----------------------------------------------------------------------
1. ``nodes`` is a tuple of DISTINCT nodes. This order is the *node order* and is the deterministic tie-break
   everywhere in dsdk.graph (smaller position wins). Matrix rows/columns use it.
2. ``edges`` is a tuple of :class:`Edge`, one per distinct (source, target) pair (directed) or per distinct
   unordered pair (undirected): duplicates are MERGED (see below).
3. Every edge endpoint is in ``nodes``.
4. ``edges`` is sorted by ``(index_of(source), index_of(target))``. For an UNDIRECTED graph each stored edge is
   oriented so that ``index_of(source) <= index_of(target)``. Hence the result does not depend on the order in
   which the caller listed the edges.

Construction rules (``from_edges``; ``from_records`` produces edges and then applies the same rules)
-----------------------------------------------------------------------------------------------------
Edge items may be :class:`Edge` objects, ``(u, v)`` tuples, or ``(u, v, weight)`` tuples (anything else:
``TypeError``). Checks run in this order and the first violated one raises:

a. Item shape (``TypeError``). ``weight`` must be ``None`` or an ``int``/``float`` that is not a ``bool``
   (else ``TypeError``) and is finite (``nan``/``inf``: ``ValueError``). ``evidence`` must be a ``Status``
   (``TypeError``) in ``EDGE_STATUSES`` (``ValueError``). ``label`` must be ``None`` or ``str`` (``TypeError``).
b. Node set. ``nodes=None`` (default): the nodes are all endpoints in FIRST-APPEARANCE order (for each edge in the
   order given: its source, then its target). ``nodes=<iterable>``: exactly those nodes, in that order with repeats
   after the first dropped; no other node exists. This is how isolated nodes are declared.
c. Missing endpoint: an edge endpoint that is not in the node set raises :class:`MissingNodeError` (message names the
   node). Declare it in ``nodes=`` if it is meant to exist.
d. Duplicates (same pair; for undirected graphs ``(u, v)`` and ``(v, u)`` are the same pair) are MERGED into one edge:
     * evidence: the STRONGEST wins (a KNOWN observation is not weakened by an extra uncertain claim);
     * weight: all duplicates must have the same weight (``None`` equals only ``None``), else :class:`GraphError`;
     * label: the distinct non-None labels, sorted, joined with ``","``; ``None`` if every label is ``None``.
e. Self-loops ``(u, u)`` are KEPT, as ordinary edges. Directed: ``u`` is its own successor. Undirected: one edge,
   and ``u`` appears ONCE in its own neighbour list.
f. Finally orient (undirected) and sort per invariant 4.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Hashable, Iterable, Mapping

from dsdk.core import Status

EDGE_STATUSES: tuple[Status, ...] = (Status.KNOWN, Status.UNKNOWN, Status.NOT_OBSERVED)
EVIDENCE_RANK: dict[Status, int] = {Status.KNOWN: 0, Status.UNKNOWN: 1, Status.NOT_OBSERVED: 2}


class GraphError(ValueError):
    """Base class of every dsdk.graph contract error that is not a plain TypeError."""


class MissingNodeError(GraphError):
    """A node was referenced that the graph does not contain (edge endpoint, query source/target, ...)."""


@dataclass(frozen=True)
class Edge:
    """One edge. ``weight`` ``None`` means unweighted (treated as 1 by ``weight_matrix``)."""

    source: Hashable
    target: Hashable
    weight: float | None = None
    evidence: Status = Status.KNOWN
    label: str | None = None


@dataclass(frozen=True)
class Graph:
    """Immutable graph. See the module docstring for all invariants and construction rules."""

    nodes: tuple[Hashable, ...]
    edges: tuple[Edge, ...]
    directed: bool = True
    closed_world: bool = False

    @classmethod
    def from_edges(
        cls,
        edges: Iterable[Edge | tuple],
        nodes: Iterable[Hashable] | None = None,
        *,
        directed: bool = True,
        closed_world: bool = False,
    ) -> "Graph":
        """Normalising constructor; implements rules a-f of the module docstring.

        ``edges`` may be a one-shot iterable (consume it once). ``from_edges([])`` is the empty graph.
        """
        edges = list(edges)
        nodes = None if nodes is None else list(nodes)

        normal: list[Edge] = []
        for item in edges:
            if isinstance(item, Edge):
                edge = item
            elif isinstance(item, tuple):
                if len(item) not in (2, 3):
                    raise TypeError(f"edge tuple must have 2 or 3 items, got {item!r}")
                edge = Edge(*item)
            else:
                raise TypeError(f"edge must be an Edge or a tuple, got {item!r}")
            w = edge.weight
            if w is not None:
                if isinstance(w, bool) or not isinstance(w, (int, float)):
                    raise TypeError(f"weight must be None or a number, got {w!r}")
                if not math.isfinite(w):
                    raise ValueError(f"weight must be finite, got {w!r}")
            if not isinstance(edge.evidence, Status):
                raise TypeError(f"evidence must be a Status, got {edge.evidence!r}")
            if edge.evidence not in EDGE_STATUSES:
                raise ValueError(f"evidence {edge.evidence!r} is not allowed on an edge")
            if edge.label is not None and not isinstance(edge.label, str):
                raise TypeError(f"label must be None or str, got {edge.label!r}")
            normal.append(edge)

        index: dict[Hashable, int] = {}
        if nodes is None:
            for edge in normal:
                for node in (edge.source, edge.target):
                    if node not in index:
                        index[node] = len(index)
        else:
            for node in nodes:
                if node not in index:
                    index[node] = len(index)

        for edge in normal:
            for node in (edge.source, edge.target):
                if node not in index:
                    raise MissingNodeError(f"edge endpoint {node!r} is not in the node set")

        groups: dict[tuple[Hashable, Hashable], list[Edge]] = {}
        for edge in normal:
            u, v = edge.source, edge.target
            if not directed and index[u] > index[v]:
                u, v = v, u
            groups.setdefault((u, v), []).append(edge)

        merged: list[Edge] = []
        for (u, v), group in groups.items():
            weight = group[0].weight
            for other in group[1:]:
                if other.weight != weight:
                    raise GraphError(f"conflicting weights for edge {u!r} -> {v!r}: {weight!r} vs {other.weight!r}")
            evidence = min((g.evidence for g in group), key=EVIDENCE_RANK.__getitem__)
            labels = sorted({g.label for g in group if g.label is not None})
            label = ",".join(labels) if labels else None
            merged.append(Edge(u, v, weight, evidence, label))

        merged.sort(key=lambda e: (index[e.source], index[e.target]))
        return cls(tuple(index), tuple(merged), directed, closed_world)

    @classmethod
    def from_records(
        cls,
        records: Iterable[Mapping[str, Any]],
        *,
        source: str = "source",
        target: str = "target",
        weight: str | None = None,
        evidence: str | None = None,
        label: str | None = None,
        nodes: Iterable[Hashable] | None = None,
        directed: bool = True,
        closed_world: bool = False,
    ) -> "Graph":
        """Build a graph from relational rows (a list of dicts), e.g. ``{"source": "a", "target": "b"}``.

        ``source`` / ``target`` are the KEY NAMES of the endpoint columns. ``weight`` / ``evidence`` / ``label``
        are key names of optional columns (``None`` = no such column; then every edge gets the default). A
        record missing a required key (``source``, ``target``, or a named optional column) raises
        :class:`GraphError`. An ``evidence`` cell may be a ``Status`` member or its string value (``"known"``,
        ``"unknown"``, ``"not_observed"``); any other string: ``ValueError``. Extra keys in a record are ignored.
        Then the same rules as :meth:`from_edges` apply (duplicate rows merge: see the module docstring; missing
        endpoints raise ``MissingNodeError`` unless ``nodes`` declares them).
        """
        edges: list[Edge] = []
        for record in records:
            try:
                u = record[source]
                v = record[target]
                w = record[weight] if weight is not None else None
                ev = record[evidence] if evidence is not None else Status.KNOWN
                lab = record[label] if label is not None else None
            except KeyError as exc:
                raise GraphError(f"record {record!r} has no key {exc.args[0]!r}") from exc
            if isinstance(ev, str):
                ev = Status(ev)
            edges.append(Edge(u, v, w, ev, lab))
        return cls.from_edges(edges, nodes, directed=directed, closed_world=closed_world)

    def has_node(self, node: Hashable) -> bool:
        """True iff ``node`` is one of ``nodes``."""
        return node in self._positions()

    def _cached(self, name: str, build):
        """Lazily computed, per-instance cache. A Graph is immutable, so a derived index never goes stale. The cache
        lives in ``__dict__`` (not a dataclass field), so equality, hashing and ``repr`` are unaffected."""
        cache = self.__dict__
        if name not in cache:
            cache[name] = build()
        return cache[name]

    def _positions(self) -> dict[Hashable, int]:
        """Node -> position in ``nodes`` (internal lookup helper; cached, treat as read-only)."""
        return self._cached("_pos", lambda: {node: i for i, node in enumerate(self.nodes)})

    def _edge_index(self) -> dict[tuple[Hashable, Hashable], Edge]:
        """``(source, target)`` -> the stored edge (cached). Undirected edges are stored in one orientation only."""
        return self._cached("_edge_ix", lambda: {(e.source, e.target): e for e in self.edges})

    def _successor_positions(self) -> list[tuple[int, ...]]:
        """For each node position, the sorted positions of its neighbours (directed: successors; undirected: all
        neighbours; a self-loop lists the node once). Cached."""

        def build() -> list[tuple[int, ...]]:
            pos = self._positions()
            found: list[set[int]] = [set() for _ in self.nodes]
            for e in self.edges:
                s, t = pos[e.source], pos[e.target]
                found[s].add(t)
                if not self.directed:
                    found[t].add(s)
            return [tuple(sorted(x)) for x in found]

        return self._cached("_succ_ix", build)

    def _predecessor_positions(self) -> list[tuple[int, ...]]:
        """Directed graphs: for each node position, the sorted positions of its in-neighbours. Cached."""

        def build() -> list[tuple[int, ...]]:
            pos = self._positions()
            found: list[set[int]] = [set() for _ in self.nodes]
            for e in self.edges:
                found[pos[e.target]].add(pos[e.source])
            return [tuple(sorted(x)) for x in found]

        return self._cached("_pred_ix", build)

    def _position_or_raise(self, node: Hashable) -> int:
        """Position of ``node``; :class:`MissingNodeError` if absent (internal helper)."""
        pos = self._positions()
        if node not in pos:
            raise MissingNodeError(f"node {node!r} is not in the graph")
        return pos[node]

    def index_of(self, node: Hashable) -> int:
        """Position of ``node`` in ``nodes``. :class:`MissingNodeError` if absent."""
        return self._position_or_raise(node)

    def get_edge(self, u: Hashable, v: Hashable) -> Edge | None:
        """The stored edge between ``u`` and ``v``, or ``None``.

        Directed: the edge ``u -> v`` only. Undirected: the edge on the unordered pair, whichever way it is
        stored. Never raises: if ``u`` or ``v`` is not a node the answer is ``None``.
        """
        if not (self.has_node(u) and self.has_node(v)):
            return None
        index = self._edge_index()
        edge = index.get((u, v))
        if edge is None and not self.directed:
            edge = index.get((v, u))
        return edge

    def has_edge(self, u: Hashable, v: Hashable) -> bool:
        """``get_edge(u, v) is not None``."""
        return self.get_edge(u, v) is not None

    def neighbors(self, node: Hashable) -> tuple[Hashable, ...]:
        """Successors of ``node`` (directed) or all neighbours (undirected), each ONCE, in node order.

        A self-loop makes ``node`` its own neighbour. :class:`MissingNodeError` if ``node`` is absent.
        """
        me = self._position_or_raise(node)
        return tuple(self.nodes[i] for i in self._successor_positions()[me])

    def predecessors(self, node: Hashable) -> tuple[Hashable, ...]:
        """Directed: nodes ``p`` with an edge ``p -> node``, in node order. Undirected: same as ``neighbors``.

        :class:`MissingNodeError` if ``node`` is absent.
        """
        if not self.directed:
            return self.neighbors(node)
        me = self._position_or_raise(node)
        return tuple(self.nodes[i] for i in self._predecessor_positions()[me])

    def adjacency(self) -> dict[Hashable, tuple[Hashable, ...]]:
        """Adjacency-list view: ``{node: neighbors(node)}`` for EVERY node (isolated nodes map to ``()``),
        with keys in node order."""
        return {node: self.neighbors(node) for node in self.nodes}

    def adjacency_matrix(self) -> tuple[tuple[int, ...], ...]:
        """n x n 0/1 matrix in node order: entry ``[i][j]`` is 1 iff ``nodes[j]`` is in ``neighbors(nodes[i])``.

        Undirected graphs give a symmetric matrix. A self-loop gives a 1 on the diagonal (undirected: 1, not 2).
        The empty graph gives ``()``.
        """
        pos = self._positions()
        n = len(self.nodes)
        mat = [[0] * n for _ in range(n)]
        for edge in self.edges:
            i, j = pos[edge.source], pos[edge.target]
            mat[i][j] = 1
            if not self.directed:
                mat[j][i] = 1
        return tuple(tuple(row) for row in mat)

    def weight_matrix(self) -> tuple[tuple[float | None, ...], ...]:
        """n x n matrix in node order: entry ``[i][j]`` is the weight of the edge ``nodes[i] -> nodes[j]``
        (``1`` if that edge exists but is unweighted) and ``None`` where there is no edge. ``None`` (not 0) marks
        absence because 0 is a legal weight. Undirected: symmetric."""
        pos = self._positions()
        n = len(self.nodes)
        mat: list[list[float | None]] = [[None] * n for _ in range(n)]
        for edge in self.edges:
            i, j = pos[edge.source], pos[edge.target]
            w = 1 if edge.weight is None else edge.weight
            mat[i][j] = w
            if not self.directed:
                mat[j][i] = w
        return tuple(tuple(row) for row in mat)

    def reverse(self) -> "Graph":
        """Directed: every edge flipped (``a -> b`` becomes ``b -> a``; weight, evidence and label kept), same
        nodes, same flags, normalised per the invariants. Undirected: an equal graph."""
        if not self.directed:
            return self
        flipped = [Edge(e.target, e.source, e.weight, e.evidence, e.label) for e in self.edges]
        return type(self).from_edges(flipped, self.nodes, directed=True, closed_world=self.closed_world)

    def relabel(self, mapping: Mapping[Hashable, Hashable]) -> "Graph":
        """Rename nodes. ``mapping`` must have a key for EVERY node (else :class:`MissingNodeError`) and must
        be injective on the nodes (two nodes mapped to one name: :class:`GraphError`). The node at position ``i``
        keeps position ``i`` under its new name, so ``relabel`` is an isomorphism that preserves node order and
        therefore every deterministic tie-break. Edges keep weight, evidence and label; the result satisfies the
        invariants (for undirected graphs the stored orientation is unchanged, as positions are unchanged).
        """
        for node in self.nodes:
            if node not in mapping:
                raise MissingNodeError(f"relabel mapping has no key for node {node!r}")
        new_nodes = tuple(mapping[node] for node in self.nodes)
        if len(set(new_nodes)) != len(new_nodes):
            raise GraphError("relabel mapping must be injective on the nodes")
        new_edges = tuple(
            Edge(mapping[e.source], mapping[e.target], e.weight, e.evidence, e.label) for e in self.edges
        )
        return type(self)(new_nodes, new_edges, self.directed, self.closed_world)
