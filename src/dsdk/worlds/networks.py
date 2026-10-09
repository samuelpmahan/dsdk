"""Graphs of the Lost Lands world, every edge carrying an evidence status, plus "six degrees" path search.

Nodes of the track graphs are TRACK IDs (``0 .. len(world.tracks) - 1``, all of them, in id order, played or not).
Nodes of the DJ graph are SELECTOR-GROUP IDs. All of these graphs are OPEN WORLD (``closed_world=False``): the corpus
is a sample, so the absence of an edge proves nothing.

Evidence vocabulary (never collapsed -- see :class:`dsdk.core.Status`)
-----------------------------------------------------------------------
* ``KNOWN``         OBSERVED. A transition ``a -> b`` was seen back-to-back in some set; a DJ pair shares a played
                    track or a credited artist.
* ``UNKNOWN``       INFERRED. Two tracks were played in the same set, but NOT (in that order) back-to-back: they
                    are plausibly related, we have no direct evidence of the move.
* ``NOT_OBSERVED``  never used as an edge label here. "Nobody looked" is represented by the ABSENCE of an edge.
* ``INVALID``       a query about a track that is not in the world (see :func:`SixDegrees.query`).

The four graphs
---------------
:func:`transition_graph`    directed, weight = how many times ``a -> b`` was observed, evidence KNOWN.
:func:`coselection_graph`   undirected, weight = in how many sets both tracks were played, evidence UNKNOWN.
:func:`dj_graph`            undirected over selector groups, evidence KNOWN.
:func:`six_degrees_graph`   directed union used for path search: observed transitions (KNOWN) plus both directions of
                            every co-selection (UNKNOWN); KNOWN wins when both exist (the ``Graph`` merge rule).
"""
from __future__ import annotations

import heapq
from collections import Counter, deque
from dataclasses import dataclass
from itertools import combinations

from dsdk.core import Judgment, Status
from dsdk.graph import Edge, Graph, known_subgraph

from .lostlands import LostLands

TRANSITION_LABEL = "transition"
COSELECTION_LABEL = "co-selection"
"""Edge labels of :func:`six_degrees_graph` (a merged edge carries both, sorted and comma-joined by ``Graph``)."""

DJ_MODES = ("tracks", "members")




def transition_graph(world: LostLands) -> Graph:
    """The track transition graph: DIRECTED, nodes ``range(len(world.tracks))``.

    One edge ``a -> b`` per distinct ``(source, target)`` among ``world.transitions``; ``weight`` is the number of
    transition rows with that pair (an ``int``, >= 1); ``evidence`` is ``Status.KNOWN``; ``label`` is ``None``;
    ``closed_world=False``. Self-loops (a track followed by itself in a set) are kept. A track that was never played
    is an isolated node.
    """
    raise NotImplementedError


def coselection_graph(world: LostLands) -> Graph:
    """The co-selection graph: UNDIRECTED, nodes ``range(len(world.tracks))``.

    An edge ``{a, b}`` (``a != b``) exists iff some set ``(group, date)`` has both tracks in its selections.
    ``weight`` is the number of DISTINCT sets containing both (an ``int``); ``evidence`` is ``Status.UNKNOWN`` for
    EVERY edge -- sharing a set is inferred association, not an observed move -- even when the two tracks also
    happen to be back-to-back; ``label`` is ``None``; ``closed_world=False``. No self-loops: a track repeated inside
    one set is not co-selected with itself.
    """
    raise NotImplementedError


def dj_graph(world: LostLands, *, by: str = "tracks") -> Graph:
    """The DJ graph: UNDIRECTED, nodes ``range(len(world.groups))`` (selector-group IDs), evidence KNOWN.

    * ``by="tracks"`` (default): groups ``g1 != g2`` are joined iff they played at least one common track (in any
      set, on any date); ``weight`` = number of DISTINCT common tracks.
    * ``by="members"``: groups are joined iff their ``members`` share at least one artist ID; ``weight`` = number of
      common artist IDs. (A ``truncated`` credit lists only some of its DJs, so this graph can miss real overlaps.)

    ``label`` is ``None`` and ``closed_world=False``. Any other ``by`` raises ``ValueError`` naming the value.
    """
    raise NotImplementedError


def six_degrees_graph(world: LostLands) -> Graph:
    """The graph :class:`SixDegrees` searches: DIRECTED, nodes ``range(len(world.tracks))``, ``closed_world=False``.

    Edges, before merging (``weight=None`` on all, because the two sources count different things):

    * for every distinct observed transition ``a -> b``: ``Edge(a, b, None, Status.KNOWN, TRANSITION_LABEL)``;
    * for every co-selected pair ``a != b``: BOTH ``Edge(a, b, None, Status.UNKNOWN, COSELECTION_LABEL)`` and
      ``Edge(b, a, ...)`` with the same fields.

    Build it with ``Graph.from_edges`` so duplicates merge by its rule: the KNOWN edge wins, and the labels join
    sorted with a comma (a KNOWN edge between co-selected tracks is labelled ``"co-selection,transition"``; a KNOWN
    self-loop is ``"transition"``; an inferred-only edge is ``"co-selection"``).
    """
    raise NotImplementedError



@dataclass(frozen=True)
class Hop:
    """One step ``source -> target`` of a path, with the evidence for it.

    * ``evidence`` is ``Status.KNOWN`` iff the transition ``source -> target`` was observed (``count`` = how many
      transition rows, ``sets`` = the distinct ``(group, date)`` sets they came from); otherwise ``Status.UNKNOWN``
      (``count`` = number of sets containing both tracks, ``sets`` = those sets).
    * ``sets`` is sorted by ``(group, date)`` with ``None`` dates first.
    """

    source: int
    target: int
    evidence: Status
    count: int
    sets: tuple[tuple[int, int | None], ...]


@dataclass(frozen=True)
class Degrees:
    """Answer of :meth:`SixDegrees.query`.

    ``judgment`` is exactly what ``dsdk.graph.reachable(six_degrees_graph(world), source, target)`` returns.
    ``path`` is the witness path (a tuple of track IDs, ``(s,)`` when ``source == target``) or ``None`` when there is
    none (INVALID, or no path even counting inferred edges). ``hops`` has ``len(path) - 1`` entries (``()`` when
    ``path`` is ``None`` or has one node).
    """

    source: object
    target: object
    judgment: Judgment
    path: tuple[int, ...] | None
    hops: tuple[Hop, ...]


class SixDegrees:
    """Shortest transition paths between tracks, with evidence. Build once, query many times.

    ``SixDegrees(world)`` builds ``self.graph = six_degrees_graph(world)`` and
    ``self.known = dsdk.graph.known_subgraph(self.graph)`` once (about a second for the real world), plus private
    indexes so a query does not rescan the edge list. ``dsdk.graph``'s own ``reachable`` is exact but costs
    O(edges) per neighbour lookup, which is far too slow on 100,000 inferred edges; this class implements the SAME
    answer over adjacency lists.
    """

    def __init__(self, world: LostLands) -> None:
        raise NotImplementedError

    def hop(self, source: int, target: int) -> Hop:
        """The :class:`Hop` for the edge ``source -> target`` of ``self.graph``.

        ``ValueError`` (message ``f"no edge {source} -> {target}"``) if the graph has no such edge, including when
        either ID is not a track.
        """
        raise NotImplementedError

    def query(self, source: object, target: object) -> Degrees:
        """Is ``target`` reachable from ``source``, and by which path? Decision table, checked in this order:

        1. ``source`` or ``target`` is not a track ID (not an ``int`` -- ``bool`` is NOT an ``int`` here --, or out
           of range): ``Judgment(Status.INVALID, None, f"node {x!r} is not in the graph")`` naming ``source`` if
           both are bad; ``path=None``, ``hops=()``. Never raises.
        2. A path over KNOWN edges only (breadth-first from ``source`` over ``self.known``; neighbours in ascending
           ID order; a node's parent is its FIRST discoverer; ``source == target`` is the one-node path):
           ``Judgment(Status.KNOWN, True, "known path: a -> b -> c")`` (IDs rendered with ``str``). This is the
           ``dsdk.graph.shortest_path`` of the known subgraph, tie-breaks included -- and it wins even when a
           shorter path exists that uses inferred edges.
        3. Otherwise the best path over ALL edges, exactly ``dsdk.graph.candidate_path``'s rule (minimise the
           number of inferred edges, then hops, then the ID sequence lexicographically; Dijkstra over states
           ``(inferred, hops, path)``): ``Judgment(Status.UNKNOWN, None, "uncertain edges on best candidate
           path: u->v (unknown), ...")`` listing only the non-KNOWN edges in path order, each as
           ``f"{u}->{v} ({evidence.value})"``.
        4. No path at all (the graph is open world): ``Judgment(Status.UNKNOWN, None, "open world: no path found,
           but absence of an edge is not proof of impossibility")``; ``path=None``.

        ``hops`` is ``tuple(self.hop(u, v) for u, v in zip(path, path[1:]))``. ``Degrees.source``/``target`` echo the
        arguments unchanged.
        """
        raise NotImplementedError


def six_degrees(world: LostLands, source: object, target: object) -> Degrees:
    """One-shot convenience: ``SixDegrees(world).query(source, target)``. Rebuilds the index every call, so use a
    :class:`SixDegrees` object when asking more than one question."""
    raise NotImplementedError
