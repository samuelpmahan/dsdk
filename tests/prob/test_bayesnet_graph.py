"""Contract tests for the graph-driven parts of dsdk.prob.bayesnet: ancestors (BFS on the reversed DAG) and ancestral_net."""
import pytest
from hypothesis import given, settings

from dsdk.graph import MissingNodeError
from dsdk.prob import BayesNet, ancestors, ancestral_net, bayes_net, joint_belief, marginals

from prob_helpers import BURGLARY_NODES, Fr, burglary, make_net, random_nets, sprinkler


def test_ancestors_of_the_burglary_network():
    net = burglary()
    assert ancestors(net, "Burglary") == frozenset()
    assert ancestors(net, "Alarm") == {"Burglary", "Earthquake"}
    assert ancestors(net, "JohnCalls") == {"Alarm", "Burglary", "Earthquake"}
    assert ancestors(net, "MaryCalls") == ancestors(net, "JohnCalls")
    assert isinstance(ancestors(net, "Alarm"), frozenset)


def test_ancestors_exclude_the_node_itself_and_all_descendants():
    net = sprinkler()
    a = ancestors(net, "Sprinkler")
    assert a == {"Cloudy"} and "Sprinkler" not in a and "WetGrass" not in a and "Rain" not in a


def test_ancestors_follow_chains_and_diamonds():
    net = make_net(list("abcd"), [("a", "b"), ("a", "c"), ("b", "d"), ("c", "d")], {
        "a": {(): Fr(1, 2)}, "b": {(True,): Fr(1, 2), (False,): Fr(1, 3)}, "c": {(True,): Fr(1, 4), (False,): Fr(1, 5)},
        "d": {(True, True): Fr(1, 2), (True, False): Fr(1, 2), (False, True): Fr(1, 2), (False, False): Fr(1, 2)}})
    assert ancestors(net, "d") == {"a", "b", "c"}
    assert ancestors(net, "b") == {"a"}


def test_ancestors_errors():
    with pytest.raises(MissingNodeError):
        ancestors(burglary(), "Nope")
    with pytest.raises(TypeError):
        ancestors("net", "x")


def test_ancestral_net_of_a_leaf_keeps_only_what_it_depends_on():
    sub = ancestral_net(burglary(), {"Alarm"})
    assert isinstance(sub, BayesNet)
    assert sub.structure.nodes == ("Burglary", "Earthquake", "Alarm"), "original node order"
    assert [(e.source, e.target) for e in sub.structure.edges] == [("Burglary", "Alarm"), ("Earthquake", "Alarm")]
    assert sub.cpts["Alarm"] == burglary().cpts["Alarm"]
    assert len(joint_belief(sub).worlds) == 8, "barren descendants JohnCalls/MaryCalls are not enumerated"


def test_ancestral_net_of_a_root_is_that_root():
    sub = ancestral_net(burglary(), {"Burglary"})
    assert sub.structure.nodes == ("Burglary",) and sub.structure.edges == ()


def test_ancestral_net_of_several_nodes_takes_the_union():
    sub = ancestral_net(sprinkler(), {"Sprinkler", "Rain"})
    assert sub.structure.nodes == ("Cloudy", "Sprinkler", "Rain")


def test_ancestral_net_of_everything_is_the_same_net():
    net = sprinkler()
    assert ancestral_net(net, frozenset(net.structure.nodes)) == net


def test_ancestral_net_is_itself_a_valid_net():
    sub = ancestral_net(burglary(), {"MaryCalls"})
    assert bayes_net(sub.structure, sub.cpts) == sub


def test_ancestral_net_does_not_change_the_original_net():
    net = burglary()
    before = (net.structure, {k: dict(v) for k, v in net.cpts.items()})
    sub = ancestral_net(net, {"Alarm"})
    sub.cpts["Alarm"][(True, True)] = Fr(1, 7)
    assert (net.structure, net.cpts) == before


@pytest.mark.parametrize("bad", [["Alarm"], "Alarm", {1}, None])
def test_ancestral_net_nodes_must_be_a_set_of_str(bad):
    with pytest.raises(TypeError):
        ancestral_net(burglary(), bad)


def test_ancestral_net_unknown_node_and_non_net():
    with pytest.raises(MissingNodeError):
        ancestral_net(burglary(), {"Nope"})
    with pytest.raises(TypeError):
        ancestral_net("net", {"x"})


def test_marginal_of_a_leaf_is_the_same_in_the_small_net_and_the_full_net():
    net = burglary()
    full = marginals(joint_belief(net)).value
    for node in BURGLARY_NODES:
        small = marginals(joint_belief(ancestral_net(net, {node}))).value
        assert small[node] == full[node], node


@settings(max_examples=60)
@given(random_nets(max_nodes=5))
def test_ancestral_marginals_agree_with_the_full_joint_for_random_dags(spec):
    nodes, edges, cpts = spec
    net = make_net(nodes, edges, cpts)
    full = marginals(joint_belief(net)).value
    for node in nodes:
        sub = ancestral_net(net, {node})
        assert set(sub.structure.nodes) == {node} | ancestors(net, node)
        assert marginals(joint_belief(sub)).value[node] == full[node]


@settings(max_examples=40)
@given(random_nets(max_nodes=5))
def test_ancestors_match_a_naive_transitive_closure(spec):
    nodes, edges, cpts = spec
    net = make_net(nodes, edges, cpts)
    parents = {n: {p for p, c in edges if c == n} for n in nodes}
    for n in nodes:
        seen, todo = set(), list(parents[n])
        while todo:
            x = todo.pop()
            if x not in seen:
                seen.add(x)
                todo.extend(parents[x])
        assert ancestors(net, n) == seen
