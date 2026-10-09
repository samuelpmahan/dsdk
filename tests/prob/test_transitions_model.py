"""Contract tests: the next-track model P(next | track) with explicit smoothing (the Lost Lands hook).

Toy data only (hand-checkable). Sequences: [a b c], [a b d], [b c], [a]  ->  counts (a,b)=2, (b,c)=2, (b,d)=1 and vocabulary a b c d.
  alpha = 1:  P(.|a) = b 1/2, a/c/d 1/6 each;  P(.|b) = c 3/7, d 2/7, a 1/7, b 1/7;  P(.|c) = uniform 1/4 (never followed by anything)
  alpha = 0:  P(.|b) = c 2/3, d 1/3 (zeros kept);  P(.|c) has NO distribution (UNKNOWN), P(.|zzz) is NOT_OBSERVED
"""
from fractions import Fraction

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from dsdk.core import Status
from dsdk.graph import Edge, Graph
from dsdk.prob import NextTrackModel, fit_next_track, model_from_graph, next_track_distribution, top_next

from prob_helpers import Fr

SEQS = [["a", "b", "c"], ["a", "b", "d"], ["b", "c"], ["a"]]


def dist(model, track):
    j = next_track_distribution(model, track)
    assert j.status is Status.KNOWN, j
    return dict(j.value)


# ==== Fitting next-track counts from sequences ====
def test_fit_counts_vocabulary_and_alpha():
    """Fitting the toy sequences gives the vocabulary a, b, c, d, the counts (a,b)=2, (b,c)=2, (b,d)=1 and smoothing 1 as an exact fraction."""
    m = fit_next_track(SEQS)
    assert isinstance(m, NextTrackModel)
    assert m.tracks == ("a", "b", "c", "d")
    assert m.counts == {("a", "b"): 2, ("b", "c"): 2, ("b", "d"): 1}
    assert m.alpha == 1 and type(m.alpha) is Fraction
    assert m.outgoing("b") == 3 and m.outgoing("c") == 0 and m.outgoing("zzz") == 0


def test_pairs_never_span_two_sequences():
    """The last track of one sequence and the first of the next do not form a transition."""
    m = fit_next_track([["a", "b"], ["c", "d"]])
    assert m.counts == {("a", "b"): 1, ("c", "d"): 1}, "no (b, c) transition"


def test_repeats_are_pairs_and_counts_accumulate():
    """A track followed by itself is a transition, and repeated pairs across sequences add up."""
    m = fit_next_track([["a", "a", "a"], ["a", "a"]])
    assert m.counts == {("a", "a"): 3}


def test_short_sequences_add_tracks_but_no_pairs():
    """Empty sequences and one-track sequences add no transitions, but a one-track sequence still adds its track to the vocabulary."""
    m = fit_next_track([[], ["x"], ("y",)])
    assert m.tracks == ("x", "y") and m.counts == {}


def test_empty_input_gives_an_empty_model():
    """Fitting no sequences gives an empty vocabulary and no counts."""
    m = fit_next_track([])
    assert m.tracks == () and m.counts == {}


def test_extra_vocabulary_and_tuples_and_generators_are_accepted():
    """Sequences may be tuples inside a generator, and extra vocabulary tracks that were never seen receive smoothed probability."""
    m = fit_next_track((s for s in [("b", "a")]), alpha=0.5, vocabulary=["z", "a"])
    assert m.tracks == ("a", "b", "z") and m.alpha == Fr(1, 2)
    assert dist(m, "b")["z"] == Fr(1, 2) / (1 + Fr(1, 2) * 3)


def test_alpha_conversion_and_validation():
    """Smoothing is converted exactly (0.25 is 1/4), may be zero or larger than 1, and a negative, bool, string or nan value is rejected."""
    assert fit_next_track(SEQS, alpha=0.25).alpha == Fr(1, 4)
    assert fit_next_track(SEQS, alpha=0).alpha == 0
    assert fit_next_track(SEQS, alpha=Fr(7)).alpha == 7, "alpha is a pseudo-count, it may exceed 1"
    for bad, exc in [(-1, ValueError), (True, TypeError), ("1", TypeError), (float("nan"), ValueError)]:
        with pytest.raises(exc):
            fit_next_track(SEQS, alpha=bad)


@pytest.mark.parametrize("seqs,exc", [(["abc"], TypeError), ([[1, 2]], TypeError), ([["a", ""]], ValueError), ([["a", None]], TypeError), ([5], TypeError)])
def test_sequence_element_rules(seqs, exc):
    """A bare string as a sequence, non-string tracks and the empty string are rejected."""
    with pytest.raises(exc):
        fit_next_track(seqs)


def test_vocabulary_element_rules():
    """Extra vocabulary entries must be non-empty strings."""
    with pytest.raises(TypeError):
        fit_next_track(SEQS, vocabulary=[3])
    with pytest.raises(ValueError):
        fit_next_track(SEQS, vocabulary=[""])


# ==== The smoothed next-track distribution P(next given track) ====
def test_smoothed_distribution_alpha_one_by_hand():
    """With smoothing 1 the toy model gives P(.|a) = b 1/2 and 1/6 for the rest, and P(.|b) = c 3/7, d 2/7, a 1/7, b 1/7, as computed by hand."""
    m = fit_next_track(SEQS)
    assert dist(m, "a") == {"a": Fr(1, 6), "b": Fr(1, 2), "c": Fr(1, 6), "d": Fr(1, 6)}
    assert dist(m, "b") == {"a": Fr(1, 7), "b": Fr(1, 7), "c": Fr(3, 7), "d": Fr(2, 7)}


def test_distribution_is_a_tuple_in_canonical_order_summing_to_exactly_one():
    """A distribution is a tuple of (track, exact fraction) over the whole vocabulary in canonical order, summing to exactly 1."""
    m = fit_next_track(SEQS)
    j = next_track_distribution(m, "b")
    assert isinstance(j.value, tuple) and [t for t, _ in j.value] == list(m.tracks)
    assert all(type(p) is Fraction for _, p in j.value)
    assert sum(p for _, p in j.value) == 1


def test_never_followed_track_gets_the_uniform_distribution_when_smoothed():
    """A track never followed by anything gets the uniform distribution when smoothing is positive."""
    assert dist(fit_next_track(SEQS), "c") == {t: Fr(1, 4) for t in "abcd"}
    assert dist(fit_next_track(SEQS, alpha=3), "c") == {t: Fr(1, 4) for t in "abcd"}


def test_alpha_zero_is_raw_maximum_likelihood_with_explicit_zeros():
    """With smoothing 0 the distribution is the raw frequency, with explicit zero entries for unseen successors."""
    m = fit_next_track(SEQS, alpha=0)
    assert dist(m, "b") == {"a": 0, "b": 0, "c": Fr(2, 3), "d": Fr(1, 3)}
    assert dist(m, "a") == {"a": 0, "b": 1, "c": 0, "d": 0}


def test_alpha_zero_and_nothing_observed_is_unknown_not_uniform():
    """Inventing a uniform distribution here would be fabricated knowledge; the honest answer is UNKNOWN."""
    j = next_track_distribution(fit_next_track(SEQS, alpha=0), "c")
    assert j.status is Status.UNKNOWN and j.value is None and "alpha is 0" in j.reason


def test_unseen_track_is_not_observed_whatever_alpha_is():
    """A track outside the vocabulary is NOT_OBSERVED for any smoothing value; smoothing does not invent it."""
    for alpha in (0, 1, 5):
        j = next_track_distribution(fit_next_track(SEQS, alpha=alpha), "zzz")
        assert j.status is Status.NOT_OBSERVED and j.value is None and "zzz" in j.reason


def test_vocabulary_only_track_is_in_the_model_with_smoothing():
    """A track given only through the extra vocabulary has a uniform distribution and receives smoothed mass as a successor."""
    m = fit_next_track(SEQS, vocabulary=["e"])
    assert dist(m, "e") == {t: Fr(1, 5) for t in "abcde"}
    assert dist(m, "b")["e"] == Fr(1, 3 + 5)


def test_larger_alpha_flattens_towards_uniform():
    """Raising the smoothing pushes P(c|b) down toward 1/4, ending within 1/100 of uniform at alpha 1000."""
    p = [dist(fit_next_track(SEQS, alpha=a), "b")["c"] for a in (0, 1, 10, 1000)]
    assert p == sorted(p, reverse=True) and p[-1] - Fr(1, 4) < Fr(1, 100)


def test_smoothing_never_reorders_observed_counts():
    """Smoothing keeps the order of observed counts: more observed successors stay more likely, and equal unseen ones stay tied."""
    d = dist(fit_next_track(SEQS, alpha=Fr(1, 3)), "b")
    assert d["c"] > d["d"] > d["a"] == d["b"]


def test_distribution_argument_types():
    """A non-model or a non-string track is rejected with a TypeError."""
    m = fit_next_track(SEQS)
    with pytest.raises(TypeError):
        next_track_distribution("model", "a")
    with pytest.raises(TypeError):
        next_track_distribution(m, 1)


# ==== The most likely successor tracks ====
def test_top_next_orders_by_probability_then_canonical_order():
    """The top successors are ordered by probability, ties broken by canonical track order, and asking for more than the vocabulary is fine."""
    m = fit_next_track(SEQS)
    j = top_next(m, "b", 3)
    assert j.status is Status.KNOWN
    assert j.value == (("c", Fr(3, 7)), ("d", Fr(2, 7)), ("a", Fr(1, 7)))
    assert top_next(m, "b", 99).value[-1] == ("b", Fr(1, 7)), "tie a/b broken by canonical order; k larger than the vocabulary is fine"
    assert len(top_next(m, "b", 99).value) == 4


def test_top_next_drops_zero_probability_entries():
    """Successors with probability zero are not listed, so an unsmoothed model may return fewer than k."""
    m = fit_next_track(SEQS, alpha=0)
    assert top_next(m, "b", 5).value == (("c", Fr(2, 3)), ("d", Fr(1, 3)))


def test_top_next_passes_through_non_known_and_checks_k():
    """UNKNOWN and NOT_OBSERVED distributions pass through, and k must be an int of at least 1."""
    m = fit_next_track(SEQS, alpha=0)
    assert top_next(m, "c", 2).status is Status.UNKNOWN
    assert top_next(m, "zzz", 2).status is Status.NOT_OBSERVED
    for k, exc in [(0, ValueError), (-1, ValueError), (1.5, TypeError), (True, TypeError)]:
        with pytest.raises(exc):
            top_next(m, "a", k)


# ==== Reading a transition graph into a next-track model (the interface for the worlds package) ====
def transition_graph():
    return Graph.from_edges(
        [Edge("zed", "amp", weight=3), Edge("amp", "zed", weight=1), Edge("amp", "amp", weight=2),
         Edge("zed", "bus", weight=5, evidence=Status.UNKNOWN), Edge("bus", "amp")],
        nodes=["zed", "amp", "bus", "lone"],
    )


def test_model_from_graph_reads_known_edge_weights_as_counts():
    """A transition graph's KNOWN edge weights become counts (an unweighted edge counts 1, a self-loop is kept, an UNKNOWN edge is skipped) and the vocabulary keeps the graph's node order."""
    m = model_from_graph(transition_graph())
    assert m.tracks == ("zed", "amp", "bus", "lone"), "canonical order = the graph's node order, not sorted"
    assert m.counts == {("zed", "amp"): 3, ("amp", "zed"): 1, ("amp", "amp"): 2, ("bus", "amp"): 1}, "unweighted = 1, self-loop kept, UNKNOWN edge skipped"


def test_uncertain_edges_count_only_when_asked():
    """Inferred (UNKNOWN) edges are counted only when include_uncertain is true."""
    m = model_from_graph(transition_graph(), include_uncertain=True)
    assert m.counts[("zed", "bus")] == 5
    assert ("zed", "bus") not in model_from_graph(transition_graph()).counts


def test_graph_model_distribution_by_hand():
    """On the small transition graph with smoothing 1 the distributions of zed, amp and the isolated track match hand-computed fractions."""
    m = model_from_graph(transition_graph(), alpha=1)
    # zed: out 3 + alpha*4 = 7 ; amp: 3+1=4... counts amp->zed 1, amp->amp 2 => out 3
    assert dist(m, "zed") == {"zed": Fr(1, 7), "amp": Fr(4, 7), "bus": Fr(1, 7), "lone": Fr(1, 7)}
    assert dist(m, "amp") == {"zed": Fr(2, 7), "amp": Fr(3, 7), "bus": Fr(1, 7), "lone": Fr(1, 7)}
    assert dist(m, "lone") == {t: Fr(1, 4) for t in ("zed", "amp", "bus", "lone")}


def test_the_isolated_node_with_alpha_zero_is_unknown():
    """An isolated track with no outgoing transitions is UNKNOWN when smoothing is 0, while a track with transitions is KNOWN."""
    m = model_from_graph(transition_graph(), alpha=0)
    assert next_track_distribution(m, "lone").status is Status.UNKNOWN
    assert next_track_distribution(m, "bus").status is Status.KNOWN


def test_graph_and_sequences_give_the_same_model_when_the_graph_is_built_from_the_same_counts():
    """A graph built from the sequence counts gives exactly the same model and distributions as fitting the sequences directly."""
    seq_model = fit_next_track(SEQS)
    g = Graph.from_edges([Edge(x, y, weight=n) for (x, y), n in seq_model.counts.items()], nodes=seq_model.tracks)
    gm = model_from_graph(g)
    assert gm.counts == seq_model.counts and gm.tracks == seq_model.tracks and gm.alpha == seq_model.alpha
    for t in seq_model.tracks:
        assert next_track_distribution(gm, t) == next_track_distribution(seq_model, t)


def test_whole_valued_float_weights_are_accepted():
    """An edge weight of 3.0 is accepted as the count 3."""
    g = Graph.from_edges([Edge("a", "b", weight=3.0)])
    assert model_from_graph(g).counts == {("a", "b"): 3}


@pytest.mark.parametrize("w,exc", [(2.5, ValueError), (0, ValueError), (-1, ValueError), (True, TypeError)])
def test_bad_edge_weights(w, exc):
    """Edge weights that are fractional, zero or negative are a ValueError, and a bool weight is a TypeError."""
    g = Graph.from_edges([Edge("a", "b", weight=w)]) if not isinstance(w, bool) else Graph.from_edges([Edge("a", "b")])
    if isinstance(w, bool):
        g = Graph(g.nodes, (Edge("a", "b", weight=True),), True, False)  # bypass from_edges validation on purpose
    with pytest.raises(exc):
        model_from_graph(g)


def test_graph_must_be_directed_with_nonempty_str_nodes():
    """The transition graph must be directed with non-empty string nodes; undirected, integer-named and empty-named graphs are rejected."""
    with pytest.raises(ValueError):
        model_from_graph(Graph.from_edges([("a", "b")], directed=False))
    with pytest.raises(TypeError):
        model_from_graph(Graph.from_edges([(1, 2)]))
    with pytest.raises(ValueError):
        model_from_graph(Graph.from_edges([("", "b")]))
    with pytest.raises(TypeError):
        model_from_graph("graph")


# ==== Properties that hold for every sequence set and smoothing value ====
track_ids = st.sampled_from(["a", "b", "c", "d"])


@settings(max_examples=60)
@given(st.lists(st.lists(track_ids, max_size=6), max_size=5), st.sampled_from([Fr(0), Fr(1, 2), Fr(1), Fr(3)]))
def test_distributions_always_sum_to_one_and_match_the_formula(seqs, alpha):
    """For random sequences and smoothing values, every distribution sums to exactly 1 and every entry equals (count + alpha) / (outgoing + alpha * vocabulary size); empty unsmoothed rows are UNKNOWN."""
    m = fit_next_track(seqs, alpha=alpha)
    for t in m.tracks:
        j = next_track_distribution(m, t)
        out = sum(n for (x, _), n in m.counts.items() if x == t)
        if out + alpha * len(m.tracks) == 0:
            assert j.status is Status.UNKNOWN
            continue
        assert j.status is Status.KNOWN
        assert sum(p for _, p in j.value) == 1
        for y, p in j.value:
            assert p == (m.counts.get((t, y), 0) + alpha) / (out + alpha * len(m.tracks))
