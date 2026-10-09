"""Next-track model: ``P(next | track)`` with explicit smoothing (track A3, the Lost Lands hook).

Built for Manager W's instruments: it takes either raw track sequences or a ``dsdk.graph`` transition graph (edge weight = how
many times ``a`` was followed by ``b``; evidence ``KNOWN`` = observed back-to-back play, ``UNKNOWN`` = inferred, e.g. same-set
co-selection) and answers, exactly and by sampling, "what plays after X?".

Model. Vocabulary ``V`` = the tracks (canonical order, see below). Counts ``c(x, y)`` = times ``y`` directly followed ``x``.
Additive (Laplace/Lidstone) smoothing with pseudo-count ``alpha >= 0``::

    P(y | x) = (c(x, y) + alpha) / (sum_z c(x, z) + alpha * |V|)          for every y in V

``alpha`` is EXPLICIT (no default hidden in the maths; the constructors default it to 1). ``alpha = 0`` is the raw
maximum-likelihood estimate: unseen transitions have probability exactly 0 and a track that was never followed by anything has NO
distribution (UNKNOWN), not an invented uniform one.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from fractions import Fraction
from typing import Iterable, Sequence

from dsdk.core import Judgment, Status
from dsdk.graph import Graph

from .exact import to_weight
from .sampling import Comparison, inverse_cdf_draws, make_comparison, make_estimate


@dataclass(frozen=True)
class NextTrackModel:
    """Counts plus smoothing. Build with :func:`fit_next_track` or :func:`model_from_graph`.

    * ``tracks``  the vocabulary: a tuple of distinct non-empty ``str`` in CANONICAL ORDER (the order every distribution uses).
    * ``counts``  ``{(x, y): n}`` with ``n`` an int >= 1; only pairs that were observed appear (read-only).
    * ``alpha``   the smoothing pseudo-count, a ``Fraction`` >= 0.
    """

    tracks: tuple[str, ...]
    counts: dict[tuple[str, str], int]
    alpha: Fraction

    def outgoing(self, track: str) -> int:
        """Total observed transitions out of ``track`` (``sum_z c(track, z)``); 0 if none. ``KeyError`` is NOT raised for a
        track outside the vocabulary: it simply has 0."""
        raise NotImplementedError


def fit_next_track(sequences: Iterable[Sequence[str]], alpha: object = 1, vocabulary: Iterable[str] | None = None) -> NextTrackModel:
    """Count consecutive pairs inside each sequence (a pair never spans two sequences).

    * ``sequences``   an iterable of sequences (list/tuple) of ``str`` track ids. A bare ``str`` as a sequence is a ``TypeError``
                      (it would be read as characters); a non-str track id is a ``TypeError``; an empty id is a ``ValueError``.
    * ``alpha``       converted with ``to_weight`` (int, Fraction or float; so ``0.5`` is exactly 1/2).
    * ``vocabulary``  optional extra tracks that exist but were never seen (they get smoothed mass); same element rules.
    Canonical track order: ``sorted(set(all tracks seen) | set(vocabulary))``. A sequence of length 0 or 1 adds no pair
    but its track (if any) is in the vocabulary. A repeat ``a, a`` counts as the pair ``(a, a)``.
    """
    raise NotImplementedError


def model_from_graph(g: Graph, alpha: object = 1, include_uncertain: bool = False) -> NextTrackModel:
    """Read the counts off a transition graph. ``g`` must be a directed ``Graph`` (``TypeError`` / ``ValueError`` for undirected)
    whose nodes are non-empty ``str`` (``TypeError`` / ``ValueError``).

    Canonical track order = ``g.nodes`` order (the graph's own deterministic order, NOT re-sorted), so W controls the order.
    Each edge ``x -> y`` contributes ``count = edge.weight`` (``None`` means 1) but only if its evidence is ``Status.KNOWN``, unless
    ``include_uncertain`` is true, in which case UNKNOWN and NOT_OBSERVED edges count too. Self-loops count. Weight rules: a ``bool`` is
    a ``TypeError``; any other weight must be a positive whole number, else ``ValueError`` (``2.5``, ``0`` and ``-1`` are rejected;
    a float with a whole value such as ``3.0`` is accepted as 3). ``alpha`` as in :func:`fit_next_track`.
    """
    raise NotImplementedError


def _row(model: NextTrackModel, track: str) -> Judgment | list[Fraction]:
    """Shared by the public functions: the smoothed probabilities of ``track``'s successors in canonical order, or the Judgment
    explaining why there is none."""
    raise NotImplementedError


def next_track_distribution(model: NextTrackModel, track: str) -> Judgment:
    """Exact ``P(. | track)`` over the whole vocabulary.

    * ``NOT_OBSERVED``  ``track`` is not in ``model.tracks`` (the model has never seen it; smoothing does not invent it).
    * ``UNKNOWN``       the denominator ``outgoing(track) + alpha * |V|`` is 0 (alpha = 0 and nothing observed after the track).
    * ``KNOWN``         a tuple of ``(track_id, Fraction)`` for EVERY vocabulary track in canonical order, summing to exactly 1.
                        With alpha = 0 the unseen successors appear with ``Fraction(0)``.
    ``TypeError`` for a non-model or a non-str track.
    """
    raise NotImplementedError


def top_next(model: NextTrackModel, track: str, k: int) -> Judgment:
    """The ``k`` most likely successors: ``KNOWN`` with a tuple of at most ``k`` ``(track_id, Fraction)`` sorted by probability
    DESCENDING, ties broken by canonical order; zero-probability entries are dropped (so alpha = 0 may give fewer than ``k``).
    Non-KNOWN distributions are returned as they are. ``k`` must be an int >= 1 (bool rejected; ``TypeError``/``ValueError``)."""
    raise NotImplementedError


def sample_next_tracks(model: NextTrackModel, track: str, n: int, seed: int) -> Judgment:
    """``n`` successor tracks drawn from ``P(. | track)`` with :func:`dsdk.prob.sampling.inverse_cdf_draws` over the canonical
    vocabulary order. ``KNOWN`` with a tuple of ``str`` (length ``n``); NOT_OBSERVED/UNKNOWN exactly as
    :func:`next_track_distribution`. Argument checks (``n`` int >= 0, ``seed`` int) raise as in ``inverse_cdf_draws``."""
    raise NotImplementedError


def compare_next_track(model: NextTrackModel, track: str, target: str, n: int, seed: int) -> Judgment:
    """Exact ``P(target | track)`` next to a Monte Carlo estimate from ``n`` draws (:func:`sample_next_tracks`, same ``seed``):
    ``KNOWN`` with a :class:`dsdk.prob.sampling.Comparison` (``successes`` = draws equal to ``target``, ``trials = drawn = n``).
    NOT_OBSERVED if ``track`` OR ``target`` is outside the vocabulary; UNKNOWN as in ``next_track_distribution``; UNKNOWN also if
    ``n == 0`` (no trials, so no estimate)."""
    raise NotImplementedError


def held_out_log_loss(model: NextTrackModel, pairs: Iterable[tuple[str, str]]) -> Judgment:
    """Mean negative log-likelihood (natural log, nats per transition) of held-out ``(x, y)`` pairs under the model.

    * ``pairs`` empty -> ``UNKNOWN`` ("no pairs").
    * any ``x`` or ``y`` outside the vocabulary -> ``NOT_OBSERVED`` (reason names it); the model cannot score what it has never seen.
    * some pair has probability 0 (needs alpha = 0) or its ``x`` has no distribution -> ``INVALID`` (reason: the model
      assigned probability zero / has no distribution, so the loss is infinite). NOT a made-up large number.
    * otherwise ``KNOWN`` float ``-sum(log(float(P(y|x)))) / len(pairs)``.
    Elements must be 2-tuples of ``str`` (``TypeError``).
    """
    raise NotImplementedError
