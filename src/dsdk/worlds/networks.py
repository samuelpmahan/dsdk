"""Graphs of the Lost Lands world, every edge carrying an evidence status, plus "six degrees" path search.

NODE NAMES. Track graphs name their nodes by the track's STRING KEY (``world.tracks[i].key``, e.g. ``"Torque#001"``), in
track-ID order, for ALL tracks, played or not. Strings (not integers) because the downstream code (``dsdk.prob``'s
``model_from_graph``) needs string track names. The DJ graph names nodes by the selector group's label. All graphs are
OPEN WORLD (``closed_world=False``): the corpus is a sample, so the absence of an edge proves nothing.

Everything here is built on ``dsdk.graph``: graphs come from ``Graph.from_edges``, and the six-degrees answer is the
Judgment of ``dsdk.graph.reachable`` with its witness path from ``shortest_path`` / ``candidate_path``. There is no
search code in this module.

Evidence vocabulary (never collapsed -- see :class:`dsdk.core.Status`)
-----------------------------------------------------------------------
* ``KNOWN``         OBSERVED. A transition ``a -> b`` was seen back-to-back in some set; a DJ pair shares a played
                    track or a credited artist.
* ``UNKNOWN``       INFERRED. Two tracks were played in the same set, but NOT (in that order) back-to-back: they
                    are plausibly related, we have no direct evidence of the move.
* ``NOT_OBSERVED``  never used as an edge label here. "Nobody looked" is represented by the ABSENCE of an edge.
* ``INVALID``       a query about a track that is not in the world (see :func:`SixDegrees.query`).

Graphs and the next-track model
-------------------------------
:func:`transition_graph`    directed, weight = how many times ``a -> b`` was observed, evidence KNOWN.
:func:`coselection_graph`   undirected, weight = in how many sets both tracks were played, evidence UNKNOWN.
:func:`dj_graph`            undirected over selector groups, evidence KNOWN.
:func:`next_track_model`    ``dsdk.prob.model_from_graph`` of the transition graph (observed counts only).
:func:`six_degrees_graph`   directed union used for path search: observed transitions (KNOWN) plus both directions of
                            every co-selection (UNKNOWN); KNOWN wins when both exist (the ``Graph`` merge rule).
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from itertools import combinations

from dsdk.core import Judgment, Status
from dsdk.graph import Edge, Graph, candidate_path, known_subgraph, reachable, shortest_path
from dsdk.prob import NextTrackModel, model_from_graph

from .lostlands import LostLands

TRANSITION_LABEL = "transition"
COSELECTION_LABEL = "co-selection"
"""Edge labels of :func:`six_degrees_graph` (a merged edge carries both, sorted and comma-joined by ``Graph``)."""

DJ_MODES = ("tracks", "members")





def transition_graph(world: LostLands) -> Graph:
    """The track transition graph: DIRECTED, nodes = the track KEYS (strings) in track-ID order, all tracks.

    One edge ``a -> b`` per distinct ``(source, target)`` among ``world.transitions`` (named by key); ``weight`` is the
    number of transition rows with that pair (an ``int``, >= 1); ``evidence`` is ``Status.KNOWN``; ``label`` is ``None``;
    ``closed_world=False``. Self-loops (a track followed by itself in a set) are kept. A track that was never played
    is an isolated node. This is the graph ``dsdk.prob.model_from_graph`` reads next-track counts from.
    """
    raise NotImplementedError


def coselection_graph(world: LostLands) -> Graph:
    """The co-selection graph: UNDIRECTED, nodes = track KEYS in track-ID order, all tracks.

    An edge ``{a, b}`` (``a != b``) exists iff some set ``(group, date)`` has both tracks in its selections.
    ``weight`` is the number of DISTINCT sets containing both (an ``int``); ``evidence`` is ``Status.UNKNOWN`` for
    EVERY edge -- sharing a set is inferred association, not an observed move -- even when the two tracks also
    happen to be back-to-back; ``label`` is ``None``; ``closed_world=False``. No self-loops: a track repeated inside
    one set is not co-selected with itself.
    """
    raise NotImplementedError


def dj_graph(world: LostLands, *, by: str = "tracks") -> Graph:
    """The DJ graph: UNDIRECTED, nodes = the selector groups' LABELS (strings) in group-ID order, evidence KNOWN.

    * ``by="tracks"`` (default): groups ``g1 != g2`` are joined iff they played at least one common track (in any
      set, on any date); ``weight`` = number of DISTINCT common tracks.
    * ``by="members"``: groups are joined iff their ``members`` share at least one artist ID; ``weight`` = number of
      common artist IDs. (A ``truncated`` credit lists only some of its DJs, so this graph can miss real overlaps.)

    ``label`` is ``None`` and ``closed_world=False``. Any other ``by`` raises ``ValueError`` naming the value.
    """
    raise NotImplementedError


def next_track_model(world: LostLands, *, alpha: object = 1) -> NextTrackModel:
    """The "what plays after X?" model: ``dsdk.prob.model_from_graph(transition_graph(world), alpha)``.

    Nothing is computed here beyond that call: the vocabulary is all 1,352 track keys in track-ID order, the counts are
    the OBSERVED transitions only (inferred co-selection never enters), and ``alpha`` is the explicit smoothing
    pseudo-count, passed through unchanged (so ``alpha=0`` is the raw maximum-likelihood estimate and the errors of
    ``model_from_graph`` for a bad ``alpha`` propagate). Query it with ``dsdk.prob.next_track_distribution`` /
    ``top_next`` using track KEYS.
    """
    raise NotImplementedError


def six_degrees_graph(world: LostLands) -> Graph:
    """The graph :class:`SixDegrees` searches: DIRECTED, nodes = track KEYS in track-ID order, ``closed_world=False``.

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
    """One step ``source -> target`` of a path (both are track KEYS), with the evidence for it.

    * ``evidence`` is ``Status.KNOWN`` iff the transition ``source -> target`` was observed (``count`` = how many
      transition rows, ``sets`` = the distinct ``(group, date)`` sets they came from); otherwise ``Status.UNKNOWN``
      (``count`` = number of sets containing both tracks, ``sets`` = those sets).
    * a set is ``(group_id, date_index_or_None)``: indices into ``world.groups`` / ``world.dates``.
      ``sets`` is sorted by ``(group, date)`` with ``None`` dates first.
    """

    source: str
    target: str
    evidence: Status
    count: int
    sets: tuple[tuple[int, int | None], ...]


@dataclass(frozen=True)
class Degrees:
    """Answer of :meth:`SixDegrees.query`.

    ``judgment`` is exactly ``dsdk.graph.reachable(six_degrees_graph(world), source, target)`` (a non-string query is the
    same INVALID judgment, built without calling it). ``path`` is the witness path (a tuple of track KEYS, ``(s,)`` when
    ``source == target``) or ``None`` when there is none (INVALID, or no path even counting inferred edges). ``hops``
    has ``len(path) - 1`` entries (``()`` when ``path`` is ``None`` or has one node).
    """

    source: object
    target: object
    judgment: Judgment
    path: tuple[str, ...] | None
    hops: tuple[Hop, ...]


class SixDegrees:
    """Shortest transition paths between tracks, with evidence. Build once, query many times.

    ``SixDegrees(world)`` builds ``self.graph = six_degrees_graph(world)`` and
    ``self.known = dsdk.graph.known_subgraph(self.graph)`` once (about half a second for the real world), plus the
    per-step evidence tables (how often and in which sets each transition was seen, which sets each track was in).
    Searching is done by ``dsdk.graph``, not here.
    """

    def __init__(self, world: LostLands) -> None:
        raise NotImplementedError

    def hop(self, source: str, target: str) -> Hop:
        """The :class:`Hop` for the edge ``source -> target`` of ``self.graph``.

        ``ValueError`` (message ``f"no edge {source} -> {target}"``) if the graph has no such edge, including when
        either key is not a track. The evidence status is the graph edge's own (``self.graph.get_edge``).
        """
        raise NotImplementedError

    def query(self, source: object, target: object) -> Degrees:
        """Is ``target`` reachable from ``source``, and by which path?

        1. ``source`` or ``target`` is not a track key (not a ``str``, or a ``str`` that names no track):
           ``Judgment(Status.INVALID, None, f"node {x!r} is not in the graph")`` naming ``source`` if both are bad;
           ``path=None``, ``hops=()``. Never raises (unhashable arguments included). This is the same Judgment
           ``dsdk.graph.reachable`` gives for a missing node.
        2. Otherwise ``judgment = dsdk.graph.reachable(self.graph, source, target)`` (a KNOWN judgment means every
           step was observed, UNKNOWN means an inferred step or no path at all).
        3. The witness: KNOWN -> ``dsdk.graph.shortest_path(self.known, source, target)``; UNKNOWN ->
           ``dsdk.graph.candidate_path(self.graph, source, target)`` (``None`` when no path exists, the open-world
           case); INVALID -> ``None``.
        ``hops`` is ``tuple(self.hop(u, v) for u, v in zip(path, path[1:]))``. ``Degrees.source``/``target`` echo the
        arguments unchanged.
        """
        raise NotImplementedError


def six_degrees(world: LostLands, source: object, target: object) -> Degrees:
    """One-shot convenience: ``SixDegrees(world).query(source, target)``. Rebuilds the index every call, so use a
    :class:`SixDegrees` object when asking more than one question."""
    raise NotImplementedError
