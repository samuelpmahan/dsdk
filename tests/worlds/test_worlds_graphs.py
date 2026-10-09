"""Evidence-labelled graphs of the Lost Lands world. Toy values are derived by hand (see tests/worlds/toy_world.py);
real-corpus values come from the independent script fixtures/worlds/gen_slices.py.

Toy derivation. Observed transitions: 0>1 (x2: sets A and C), 1>2, 2>3, 3>4, 4>3.
Co-selected pairs (sets A={0,1,2}, B={2,3}, C={0,1}, D={3,4}): {0,1} in A and C -> 2; {0,2},{1,2},{2,3},{3,4} -> 1 each.
"""
import pytest
from toy_world import KEYS, E, K, toy_doc, toy_world

from dsdk.core import Status
from dsdk.graph import Graph, components
from dsdk.prob import next_track_distribution, top_next
from dsdk.worlds import (
    COSELECTION_LABEL, TRANSITION_LABEL, coselection_graph, dj_graph, next_track_model, parse_lostlands,
    six_degrees_graph, transition_graph,
)


def edge_map(g):
    return {(e.source, e.target): (e.weight, e.evidence, e.label) for e in g.edges}


# ==== Track transition graph: directed, weighted by count, observed (KNOWN) ====
def test_transition_graph_toy():
    """The toy transition graph has all 6 tracks as nodes (including the never-played one) and exactly the 5 observed moves, with 0 to 1 weighted 2 because it happened twice, all KNOWN."""
    g = transition_graph(toy_world())
    assert isinstance(g, Graph) and g.directed and not g.closed_world
    assert g.nodes == tuple(KEYS)  # Six#001 is never played but is still a node
    assert edge_map(g) == {E(0, 1): (2, Status.KNOWN, None), E(1, 2): (1, Status.KNOWN, None), E(2, 3): (1, Status.KNOWN, None),
                           E(3, 4): (1, Status.KNOWN, None), E(4, 3): (1, Status.KNOWN, None)}
    assert g.neighbors(K(5)) == () and g.predecessors(K(5)) == ()
    assert all(isinstance(n, str) for n in g.nodes)
    assert all(isinstance(e.weight, int) and not isinstance(e.weight, bool) for e in g.edges)


def test_transition_graph_keeps_self_loops_and_counts_each_row():
    """A track followed by itself becomes a self-loop edge with weight 1, and it is KNOWN."""
    doc = toy_doc()
    doc["selections"] += [[1, 0, 0], [1, 0, 0]]  # T1 played again in set A (graph tests do not need contiguity)
    doc["transitions"] += [[1, 1, 0, 0]]
    doc["meta"].update(selectionEvents=12, transitionEvents=7)
    g = transition_graph(parse_lostlands(doc))
    assert g.get_edge(K(1), K(1)).weight == 1 and g.get_edge(K(1), K(1)).evidence is Status.KNOWN


def test_transition_graph_direction_matters():
    """The transition graph is directed: 0 to 1 exists without 1 to 0, while 3 to 4 and 4 to 3 both exist because both were observed."""
    g = transition_graph(toy_world())
    assert g.has_edge(K(0), K(1)) and not g.has_edge(K(1), K(0))
    assert g.has_edge(K(3), K(4)) and g.has_edge(K(4), K(3))  # observed both ways, in set D


# ==== Co-selection graph: shared sets, inferred (UNKNOWN) ====
def test_coselection_graph_toy():
    """The toy co-selection graph has exactly the five pairs that shared a set, weighted by the number of shared sets, all UNKNOWN (inferred)."""
    g = coselection_graph(toy_world())
    assert not g.directed and not g.closed_world and g.nodes == tuple(KEYS)
    assert edge_map(g) == {E(0, 1): (2, Status.UNKNOWN, None), E(0, 2): (1, Status.UNKNOWN, None), E(1, 2): (1, Status.UNKNOWN, None),
                           E(2, 3): (1, Status.UNKNOWN, None), E(3, 4): (1, Status.UNKNOWN, None)}


def test_coselection_never_claims_known_even_for_back_to_back_pairs():
    """0 and 1 were observed back-to-back, yet the CO-SELECTION edge stays inferred: it records shared sets only."""
    g = coselection_graph(toy_world())
    assert g.get_edge(K(0), K(1)).evidence is Status.UNKNOWN and g.get_edge(K(1), K(0)).evidence is Status.UNKNOWN
    assert all(e.evidence is Status.UNKNOWN for e in g.edges)


def test_a_track_repeated_in_one_set_is_not_co_selected_with_itself_and_counts_once():
    """A track played twice in one set creates no self-edge and still counts as one shared set with its neighbour."""
    g = coselection_graph(toy_world())
    assert not g.has_edge(K(3), K(3))
    assert g.get_edge(K(3), K(4)).weight == 1  # T3 twice in set D still one shared set


def test_coselection_is_per_set_not_per_date_or_per_dj():
    """T0 (set A) and T3 (set B, same date, different DJ) are NOT co-selected; T1 and T4 never share a set."""
    g = coselection_graph(toy_world())
    assert not g.has_edge(K(0), K(3)) and not g.has_edge(K(1), K(4)) and not g.has_edge(K(0), K(4))


def test_undated_set_still_co_selects():
    """Tracks in a set with no date are still co-selected with each other."""
    doc = toy_doc()
    doc["selections"] += [[4, 1, -1], [5, 1, -1]]
    doc["meta"]["selectionEvents"] = 12
    doc["transitions"].append([4, 5, 1, -1])
    doc["meta"]["transitionEvents"] = 7
    assert coselection_graph(parse_lostlands(doc)).get_edge(K(4), K(5)).weight == 1


# ==== DJ graph: which DJs share tracks or members ====
def test_dj_graph_by_tracks_toy():
    """G0 played {0,1,2}, G1 {2,3}, G2 {3,4}: G0-G1 share {2}, G1-G2 share {3}, G0-G2 share nothing."""
    g = dj_graph(toy_world())
    assert not g.directed and g.nodes == ("Ada", "Bo & Cy", "Cy + More")  # nodes are the DJ credit labels
    assert edge_map(g) == {("Ada", "Bo & Cy"): (1, Status.KNOWN, None), ("Bo & Cy", "Cy + More"): (1, Status.KNOWN, None)}
    assert edge_map(dj_graph(toy_world(), by="tracks")) == edge_map(g)


def test_dj_graph_by_members_toy():
    """Members: G0 {Ada}, G1 {Bo, Cy}, G2 {Cy}: only G1-G2 share an artist (Cy)."""
    g = dj_graph(toy_world(), by="members")
    assert g.nodes == ("Ada", "Bo & Cy", "Cy + More") and edge_map(g) == {("Bo & Cy", "Cy + More"): (1, Status.KNOWN, None)}


def test_dj_graph_weight_counts_distinct_shared_tracks_not_plays():
    """The DJ graph weight is the number of distinct shared tracks, so playing the same shared track twice does not add weight."""
    doc = toy_doc()
    doc["selections"] += [[3, 0, 1], [3, 0, 1]]  # G0 plays T3 twice more in set C: G0-G1 now share {2, 3}
    doc["meta"]["selectionEvents"] = 12
    doc["transitions"] += [[3, 3, 0, 1]]
    doc["meta"]["transitionEvents"] = 7
    assert dj_graph(parse_lostlands(doc)).get_edge('Ada', 'Bo & Cy').weight == 2


@pytest.mark.parametrize("bad", ["track", "Tracks", "", None, 3])
def test_dj_graph_rejects_unknown_modes(bad):
    """dj_graph raises ValueError for any mode other than 'tracks' or 'members'."""
    with pytest.raises(ValueError):
        dj_graph(toy_world(), by=bad)


# ==== Combined search graph: observed moves plus inferred co-selection ====
def test_six_degrees_graph_toy_edges_evidence_and_labels():
    """KNOWN: 0>1 1>2 2>3 3>4 4>3 (each also co-selected -> label 'co-selection,transition').
    UNKNOWN: reverses 1>0 2>1 3>2, and both directions of {0,2}. 3>4 and 4>3 are both observed, so both KNOWN."""
    g = six_degrees_graph(toy_world())
    assert g.directed and not g.closed_world and g.nodes == tuple(KEYS)
    both = f"{COSELECTION_LABEL},{TRANSITION_LABEL}"
    assert both == "co-selection,transition"
    assert edge_map(g) == {
        E(0, 1): (None, Status.KNOWN, both), E(0, 2): (None, Status.UNKNOWN, COSELECTION_LABEL),
        E(1, 0): (None, Status.UNKNOWN, COSELECTION_LABEL), E(1, 2): (None, Status.KNOWN, both),
        E(2, 0): (None, Status.UNKNOWN, COSELECTION_LABEL), E(2, 1): (None, Status.UNKNOWN, COSELECTION_LABEL),
        E(2, 3): (None, Status.KNOWN, both), E(3, 2): (None, Status.UNKNOWN, COSELECTION_LABEL),
        E(3, 4): (None, Status.KNOWN, both), E(4, 3): (None, Status.KNOWN, both)}


def test_six_degrees_graph_known_self_loop_is_labelled_transition_only():
    """An observed self-loop in the search graph is KNOWN and labelled just 'transition', since co-selection never links a track to itself."""
    doc = toy_doc()
    doc["selections"] += [[1, 0, 1], [1, 0, 1]]
    doc["transitions"] += [[1, 1, 0, 1]]
    doc["meta"].update(selectionEvents=12, transitionEvents=7)
    g = six_degrees_graph(parse_lostlands(doc))
    e = g.get_edge(K(1), K(1))
    assert (e.evidence, e.label) == (Status.KNOWN, "transition")


def test_labels_and_constants():
    """The two edge labels are exactly 'transition' and 'co-selection'."""
    assert TRANSITION_LABEL == "transition" and COSELECTION_LABEL == "co-selection"


# ==== Next-track model fitted from the transition graph by dsdk.prob ====


def test_next_track_model_toy_counts_and_probabilities():
    """The toy next-track model has all 6 track keys as its vocabulary and exactly the observed move counts, and with smoothing 1 the chance that Two follows One is (2+1)/(2+6) = 3/8 while every other track gets 1/8."""
    from fractions import Fraction

    m = next_track_model(toy_world())
    assert m.tracks == tuple(KEYS)
    assert m.counts == {E(0, 1): 2, E(1, 2): 1, E(2, 3): 1, E(3, 4): 1, E(4, 3): 1}
    dist = dict(next_track_distribution(m, K(0)).value)
    assert dist[K(1)] == Fraction(3, 8) and all(dist[k] == Fraction(1, 8) for k in KEYS if k != K(1)) and sum(dist.values()) == 1


def test_next_track_model_uses_observed_moves_only_and_passes_alpha_through():
    """Inferred co-selection never enters the next-track counts, and alpha=0 gives the raw frequencies: after One the model says Two with probability exactly 1 and a never-followed track has no distribution at all."""
    from dsdk.core import Status
    from fractions import Fraction

    m = next_track_model(toy_world(), alpha=0)
    assert top_next(m, K(0), 3).value == ((K(1), Fraction(1)),)
    assert next_track_distribution(m, K(5)).status is Status.UNKNOWN  # Six#001 was never played, so nothing follows it
    assert next_track_distribution(m, "Nine#001").status is Status.NOT_OBSERVED


def test_next_track_model_real_counts_match_the_transition_graph(real_world, slices):
    """On the real corpus the next-track model has 1,352 tracks and 1,919 total counts, and Space Laces - Torque was followed 12 times in all, matching the independent script."""
    m = next_track_model(real_world)
    assert len(m.tracks) == 1352 and sum(m.counts.values()) == len(real_world.transitions) == 1919
    assert m.outgoing(real_world.tracks[483].key) == sum(slices["tracks"]["483"]["out"].values()) == 12


# ==== Real-corpus graphs match the independent counting script ====
def test_real_graph_totals_match_the_independent_script(real_world, slices):
    """On the real corpus the transition and co-selection graphs have the same edge counts, self-loop count, total weights and component count as the independent counting script."""
    t = slices["graph_totals"]
    tg, cg = transition_graph(real_world), coselection_graph(real_world)
    assert len(tg.edges) == t["transition_edges"] == 1894
    assert sum(1 for e in tg.edges if e.source == e.target) == t["transition_self_loops"] == 3
    assert sum(e.weight for e in tg.edges) == t["transition_total_weight"] == len(real_world.transitions)
    assert len(cg.edges) == t["coselection_edges"] == 48298
    assert sum(e.weight for e in cg.edges) == t["coselection_total_weight"]
    assert len(tg.nodes) == len(cg.nodes) == 1352 and tg.nodes[483] == real_world.tracks[483].key
    assert len(components(tg)) == t["transition_weak_components"] == 5


def test_real_dj_graph_matches_the_independent_script(real_world, slices):
    """The real DJ graph (both by shared tracks and by shared members) has exactly the edges and weights the independent script computed."""
    by_tracks, by_members = dj_graph(real_world), dj_graph(real_world, by="members")
    name = [g.label for g in real_world.groups]
    assert {f"{name.index(e.source)},{name.index(e.target)}": e.weight for e in by_tracks.edges} == slices["dj_tracks"]
    assert {f"{name.index(e.source)},{name.index(e.target)}": e.weight for e in by_members.edges} == slices["dj_members"]
    assert len(by_tracks.nodes) == 50 and len(by_tracks.edges) == 441 and len(by_members.edges) == 14


def test_real_track_neighbourhoods_match_hand_checked_slices(real_world, slices):
    """Space Laces - Torque (483), PEEKABOO & G-REX - Babatunde (237), the first and the last track: who followed and
    preceded each, how many times, and which tracks shared a set with it."""
    tg, cg = transition_graph(real_world), coselection_graph(real_world)
    keys = [t.key for t in real_world.tracks]
    for key, s in slices["tracks"].items():
        i = int(key)
        out = {str(keys.index(e.target)): e.weight for e in tg.edges if e.source == keys[i]}
        inn = {str(keys.index(e.source)): e.weight for e in tg.edges if e.target == keys[i]}
        assert out == s["out"], f"followers of {s['label']}"
        assert inn == s["in"], f"predecessors of {s['label']}"
        assert [keys.index(n) for n in cg.neighbors(keys[i])] == s["co_neighbours"], f"co-selected with {s['label']}"
    # read by a person: Torque was followed by its own VIP twice
    torque = slices["tracks"]["483"]
    vip = [k for k in torque["out"] if real_world.track_label(int(k)) == "Space Laces - Torque (VIP)"]
    assert len(vip) == 1 and torque["out"][vip[0]] == 2


def test_real_co_pair_weights(real_world, slices):
    """The twelve most co-selected real track pairs have exactly the shared-set counts the independent script computed."""
    cg = coselection_graph(real_world)
    for key, n in slices["co_pairs"].items():
        a, b = (int(x) for x in key.split(","))
        assert cg.get_edge(real_world.tracks[a].key, real_world.tracks[b].key).weight == n


def test_real_six_degrees_graph_size(real_world, slices):
    """The real search graph has 96,599 edges, of which exactly 1,894 are KNOWN, with the component count the independent script found."""
    g = six_degrees_graph(real_world)
    assert len(g.edges) == slices["graph_totals"]["six_degrees_edges"] == 96599
    assert sum(1 for e in g.edges if e.evidence is Status.KNOWN) == 1894
    assert len(components(g)) == slices["graph_totals"]["six_degrees_weak_components"]
