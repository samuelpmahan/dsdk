"""Contract tests for dsdk.prob.bayesnet construction and the exact joint: bayes_net, joint_belief.

A Bayes-net structure IS a dsdk.graph DAG; validation uses the graph's own cycle detection and edge evidence.
"""
import itertools
from fractions import Fraction

import pytest
from hypothesis import given, settings

from dsdk.core import Status
from dsdk.graph import CycleError, Edge, Graph
from dsdk.logic import And, Not, Var
from dsdk.prob import MAX_VARIABLES, BayesNet, bayes_net, joint_belief, marginals, probability

from prob_helpers import (
    BURGLARY_CPTS, BURGLARY_EDGES, BURGLARY_NODES, Fr, SPRINKLER_CPTS, SPRINKLER_EDGES, SPRINKLER_NODES, burglary, make_net,
    random_nets, ref_net_joint, ref_net_prob, sprinkler,
)


def lit(name, value=True):
    return Var(name) if value else Not(Var(name))


def conj_lits(d):
    out = None
    for k, v in d.items():
        out = lit(k, v) if out is None else And(out, lit(k, v))
    return out


# ==== Building a valid Bayes net keeps its structure and exact tables ====
def test_valid_net_keeps_structure_and_exact_fraction_cpts():
    """Valid net keeps structure and exact fraction cpts."""
    net = burglary()
    assert isinstance(net, BayesNet)
    assert net.structure.nodes == tuple(BURGLARY_NODES)
    assert net.cpts["Alarm"][(True, False)] == Fr(94, 100)
    assert all(type(p) is Fraction for rows in net.cpts.values() for p in rows.values())


def test_float_and_int_cpt_values_are_converted_exactly():
    """Float and int cpt values are converted exactly."""
    net = make_net(["X", "Y"], [("X", "Y")], {"X": {(): 0.2}, "Y": {(True,): 1, (False,): 0.05}})
    assert net.cpts["X"][()] == Fr(1, 5) and net.cpts["Y"][(True,)] == 1 and net.cpts["Y"][(False,)] == Fr(1, 20)


def test_net_stores_its_own_copy_of_the_tables():
    """Net stores its own copy of the tables."""
    cpts = {"X": {(): Fr(1, 2)}}
    net = bayes_net(Graph.from_edges([], ["X"]), cpts)
    cpts["X"][()] = Fr(1, 3)
    cpts["X"][(True,)] = Fr(1, 3)
    assert net.cpts == {"X": {(): Fr(1, 2)}}


def test_parent_order_is_the_graphs_node_order_not_the_edge_listing_order():
    """Alarm's key is (Burglary, Earthquake) because that is node order, whatever order the edges were listed in."""
    edges = [("Earthquake", "Alarm"), ("Burglary", "Alarm")]
    net = make_net(["Burglary", "Earthquake", "Alarm"], edges, {"Burglary": {(): Fr(1, 2)}, "Earthquake": {(): Fr(1, 2)},
                   "Alarm": {(True, False): Fr(1, 10), (True, True): Fr(2, 10), (False, True): Fr(3, 10), (False, False): Fr(4, 10)}})
    assert net.structure.predecessors("Alarm") == ("Burglary", "Earthquake")
    j = probability(joint_belief(net), Var("Alarm"), And(Var("Burglary"), Not(Var("Earthquake"))))
    assert j.value == Fr(1, 10)


def test_single_node_and_isolated_nodes_are_fine():
    """Single node and isolated nodes are fine."""
    net = make_net(["X", "Y"], [], {"X": {(): Fr(1, 2)}, "Y": {(): Fr(1, 4)}})
    assert joint_belief(net).total == 1


# ==== Invalid Bayes nets are rejected, checks run in the documented order ====
def test_structure_and_cpts_types():
    """A non-Graph structure or a non-Mapping cpts argument is rejected with a TypeError before anything else is looked at."""
    with pytest.raises(TypeError):
        bayes_net("graph", {})
    with pytest.raises(TypeError):
        bayes_net(Graph.from_edges([], ["X"]), [("X", 0.5)])


def test_undirected_graph_is_rejected():
    """A Bayes net must be directed: an undirected graph is a ValueError."""
    g = Graph.from_edges([("X", "Y")], directed=False)
    with pytest.raises(ValueError):
        bayes_net(g, {"X": {(): 0.5}, "Y": {(): 0.5}})


def test_directed_check_precedes_node_type_check():
    """The directed-graph check runs before the node-type check, so an undirected graph with integer nodes is a ValueError, not a TypeError."""
    g = Graph.from_edges([(1, 2)], directed=False)
    with pytest.raises(ValueError):
        bayes_net(g, {})


def test_non_str_nodes_are_a_type_error():
    """Node ids are variable names, so a graph whose nodes are integers is rejected with a TypeError."""
    g = Graph.from_edges([(1, 2)])
    with pytest.raises(TypeError):
        bayes_net(g, {1: {(): 0.5}, 2: {(True,): 0.5, (False,): 0.5}})


@pytest.mark.parametrize("status", [Status.UNKNOWN, Status.NOT_OBSERVED])
def test_uncertain_edges_are_refused_because_the_joint_would_be_fabricated(status):
    """An inferred/candidate dependency is not a verified structural claim: an exact net on it would be fabricated certainty."""
    g = Graph.from_edges([Edge("X", "Y", evidence=status)])
    with pytest.raises(ValueError, match="X") as info:
        bayes_net(g, {"X": {(): 0.5}, "Y": {(True,): 0.5, (False,): 0.5}})
    assert not isinstance(info.value, CycleError)


def test_known_edges_pass_the_evidence_check():
    """Edges whose evidence is KNOWN (observed structure) are accepted by the net builder."""
    g = Graph.from_edges([Edge("X", "Y", evidence=Status.KNOWN)])
    bayes_net(g, {"X": {(): 0.5}, "Y": {(True,): 0.5, (False,): 0.5}})


def test_cycle_is_rejected_with_the_graphs_cycle_error_and_a_witness():
    """Cycle is rejected with the graphs cycle error and a witness."""
    g = Graph.from_edges([("X", "Y"), ("Y", "Z"), ("Z", "X")])
    with pytest.raises(CycleError) as info:
        bayes_net(g, {})
    assert set(info.value.cycle) >= {"X", "Y", "Z"}


def test_self_loop_is_a_cycle():
    """Self loop is a cycle."""
    with pytest.raises(CycleError):
        bayes_net(Graph.from_edges([("X", "X")]), {"X": {(True,): 0.5, (False,): 0.5}})


def test_edge_evidence_is_checked_before_cycles():
    """An uncertain edge is reported as a plain ValueError even when it lies inside a cycle, because the evidence check comes before the cycle check."""
    g = Graph.from_edges([Edge("X", "Y", evidence=Status.UNKNOWN), ("Y", "X")])
    with pytest.raises(ValueError) as info:
        bayes_net(g, {})
    assert not isinstance(info.value, CycleError)


def test_cycle_is_checked_before_missing_cpts():
    """A cyclic graph is reported as a cycle even when the probability tables are missing, because the cycle check comes first."""
    with pytest.raises(CycleError):
        bayes_net(Graph.from_edges([("X", "Y"), ("Y", "X")]), {})


def test_missing_and_extra_cpt_nodes():
    """A table missing for a node, or a table given for a node the graph does not have, is a ValueError that names the node."""
    g = Graph.from_edges([("X", "Y")])
    with pytest.raises(ValueError, match="Y"):
        bayes_net(g, {"X": {(): 0.5}})
    with pytest.raises(ValueError, match="Z"):
        bayes_net(g, {"X": {(): 0.5}, "Y": {(True,): 0.5, (False,): 0.5}, "Z": {(): 0.5}})


def test_cpt_must_be_a_mapping():
    """A node's probability table must be a mapping from parent values to probabilities; a bare number is a TypeError."""
    with pytest.raises(TypeError):
        bayes_net(Graph.from_edges([], ["X"]), {"X": 0.5})


@pytest.mark.parametrize(
    "rows",
    [
        {(True,): 0.5, (False,): 0.5},  # root with parent keys
        {(): 0.5, (True,): 0.5},  # extra key
        {"": 0.5},  # not a tuple
    ],
)
def test_root_cpt_key_must_be_the_empty_tuple(rows):
    """A node with no parents must have exactly one table row, keyed by the empty tuple; extra or non-tuple keys are a ValueError."""
    with pytest.raises(ValueError):
        bayes_net(Graph.from_edges([], ["X"]), {"X": rows})


@pytest.mark.parametrize(
    "rows",
    [
        {(True,): 0.5},  # missing the False row
        {(True,): 0.5, (False,): 0.5, (True, True): 0.5},  # wrong length key
        {(1,): 0.5, (0,): 0.5},  # 1 and 0 are not bool
        {(True,): 0.5, (None,): 0.5},
        {},
    ],
)
def test_child_cpt_must_cover_exactly_the_parent_combinations_of_bools(rows):
    """A child's table must have every combination of its parents' True/False values, as real booleans (1 and 0 do not count), and no other keys."""
    g = Graph.from_edges([("X", "Y")])
    with pytest.raises(ValueError):
        bayes_net(g, {"X": {(): 0.5}, "Y": rows})


def test_two_parent_cpt_needs_all_four_rows():
    """Two parent cpt needs all four rows."""
    g = Graph.from_edges([("X", "Z"), ("Y", "Z")])
    rows = {(True, True): 0.5, (True, False): 0.5, (False, True): 0.5}
    with pytest.raises(ValueError):
        bayes_net(g, {"X": {(): 0.5}, "Y": {(): 0.5}, "Z": rows})


@pytest.mark.parametrize("p,exc", [(1.5, ValueError), (-0.5, ValueError), (True, TypeError), ("0.5", TypeError), (float("nan"), ValueError)])
def test_cpt_probabilities_go_through_to_prob(p, exc):
    """Table entries are validated like any probability: above 1, below 0 or nan is a ValueError, and a bool or string is a TypeError."""
    with pytest.raises(exc):
        bayes_net(Graph.from_edges([], ["X"]), {"X": {(): p}})


# ==== The joint distribution of a Bayes net is exact and matches textbook numbers ====
def test_joint_is_normalised_exactly_and_over_sorted_variables():
    """Joint is normalised exactly and over sorted variables."""
    j = joint_belief(burglary())
    assert j.variables == tuple(sorted(BURGLARY_NODES))
    assert len(j.worlds) == 32
    assert j.total == 1 and type(j.total) is Fraction


def test_joint_world_order_is_logic_models_order():
    """Joint world order is logic models order."""
    j = joint_belief(burglary())
    expected = [dict(zip(j.variables, c)) for c in itertools.product([False, True], repeat=5)]
    assert [w.assignment() for w in j.worlds] == expected


def test_joint_weights_are_products_of_cpt_entries_one_world_by_hand():
    """B=T, E=F, A=T, J=T, M=F: 0.001 * 0.998 * 0.94 * 0.90 * (1 - 0.70)."""
    j = joint_belief(burglary())
    target = {"Burglary": True, "Earthquake": False, "Alarm": True, "JohnCalls": True, "MaryCalls": False}
    w = next(w for w in j.worlds if w.assignment() == target)
    assert w.weight == Fr(1, 1000) * Fr(998, 1000) * Fr(94, 100) * Fr(90, 100) * Fr(30, 100)


def test_burglary_posterior_matches_the_textbook_value():
    """Russell & Norvig: P(Burglary | JohnCalls, MaryCalls) = 0.284 (exactly 0.28417...). An external number, not our own code."""
    j = joint_belief(burglary())
    p = probability(j, Var("Burglary"), And(Var("JohnCalls"), Var("MaryCalls"))).value
    assert float(p) == pytest.approx(0.284, abs=5e-4)
    assert p == ref_net_prob(BURGLARY_NODES, BURGLARY_EDGES, BURGLARY_CPTS, {"Burglary": True}, {"JohnCalls": True, "MaryCalls": True})


def test_sprinkler_explaining_away():
    """Textbook: P(Rain | Wet) = 0.708 but P(Rain | Wet, Sprinkler) = 0.320: learning the sprinkler was on 'explains away' the rain."""
    j = joint_belief(sprinkler())
    rain_wet = probability(j, Var("Rain"), Var("WetGrass")).value
    rain_wet_sprinkler = probability(j, Var("Rain"), And(Var("WetGrass"), Var("Sprinkler"))).value
    assert float(rain_wet) == pytest.approx(0.708, abs=5e-4)
    assert float(rain_wet_sprinkler) == pytest.approx(0.3204, abs=5e-4)
    assert rain_wet_sprinkler < rain_wet


def test_roots_are_marginally_their_prior_and_children_are_not():
    """Roots are marginally their prior and children are not."""
    j = joint_belief(sprinkler())
    m = marginals(j).value
    assert m["Cloudy"] == Fr(1, 2)
    assert m["Sprinkler"] == Fr(1, 2) * Fr(1, 10) + Fr(1, 2) * Fr(1, 2)
    assert m["Rain"] == Fr(1, 2) * Fr(8, 10) + Fr(1, 2) * Fr(2, 10)


def test_deterministic_cpt_rows_give_zero_weight_worlds_that_are_kept():
    """Deterministic cpt rows give zero weight worlds that are kept."""
    net = make_net(["X", "Y"], [("X", "Y")], {"X": {(): Fr(1, 2)}, "Y": {(True,): 1, (False,): 0}})
    j = joint_belief(net)
    assert len(j.worlds) == 4 and [w.weight for w in j.worlds] == [Fr(1, 2), 0, 0, Fr(1, 2)]


def test_conditioning_the_joint_on_an_impossible_event_is_invalid():
    """Conditioning the joint on an impossible event is invalid."""
    net = make_net(["X", "Y"], [("X", "Y")], {"X": {(): Fr(1, 2)}, "Y": {(True,): 1, (False,): 0}})
    j = probability(joint_belief(net), Var("X"), And(Var("X"), Not(Var("Y"))))
    assert j.status is Status.INVALID


def test_joint_variable_limit():
    """A net with more than the supported number of variables cannot be turned into a joint distribution and raises a ValueError."""
    nodes = [f"n{i:02d}" for i in range(MAX_VARIABLES + 1)]
    net = make_net(nodes, [], {n: {(): Fr(1, 2)} for n in nodes})
    with pytest.raises(ValueError):
        joint_belief(net)


def test_joint_type_error():
    """Asking for the joint distribution of something that is not a Bayes net is a TypeError."""
    with pytest.raises(TypeError):
        joint_belief("net")


@settings(max_examples=60)
@given(random_nets())
def test_joint_equals_the_independent_oracle_and_sums_to_one(spec):
    """For random small DAGs with random tables, the joint distribution has the same worlds, in the same order, with the same exact weights as an independent brute-force computation, and the weights sum to exactly 1."""
    nodes, edges, cpts = spec
    net = make_net(nodes, edges, cpts)
    j = joint_belief(net)
    oracle, names = ref_net_joint(nodes, edges, cpts)
    assert j.variables == tuple(names)
    assert [w.weight for w in j.worlds] == [oracle[tuple(v for _, v in w.values)] for w in j.worlds]
    assert [tuple(v for _, v in w.values) for w in j.worlds] == list(itertools.product([False, True], repeat=len(names)))
    assert j.total == 1


@settings(max_examples=40)
@given(random_nets(), )
def test_conditionals_match_the_oracle(spec):
    """For random small DAGs, a conditional probability read from the joint distribution equals the independent brute-force value, and impossible evidence is reported INVALID."""
    nodes, edges, cpts = spec
    net = make_net(nodes, edges, cpts)
    j = joint_belief(net)
    q, e = {nodes[-1]: True}, {nodes[0]: False}
    expected = ref_net_prob(nodes, edges, cpts, q, e)
    got = probability(j, conj_lits(q), conj_lits(e)) if nodes[0] != nodes[-1] else None
    if got is None:
        return
    if expected is None:
        assert got.status is Status.INVALID
    else:
        assert got.status is Status.KNOWN and got.value == expected
