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
from toy_world import KEYS, E, K, toy_world

from dsdk.core import Judgment, Status
from dsdk.graph import candidate_path, known_subgraph, reachable, shortest_path
from dsdk.worlds import Degrees, Hop, SixDegrees, parse_lostlands, six_degrees, six_degrees_graph


@pytest.fixture(scope="module")
def toy():
    return SixDegrees(toy_world())


def hops_of(d):
    return [(h.source, h.target, h.evidence, h.count, h.sets) for h in d.hops]


# ==== Six degrees on the toy festival (answers derived by hand) ====
def test_known_path_when_every_step_was_observed(toy):
    """On the toy festival, going from track 0 to track 4 is KNOWN along 0, 1, 2, 3, 4, and each step reports how many times it was seen and in which DJ sets."""
    d = toy.query(K(0), K(4))
    assert isinstance(d, Degrees) and d.path == tuple(K(i) for i in (0, 1, 2, 3, 4))
    assert d.judgment == Judgment(Status.KNOWN, True, "known path: One#001 -> Two#001 -> Three#001 -> Four#001 -> Five#001")
    assert hops_of(d) == [
        (K(0), K(1), Status.KNOWN, 2, ((0, 0), (0, 1))),  # seen in set A (Ada, day 0) and set C (Ada, day 1)
        (K(1), K(2), Status.KNOWN, 1, ((0, 0),)),
        (K(2), K(3), Status.KNOWN, 1, ((1, 0),)),
        (K(3), K(4), Status.KNOWN, 1, ((2, 1),)),
    ]
    assert (d.source, d.target) == (K(0), K(4))


def test_known_path_beats_a_shorter_path_that_uses_inferred_edges(toy):
    """0 and 2 share a set (inferred 0>2, one hop) but the OBSERVED route 0>1>2 is what counts as KNOWN."""
    d = toy.query(K(0), K(2))
    assert d.judgment.status is Status.KNOWN and d.path == (K(0), K(1), K(2))
    assert all(h.evidence is Status.KNOWN for h in d.hops)


def test_inferred_path_is_unknown_and_names_the_inferred_steps(toy):
    """4>3 observed; 3>2 and 2>0 only inferred (no observed move from 3 to 2 or 2 to 0). Via 2>1>0 would cost 3."""
    d = toy.query(K(4), K(0))
    assert d.path == (K(4), K(3), K(2), K(0))
    assert d.judgment.status is Status.UNKNOWN and d.judgment.value is None
    assert d.judgment.reason == "uncertain edges on best candidate path: Four#001->Three#001 (unknown), Three#001->One#001 (unknown)"
    assert hops_of(d) == [
        (K(4), K(3), Status.KNOWN, 1, ((2, 1),)),
        (K(3), K(2), Status.UNKNOWN, 1, ((1, 0),)),  # tracks 3 and 2 met only in set B
        (K(2), K(0), Status.UNKNOWN, 1, ((0, 0),)),  # tracks 2 and 0 met only in set A
    ]


def test_one_inferred_step_is_enough_to_lose_known(toy):
    """Going from track 1 back to track 0 is UNKNOWN because the reverse move was never observed; the single step is inferred from the two sets that contain both tracks."""
    d = toy.query(K(1), K(0))
    assert d.path == (K(1), K(0)) and d.judgment.reason == "uncertain edges on best candidate path: Two#001->One#001 (unknown)"
    assert d.hops == (Hop(K(1), K(0), Status.UNKNOWN, 2, ((0, 0), (0, 1))),)  # 0 and 1 share TWO sets


def test_fewest_inferred_edges_wins_before_fewest_hops(toy):
    """From 3 to 0: 3>2>0 is two hops with two inferred edges; no observed-only route exists. Equal-cost ties go to the
    lexicographically smaller node sequence: (3,2,0) not (3,2,1,0)."""
    d = toy.query(K(3), K(0))
    assert d.path == (K(3), K(2), K(0))


def test_unplayed_track_is_unreachable_but_not_impossible(toy):
    """T5 was never played: no evidence either way. The answer is UNKNOWN (open world), never KNOWN False."""
    for a, b in ((K(0), K(5)), (K(5), K(0))):
        d = toy.query(a, b)
        assert d.judgment == Judgment(
            Status.UNKNOWN, None, "open world: no path found, but absence of an edge is not proof of impossibility")
        assert d.path is None and d.hops == ()


def test_a_track_reaches_itself_with_the_empty_path(toy):
    """A track reaches itself with the one-node path and no steps, KNOWN, even for a track that was never played."""
    for t in (K(3), K(5)):
        d = toy.query(t, t)
        assert d.judgment == Judgment(Status.KNOWN, True, f"known path: {t}") and d.path == (t,) and d.hops == ()


@pytest.mark.parametrize("src, dst, bad", [(K(0), "Nine#001", "Nine#001"), ("Nine#001", K(0), "Nine#001"), (-1, K(0), -1), (K(0), 6, 6),
                                          ("Nine#001", -1, "Nine#001"), (True, K(0), True), (K(0), False, False), (0, K(1), 0),
                                          (None, K(1), None), (K(0), 2.0, 2.0), (1.5, K(1), 1.5), ("", K(1), ""), ([K(0)], K(1), [K(0)])])
def test_non_tracks_are_invalid_not_exceptions_and_name_the_first_bad_node(toy, src, dst, bad):
    """Asking about something that is not a track key (an unknown key, a bare integer, a bool, None, a float, a list) returns an INVALID judgment naming the first bad node and never raises."""
    d = toy.query(src, dst)
    assert d.judgment.status is Status.INVALID and d.judgment.value is None
    assert d.judgment.reason == f"node {bad!r} is not in the graph"
    assert d.path is None and d.hops == ()
    assert d.source is src and d.target is dst


def test_invalid_unknown_and_known_false_are_three_different_answers(toy):
    """An unknown track (INVALID), a never-played track (UNKNOWN) and a reachable track (KNOWN) give three different statuses."""
    answers = {toy.query(K(0), 'Nine#001').judgment.status, toy.query(K(0), K(5)).judgment.status, toy.query(K(0), K(4)).judgment.status}
    assert answers == {Status.INVALID, Status.UNKNOWN, Status.KNOWN}


def test_hop_lookup(toy):
    """SixDegrees.hop(a, b) reports the evidence for one step: the count and sets for an observed move, the shared sets for an inferred one, and a clear ValueError when there is no such edge."""
    assert toy.hop(K(0), K(1)) == Hop(K(0), K(1), Status.KNOWN, 2, ((0, 0), (0, 1)))
    assert toy.hop(K(1), K(0)) == Hop(K(1), K(0), Status.UNKNOWN, 2, ((0, 0), (0, 1)))
    assert toy.hop(K(3), K(4)).count == 1 and toy.hop(K(4), K(3)).evidence is Status.KNOWN
    for a, b in ((K(0), K(3)), (K(0), K(5)), ("Nine#001", K(0)), (K(0), K(0))):
        with pytest.raises(ValueError) as err:
            toy.hop(a, b)
        assert str(err.value) == f"no edge {a} -> {b}"


def test_index_exposes_the_graphs_it_searches(toy):
    """The SixDegrees object exposes the graph it searches and its observed-only subgraph, and they have the same nodes and the expected 5 observed edges."""
    assert toy.graph.edges == six_degrees_graph(toy_world()).edges
    assert all(e.evidence is Status.KNOWN for e in toy.known.edges) and len(toy.known.edges) == 5
    assert toy.known.nodes == toy.graph.nodes


def test_query_is_repeatable_and_does_not_mutate_the_index(toy):
    """Asking every pair of toy tracks twice gives identical answers, so a query does not change the index."""
    first = [toy.query(a, b) for a in KEYS for b in KEYS]
    second = [toy.query(a, b) for a in KEYS for b in KEYS]
    assert first == second


def test_six_degrees_convenience_matches_the_class():
    """The one-shot six_degrees function returns the same answer as building a SixDegrees object and querying it."""
    w = toy_world()
    assert six_degrees(w, K(4), K(0)) == SixDegrees(w).query(K(4), K(0))


def test_undated_set_sorts_first_in_hop_sets():
    """When a step is evidenced by one dated set and one undated set, the undated one is listed first and both are counted."""
    doc = {
        "schema": "jukebox-primitives/v1",
        "meta": {"tracks": 2, "selectionEvents": 4, "transitionEvents": 2},
        "artists": ["A"], "tracks": [["a#1", "a", [0], [], None, []], ["b#1", "b", [0], [], None, []]],
        "selectorGroups": [[[0], "A", 0]], "dates": ["2018-01-01"],
        "selections": [[0, 0, 0], [1, 0, 0], [0, 0, -1], [1, 0, -1]],
        "transitions": [[0, 1, 0, 0], [0, 1, 0, -1]],
    }
    h = SixDegrees(parse_lostlands(doc)).hop('a#1', 'b#1')
    assert h.sets == ((0, None), (0, 0)) and h.count == 2 and h.evidence is Status.KNOWN


# ==== The fast search gives the same answers as dsdk.graph reachability on 40 random worlds ====
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
    keys = [t.key for t in world.tracks]
    for a in keys:
        for b in keys:
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


# ==== Six degrees on the real corpus, checked against the independent oracle ====
def test_real_degrees_match_the_independent_script(real_degrees, slices):
    """47 pairs: known chains of 1-20+ hops, one-way pairs that need inferred edges, disconnected pairs, self pairs. The
    expected paths come from a different algorithm (Bellman-Ford + backward table), so a tie-break bug shows up here."""
    cases = slices["degrees"]
    keys = [t.key for t in real_degrees.world.tracks]
    assert len(cases) >= 40
    seen = set()
    for c in cases:
        d = real_degrees.query(keys[c["source"]], keys[c["target"]])
        assert d.judgment.status.value == c["status"], c
        assert d.judgment.reason == c["reason"]
        assert (list(d.path) if d.path else None) == c["path_keys"]
        got = [{"evidence": h.evidence.value, "count": h.count, "sets": [list(s) for s in h.sets],
                "source": keys.index(h.source), "target": keys.index(h.target)} for h in d.hops]
        assert got == c["hops"]
        seen.add((c["status"], d.path is None, any(h.evidence is Status.UNKNOWN for h in d.hops)))
    assert {("known", False, False), ("unknown", False, True), ("unknown", True, False)} <= seen


def test_real_torque_to_babatunde_is_four_observed_hops(real_degrees, real_world):
    """Space Laces - Torque -> ... -> PEEKABOO & G-REX - Babatunde, every step actually played back-to-back by someone."""
    keys = [t.key for t in real_world.tracks]
    d = real_degrees.query(keys[483], keys[237])
    assert d.judgment.status is Status.KNOWN and d.path == tuple(keys[i] for i in (483, 259, 1010, 951, 237))
    assert [real_world.track_label(keys.index(t)) for t in d.path] == [
        "Space Laces - Torque", "Kompany - Stomp", "Tokey - High Breed", "SKisM - Experts (REMIX)",
        "PEEKABOO (USA) & G-REX - Babatunde"]
    assert all(h.evidence is Status.KNOWN and h.count >= 1 and h.sets for h in d.hops)


def test_real_every_known_hop_comes_from_a_set_that_really_has_that_transition(real_degrees, real_world):
    """For three real queries, every observed step cites sets in which those two tracks really are consecutive."""
    sets = real_world.sets()
    keys = [t.key for t in real_world.tracks]
    for pair in ((483, 237), (5, 900), (0, 1351)):
        for h in real_degrees.query(keys[pair[0]], keys[pair[1]]).hops:
            for key in h.sets:
                tracks = [keys[t] for t in sets[key]]
                assert (h.source, h.target) in list(zip(tracks, tracks[1:]))


# ==== Step evidence counts plays, not sets ====


def test_a_move_repeated_inside_one_set_counts_twice_but_cites_the_set_once():
    """If one DJ plays track 0 then track 1 twice in the same set, the step 0 to 1 is reported as seen 2 times but cites that single set once."""
    doc = {
        "schema": "jukebox-primitives/v1",
        "meta": {"tracks": 2, "selectionEvents": 4, "transitionEvents": 3},
        "artists": ["A"], "tracks": [["a#1", "a", [0], [], None, []], ["b#1", "b", [0], [], None, []]],
        "selectorGroups": [[[0], "A", 0]], "dates": ["2018-01-01"],
        "selections": [[0, 0, 0], [1, 0, 0], [0, 0, 0], [1, 0, 0]],
        "transitions": [[0, 1, 0, 0], [1, 0, 0, 0], [0, 1, 0, 0]],
    }
    h = SixDegrees(parse_lostlands(doc)).hop('a#1', 'b#1')
    assert (h.evidence, h.count, h.sets) == (Status.KNOWN, 2, ((0, 0),))
