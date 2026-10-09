"""Six degrees of dubstep: SixDegrees.query returns a Judgment plus a witness path with per-hop evidence.

Three independent sources of truth:
1. hand-derived toy answers (tests/worlds/toy_world.py);
2. a DIFFERENTIAL test against dsdk.graph (reachable, shortest_path, candidate_path) on many small random worlds --
   SixDegrees must give the same Judgment (status, value, reason) and the same witness path;
3. fixtures/worlds/lostlands_slices.json["degrees"], produced by fixtures/worlds/gen_slices.py with different algorithms.

Toy derivation. Known edges: 0>1 1>2 2>3 3>4 4>3. Inferred edges: 1>0 2>1 3>2 0>2 2>0.
"""
import random

import pytest
from toy_world import toy_world

from dsdk.core import Judgment, Status
from dsdk.graph import candidate_path, reachable, shortest_path, known_subgraph
from dsdk.worlds import Degrees, Hop, SixDegrees, parse_lostlands, six_degrees, six_degrees_graph


@pytest.fixture(scope="module")
def toy():
    return SixDegrees(toy_world())


def hops_of(d):
    return [(h.source, h.target, h.evidence, h.count, h.sets) for h in d.hops]


# ---------------------------------------------------------------------------------------------- toy, by hand


def test_known_path_when_every_step_was_observed(toy):
    d = toy.query(0, 4)
    assert isinstance(d, Degrees) and d.path == (0, 1, 2, 3, 4)
    assert d.judgment == Judgment(Status.KNOWN, True, "known path: 0 -> 1 -> 2 -> 3 -> 4")
    assert hops_of(d) == [
        (0, 1, Status.KNOWN, 2, ((0, 0), (0, 1))),  # seen in set A (Ada, day 0) and set C (Ada, day 1)
        (1, 2, Status.KNOWN, 1, ((0, 0),)),
        (2, 3, Status.KNOWN, 1, ((1, 0),)),
        (3, 4, Status.KNOWN, 1, ((2, 1),)),
    ]
    assert (d.source, d.target) == (0, 4)


def test_known_path_beats_a_shorter_path_that_uses_inferred_edges(toy):
    """0 and 2 share a set (inferred 0>2, one hop) but the OBSERVED route 0>1>2 is what counts as KNOWN."""
    d = toy.query(0, 2)
    assert d.judgment.status is Status.KNOWN and d.path == (0, 1, 2)
    assert all(h.evidence is Status.KNOWN for h in d.hops)


def test_inferred_path_is_unknown_and_names_the_inferred_steps(toy):
    """4>3 observed; 3>2 and 2>0 only inferred (no observed move from 3 to 2 or 2 to 0). Via 2>1>0 would cost 3."""
    d = toy.query(4, 0)
    assert d.path == (4, 3, 2, 0)
    assert d.judgment.status is Status.UNKNOWN and d.judgment.value is None
    assert d.judgment.reason == "uncertain edges on best candidate path: 3->2 (unknown), 2->0 (unknown)"
    assert hops_of(d) == [
        (4, 3, Status.KNOWN, 1, ((2, 1),)),
        (3, 2, Status.UNKNOWN, 1, ((1, 0),)),  # tracks 3 and 2 met only in set B
        (2, 0, Status.UNKNOWN, 1, ((0, 0),)),  # tracks 2 and 0 met only in set A
    ]


def test_one_inferred_step_is_enough_to_lose_known(toy):
    d = toy.query(1, 0)
    assert d.path == (1, 0) and d.judgment.reason == "uncertain edges on best candidate path: 1->0 (unknown)"
    assert d.hops == (Hop(1, 0, Status.UNKNOWN, 2, ((0, 0), (0, 1))),)  # 0 and 1 share TWO sets


def test_fewest_inferred_edges_wins_before_fewest_hops(toy):
    """From 3 to 0: 3>2>0 is two hops with two inferred edges; no observed-only route exists. Equal-cost ties go to the
    lexicographically smaller node sequence: (3,2,0) not (3,2,1,0)."""
    d = toy.query(3, 0)
    assert d.path == (3, 2, 0)


def test_unplayed_track_is_unreachable_but_not_impossible(toy):
    """T5 was never played: no evidence either way. The answer is UNKNOWN (open world), never KNOWN False."""
    for a, b in ((0, 5), (5, 0)):
        d = toy.query(a, b)
        assert d.judgment == Judgment(
            Status.UNKNOWN, None, "open world: no path found, but absence of an edge is not proof of impossibility")
        assert d.path is None and d.hops == ()


def test_a_track_reaches_itself_with_the_empty_path(toy):
    for t in (3, 5):
        d = toy.query(t, t)
        assert d.judgment == Judgment(Status.KNOWN, True, f"known path: {t}") and d.path == (t,) and d.hops == ()


@pytest.mark.parametrize("src, dst, bad", [(0, 9, 9), (9, 0, 9), (-1, 0, -1), (0, 6, 6), (9, -1, 9), (True, 0, True),
                                          (0, False, False), ("0", 1, "0"), (None, 1, None), (0, 2.0, 2.0), (1.5, 1, 1.5)])
def test_non_tracks_are_invalid_not_exceptions_and_name_the_first_bad_node(toy, src, dst, bad):
    d = toy.query(src, dst)
    assert d.judgment.status is Status.INVALID and d.judgment.value is None
    assert d.judgment.reason == f"node {bad!r} is not in the graph"
    assert d.path is None and d.hops == ()
    assert d.source is src and d.target is dst


def test_invalid_unknown_and_known_false_are_three_different_answers(toy):
    answers = {toy.query(0, 9).judgment.status, toy.query(0, 5).judgment.status, toy.query(0, 4).judgment.status}
    assert answers == {Status.INVALID, Status.UNKNOWN, Status.KNOWN}


def test_hop_lookup(toy):
    assert toy.hop(0, 1) == Hop(0, 1, Status.KNOWN, 2, ((0, 0), (0, 1)))
    assert toy.hop(1, 0) == Hop(1, 0, Status.UNKNOWN, 2, ((0, 0), (0, 1)))
    assert toy.hop(3, 4).count == 1 and toy.hop(4, 3).evidence is Status.KNOWN
    for a, b in ((0, 3), (0, 5), (9, 0), (0, 0), (-1, 1)):
        with pytest.raises(ValueError) as err:
            toy.hop(a, b)
        assert str(err.value) == f"no edge {a} -> {b}"


def test_index_exposes_the_graphs_it_searches(toy):
    assert toy.graph.edges == six_degrees_graph(toy_world()).edges
    assert all(e.evidence is Status.KNOWN for e in toy.known.edges) and len(toy.known.edges) == 5
    assert toy.known.nodes == toy.graph.nodes


def test_query_is_repeatable_and_does_not_mutate_the_index(toy):
    first = [toy.query(a, b) for a in range(6) for b in range(6)]
    second = [toy.query(a, b) for a in range(6) for b in range(6)]
    assert first == second


def test_six_degrees_convenience_matches_the_class():
    w = toy_world()
    assert six_degrees(w, 4, 0) == SixDegrees(w).query(4, 0)


def test_undated_set_sorts_first_in_hop_sets():
    doc = {
        "schema": "jukebox-primitives/v1",
        "meta": {"tracks": 2, "selectionEvents": 4, "transitionEvents": 2},
        "artists": ["A"], "tracks": [["a#1", "a", [0], [], None, []], ["b#1", "b", [0], [], None, []]],
        "selectorGroups": [[[0], "A", 0]], "dates": ["2018-01-01"],
        "selections": [[0, 0, 0], [1, 0, 0], [0, 0, -1], [1, 0, -1]],
        "transitions": [[0, 1, 0, 0], [0, 1, 0, -1]],
    }
    h = SixDegrees(parse_lostlands(doc)).hop(0, 1)
    assert h.sets == ((0, None), (0, 0)) and h.count == 2 and h.evidence is Status.KNOWN


# ---------------------------------------------------------------------------------------------- differential vs dsdk.graph


def random_world(seed):
    rng = random.Random(seed)
    n_tracks, n_groups, n_dates = rng.randint(2, 14), rng.randint(1, 3), rng.randint(1, 2)
    sel, trn = [], []
    sets = [(g, d) for g in range(n_groups) for d in range(n_dates)]
    rng.shuffle(sets)
    for g, d in sets[: rng.randint(1, len(sets))]:
        tracks = [rng.randrange(n_tracks) for _ in range(rng.randint(1, 6))]
        sel += [[t, g, d] for t in tracks]
        trn += [[a, b, g, d] for a, b in zip(tracks, tracks[1:])]
    return parse_lostlands({
        "schema": "jukebox-primitives/v1",
        "meta": {"tracks": n_tracks, "selectionEvents": len(sel), "transitionEvents": len(trn)},
        "artists": ["x"], "tracks": [[f"t{i}#1", f"t{i}", [0], [], None, []] for i in range(n_tracks)],
        "selectorGroups": [[[0], f"g{g}", 0] for g in range(n_groups)], "dates": [f"d{d}" for d in range(n_dates)],
        "selections": sel, "transitions": trn})


@pytest.mark.parametrize("seed", range(40))
def test_matches_dsdk_graph_reachable_on_random_worlds(seed):
    """The indexed search must be indistinguishable from dsdk.graph on every ordered pair: same Judgment (status, value
    and the exact reason string) and the same witness path (BFS tie-breaks for KNOWN, candidate_path for UNKNOWN)."""
    world = random_world(seed)
    sd = SixDegrees(world)
    g = sd.graph
    n = len(world.tracks)
    for a in range(n):
        for b in range(n):
            d = sd.query(a, b)
            expected = reachable(g, a, b)
            assert d.judgment == expected, f"seed {seed}: {a}->{b}"
            if expected.status is Status.KNOWN:
                assert d.path == shortest_path(known_subgraph(g), a, b)
            elif expected.reason.startswith("uncertain"):
                assert d.path == candidate_path(g, a, b)
            else:
                assert d.path is None
            if d.path:
                assert [(h.source, h.target) for h in d.hops] == list(zip(d.path, d.path[1:]))
                for h in d.hops:
                    assert h.evidence is g.get_edge(h.source, h.target).evidence


# ---------------------------------------------------------------------------------------------- real corpus


def test_real_degrees_match_the_independent_script(real_degrees, slices):
    """47 pairs: known chains of 1-20+ hops, one-way pairs that need inferred edges, disconnected pairs, self pairs. The
    expected paths come from a different algorithm (Bellman-Ford + backward table), so a tie-break bug shows up here."""
    cases = slices["degrees"]
    assert len(cases) >= 40
    seen = set()
    for c in cases:
        d = real_degrees.query(c["source"], c["target"])
        assert d.judgment.status.value == c["status"], c
        assert d.judgment.reason == c["reason"]
        assert (list(d.path) if d.path else None) == c["path"]
        got = [{"evidence": h.evidence.value, "count": h.count, "sets": [list(s) for s in h.sets], "source": h.source, "target": h.target}
               for h in d.hops]
        assert got == c["hops"]
        seen.add((c["status"], d.path is None, any(h.evidence is Status.UNKNOWN for h in d.hops)))
    assert {("known", False, False), ("unknown", False, True), ("unknown", True, False)} <= seen


def test_real_torque_to_babatunde_is_four_observed_hops(real_degrees, real_world):
    """Space Laces - Torque -> ... -> PEEKABOO & G-REX - Babatunde, every step actually played back-to-back by someone."""
    d = real_degrees.query(483, 237)
    assert d.judgment.status is Status.KNOWN and d.path == (483, 259, 1010, 951, 237)
    assert [real_world.track_label(t) for t in d.path] == [
        "Space Laces - Torque", "Kompany - Stomp", "Tokey - High Breed", "SKisM - Experts (REMIX)",
        "PEEKABOO (USA) & G-REX - Babatunde"]
    assert all(h.evidence is Status.KNOWN and h.count >= 1 and h.sets for h in d.hops)


def test_real_every_known_hop_comes_from_a_set_that_really_has_that_transition(real_degrees, real_world):
    sets = real_world.sets()
    for pair in ((483, 237), (5, 900), (0, 1351)):
        for h in real_degrees.query(*pair).hops:
            for key in h.sets:
                tracks = sets[key]
                assert (h.source, h.target) in list(zip(tracks, tracks[1:]))
