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
        raise NotImplementedError

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
        raise NotImplementedError

    def has_node(self, node: Hashable) -> bool:
        """True iff ``node`` is one of ``nodes``."""
        raise NotImplementedError

    def index_of(self, node: Hashable) -> int:
        """Position of ``node`` in ``nodes``. :class:`MissingNodeError` if absent."""
        raise NotImplementedError

    def get_edge(self, u: Hashable, v: Hashable) -> Edge | None:
        """The stored edge between ``u`` and ``v``, or ``None``.

        Directed: the edge ``u -> v`` only. Undirected: the edge on the unordered pair, whichever way it is
        stored. Never raises: if ``u`` or ``v`` is not a node the answer is ``None``.
        """
        raise NotImplementedError

    def has_edge(self, u: Hashable, v: Hashable) -> bool:
        """``get_edge(u, v) is not None``."""
        raise NotImplementedError

    def neighbors(self, node: Hashable) -> tuple[Hashable, ...]:
        """Successors of ``node`` (directed) or all neighbours (undirected), each ONCE, in node order.

        A self-loop makes ``node`` its own neighbour. :class:`MissingNodeError` if ``node`` is absent.
        """
        raise NotImplementedError

    def predecessors(self, node: Hashable) -> tuple[Hashable, ...]:
        """Directed: nodes ``p`` with an edge ``p -> node``, in node order. Undirected: same as ``neighbors``.

        :class:`MissingNodeError` if ``node`` is absent.
        """
        raise NotImplementedError

    def adjacency(self) -> dict[Hashable, tuple[Hashable, ...]]:
        """Adjacency-list view: ``{node: neighbors(node)}`` for EVERY node (isolated nodes map to ``()``),
        with keys in node order."""
        raise NotImplementedError

    def adjacency_matrix(self) -> tuple[tuple[int, ...], ...]:
        """n x n 0/1 matrix in node order: entry ``[i][j]`` is 1 iff ``nodes[j]`` is in ``neighbors(nodes[i])``.

        Undirected graphs give a symmetric matrix. A self-loop gives a 1 on the diagonal (undirected: 1, not 2).
        The empty graph gives ``()``.
        """
        raise NotImplementedError

    def weight_matrix(self) -> tuple[tuple[float | None, ...], ...]:
        """n x n matrix in node order: entry ``[i][j]`` is the weight of the edge ``nodes[i] -> nodes[j]``
        (``1`` if that edge exists but is unweighted) and ``None`` where there is no edge. ``None`` (not 0) marks
        absence because 0 is a legal weight. Undirected: symmetric."""
        raise NotImplementedError

    def reverse(self) -> "Graph":
        """Directed: every edge flipped (``a -> b`` becomes ``b -> a``; weight, evidence and label kept), same
        nodes, same flags, normalised per the invariants. Undirected: an equal graph."""
        raise NotImplementedError

    def relabel(self, mapping: Mapping[Hashable, Hashable]) -> "Graph":
        """Rename nodes. ``mapping`` must have a key for EVERY node (else :class:`MissingNodeError`) and must
        be injective on the nodes (two nodes mapped to one name: :class:`GraphError`). The node at position ``i``
        keeps position ``i`` under its new name, so ``relabel`` is an isomorphism that preserves node order and
        therefore every deterministic tie-break. Edges keep weight, evidence and label; the result satisfies the
        invariants (for undirected graphs the stored orientation is unchanged, as positions are unchanged).
        """
        raise NotImplementedError
