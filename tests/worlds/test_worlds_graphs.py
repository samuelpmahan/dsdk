"""Evidence-labelled graphs of the Lost Lands world. Toy values are derived by hand (see tests/worlds/toy_world.py);
real-corpus values come from the independent script fixtures/worlds/gen_slices.py.

Toy derivation. Observed transitions: 0>1 (x2: sets A and C), 1>2, 2>3, 3>4, 4>3.
Co-selected pairs (sets A={0,1,2}, B={2,3}, C={0,1}, D={3,4}): {0,1} in A and C -> 2; {0,2},{1,2},{2,3},{3,4} -> 1 each.
"""
import pytest
from toy_world import toy_doc, toy_world

from dsdk.core import Status
from dsdk.graph import Graph, components
from dsdk.worlds import (
    COSELECTION_LABEL, TRANSITION_LABEL, coselection_graph, dj_graph, parse_lostlands, six_degrees_graph,
    transition_graph,
)


def edge_map(g):
    return {(e.source, e.target): (e.weight, e.evidence, e.label) for e in g.edges}


# ---------------------------------------------------------------------------------------------- transition graph


def test_transition_graph_toy():
    g = transition_graph(toy_world())
    assert isinstance(g, Graph) and g.directed and not g.closed_world
    assert g.nodes == (0, 1, 2, 3, 4, 5)  # T5 is never played but is still a node
    assert edge_map(g) == {(0, 1): (2, Status.KNOWN, None), (1, 2): (1, Status.KNOWN, None), (2, 3): (1, Status.KNOWN, None),
                           (3, 4): (1, Status.KNOWN, None), (4, 3): (1, Status.KNOWN, None)}
    assert g.neighbors(5) == () and g.predecessors(5) == ()
    assert all(isinstance(e.weight, int) and not isinstance(e.weight, bool) for e in g.edges)


def test_transition_graph_keeps_self_loops_and_counts_each_row():
    doc = toy_doc()
    doc["selections"] += [[1, 0, 0], [1, 0, 0]]  # T1 played again in set A (graph tests do not need contiguity)
    doc["transitions"] += [[1, 1, 0, 0]]
    doc["meta"].update(selectionEvents=12, transitionEvents=7)
    g = transition_graph(parse_lostlands(doc))
    assert g.get_edge(1, 1).weight == 1 and g.get_edge(1, 1).evidence is Status.KNOWN


def test_transition_graph_direction_matters():
    g = transition_graph(toy_world())
    assert g.has_edge(0, 1) and not g.has_edge(1, 0)
    assert g.has_edge(3, 4) and g.has_edge(4, 3)  # observed both ways, in set D


# ---------------------------------------------------------------------------------------------- co-selection graph


def test_coselection_graph_toy():
    g = coselection_graph(toy_world())
    assert not g.directed and not g.closed_world and g.nodes == (0, 1, 2, 3, 4, 5)
    assert edge_map(g) == {(0, 1): (2, Status.UNKNOWN, None), (0, 2): (1, Status.UNKNOWN, None), (1, 2): (1, Status.UNKNOWN, None),
                           (2, 3): (1, Status.UNKNOWN, None), (3, 4): (1, Status.UNKNOWN, None)}


def test_coselection_never_claims_known_even_for_back_to_back_pairs():
    """0 and 1 were observed back-to-back, yet the CO-SELECTION edge stays inferred: it records shared sets only."""
    g = coselection_graph(toy_world())
    assert g.get_edge(0, 1).evidence is Status.UNKNOWN and g.get_edge(1, 0).evidence is Status.UNKNOWN
    assert all(e.evidence is Status.UNKNOWN for e in g.edges)


def test_a_track_repeated_in_one_set_is_not_co_selected_with_itself_and_counts_once():
    g = coselection_graph(toy_world())
    assert not g.has_edge(3, 3)
    assert g.get_edge(3, 4).weight == 1  # T3 twice in set D still one shared set


def test_coselection_is_per_set_not_per_date_or_per_dj():
    """T0 (set A) and T3 (set B, same date, different DJ) are NOT co-selected; T1 and T4 never share a set."""
    g = coselection_graph(toy_world())
    assert not g.has_edge(0, 3) and not g.has_edge(1, 4) and not g.has_edge(0, 4)


def test_undated_set_still_co_selects():
    doc = toy_doc()
    doc["selections"] += [[4, 1, -1], [5, 1, -1]]
    doc["meta"]["selectionEvents"] = 12
    doc["transitions"].append([4, 5, 1, -1])
    doc["meta"]["transitionEvents"] = 7
    assert coselection_graph(parse_lostlands(doc)).get_edge(4, 5).weight == 1


# ---------------------------------------------------------------------------------------------- DJ graph


def test_dj_graph_by_tracks_toy():
    """G0 played {0,1,2}, G1 {2,3}, G2 {3,4}: G0-G1 share {2}, G1-G2 share {3}, G0-G2 share nothing."""
    g = dj_graph(toy_world())
    assert not g.directed and g.nodes == (0, 1, 2)
    assert edge_map(g) == {(0, 1): (1, Status.KNOWN, None), (1, 2): (1, Status.KNOWN, None)}
    assert edge_map(dj_graph(toy_world(), by="tracks")) == edge_map(g)


def test_dj_graph_by_members_toy():
    """Members: G0 {Ada}, G1 {Bo, Cy}, G2 {Cy}: only G1-G2 share an artist (Cy)."""
    g = dj_graph(toy_world(), by="members")
    assert g.nodes == (0, 1, 2) and edge_map(g) == {(1, 2): (1, Status.KNOWN, None)}


def test_dj_graph_weight_counts_distinct_shared_tracks_not_plays():
    doc = toy_doc()
    doc["selections"] += [[3, 0, 1], [3, 0, 1]]  # G0 plays T3 twice more in set C: G0-G1 now share {2, 3}
    doc["meta"]["selectionEvents"] = 12
    doc["transitions"] += [[3, 3, 0, 1]]
    doc["meta"]["transitionEvents"] = 7
    assert dj_graph(parse_lostlands(doc)).get_edge(0, 1).weight == 2


@pytest.mark.parametrize("bad", ["track", "Tracks", "", None, 3])
def test_dj_graph_rejects_unknown_modes(bad):
    with pytest.raises(ValueError):
        dj_graph(toy_world(), by=bad)


# ---------------------------------------------------------------------------------------------- six degrees graph


def test_six_degrees_graph_toy_edges_evidence_and_labels():
    """KNOWN: 0>1 1>2 2>3 3>4 4>3 (each also co-selected -> label 'co-selection,transition').
    UNKNOWN: reverses 1>0 2>1 3>2, and both directions of {0,2}. 3>4 and 4>3 are both observed, so both KNOWN."""
    g = six_degrees_graph(toy_world())
    assert g.directed and not g.closed_world and g.nodes == (0, 1, 2, 3, 4, 5)
    both = f"{COSELECTION_LABEL},{TRANSITION_LABEL}"
    assert both == "co-selection,transition"
    assert edge_map(g) == {
        (0, 1): (None, Status.KNOWN, both), (0, 2): (None, Status.UNKNOWN, COSELECTION_LABEL),
        (1, 0): (None, Status.UNKNOWN, COSELECTION_LABEL), (1, 2): (None, Status.KNOWN, both),
        (2, 0): (None, Status.UNKNOWN, COSELECTION_LABEL), (2, 1): (None, Status.UNKNOWN, COSELECTION_LABEL),
        (2, 3): (None, Status.KNOWN, both), (3, 2): (None, Status.UNKNOWN, COSELECTION_LABEL),
        (3, 4): (None, Status.KNOWN, both), (4, 3): (None, Status.KNOWN, both)}


def test_six_degrees_graph_known_self_loop_is_labelled_transition_only():
    doc = toy_doc()
    doc["selections"] += [[1, 0, 1], [1, 0, 1]]
    doc["transitions"] += [[1, 1, 0, 1]]
    doc["meta"].update(selectionEvents=12, transitionEvents=7)
    g = six_degrees_graph(parse_lostlands(doc))
    e = g.get_edge(1, 1)
    assert (e.evidence, e.label) == (Status.KNOWN, "transition")


def test_labels_and_constants():
    assert TRANSITION_LABEL == "transition" and COSELECTION_LABEL == "co-selection"


# ---------------------------------------------------------------------------------------------- real corpus


def test_real_graph_totals_match_the_independent_script(real_world, slices):
    t = slices["graph_totals"]
    tg, cg = transition_graph(real_world), coselection_graph(real_world)
    assert len(tg.edges) == t["transition_edges"] == 1894
    assert sum(1 for e in tg.edges if e.source == e.target) == t["transition_self_loops"] == 3
    assert sum(e.weight for e in tg.edges) == t["transition_total_weight"] == len(real_world.transitions)
    assert len(cg.edges) == t["coselection_edges"] == 48298
    assert sum(e.weight for e in cg.edges) == t["coselection_total_weight"]
    assert len(tg.nodes) == len(cg.nodes) == 1352
    assert len(components(tg)) == t["transition_weak_components"] == 5


def test_real_dj_graph_matches_the_independent_script(real_world, slices):
    by_tracks, by_members = dj_graph(real_world), dj_graph(real_world, by="members")
    assert {f"{e.source},{e.target}": e.weight for e in by_tracks.edges} == slices["dj_tracks"]
    assert {f"{e.source},{e.target}": e.weight for e in by_members.edges} == slices["dj_members"]
    assert len(by_tracks.nodes) == 50 and len(by_tracks.edges) == 441 and len(by_members.edges) == 14


def test_real_track_neighbourhoods_match_hand_checked_slices(real_world, slices):
    """Space Laces - Torque (483), PEEKABOO & G-REX - Babatunde (237), the first and the last track: who followed and
    preceded each, how many times, and which tracks shared a set with it."""
    tg, cg = transition_graph(real_world), coselection_graph(real_world)
    for key, s in slices["tracks"].items():
        i = int(key)
        out = {str(e.target): e.weight for e in tg.edges if e.source == i}
        inn = {str(e.source): e.weight for e in tg.edges if e.target == i}
        assert out == s["out"], f"followers of {s['label']}"
        assert inn == s["in"], f"predecessors of {s['label']}"
        assert list(cg.neighbors(i)) == s["co_neighbours"], f"co-selected with {s['label']}"
    # read by a person: Torque was followed by its own VIP twice
    torque = slices["tracks"]["483"]
    vip = [k for k in torque["out"] if real_world.track_label(int(k)) == "Space Laces - Torque (VIP)"]
    assert len(vip) == 1 and torque["out"][vip[0]] == 2


def test_real_co_pair_weights(real_world, slices):
    cg = coselection_graph(real_world)
    for key, n in slices["co_pairs"].items():
        a, b = (int(x) for x in key.split(","))
        assert cg.get_edge(a, b).weight == n


def test_real_six_degrees_graph_size(real_world, slices):
    g = six_degrees_graph(real_world)
    assert len(g.edges) == slices["graph_totals"]["six_degrees_edges"] == 96599
    assert sum(1 for e in g.edges if e.evidence is Status.KNOWN) == 1894
    assert len(components(g)) == slices["graph_totals"]["six_degrees_weak_components"]
