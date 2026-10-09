"""Contract tests for dsdk.graph.evidence: reachability as a Judgment ("a missing edge is not proof")."""
import pytest
from hypothesis import given
from hypothesis import strategies as st

from dsdk.core import Judgment, Status
from dsdk.graph import Edge, Graph, MissingNodeError, candidate_path, known_subgraph, reachable

from graph_oracles import evidence_edge_lists, fw_distances, merged_evidence

K, U, N = Status.KNOWN, Status.UNKNOWN, Status.NOT_OBSERVED


def build(edges, nodes=None, directed=True, closed_world=False):
    return Graph.from_edges(edges, nodes, directed=directed, closed_world=closed_world)


def ev(u, v, status):
    return Edge(u, v, evidence=status)


# ================================================================================ known_subgraph
def test_known_subgraph_keeps_nodes_flags_and_only_known_edges():
    """Isolated nodes and flags survive; UNKNOWN and NOT_OBSERVED edges are dropped."""
    g = build([ev("a", "b", K), ev("b", "c", U), ev("c", "d", N)], ["a", "b", "c", "d", "z"], closed_world=True)
    k = known_subgraph(g)
    assert k.nodes == g.nodes and k.closed_world is True and k.directed is True
    assert [(e.source, e.target) for e in k.edges] == [("a", "b")]


# ==================================================================================== reachable
def test_known_path_gives_known_true_with_the_path_in_the_reason():
    """A path of KNOWN edges proves reachability: KNOWN True, and the reason shows the witness."""
    j = reachable(build([ev("a", "b", K), ev("b", "c", K)]), "a", "c")
    assert j == Judgment(Status.KNOWN, True, "known path: a -> b -> c")


def test_source_equals_target_is_known_true_even_in_an_empty_world():
    """The empty path always exists, with no edges at all (and the reason has a single node)."""
    j = reachable(build([], ["a"]), "a", "a")
    assert j == Judgment(Status.KNOWN, True, "known path: a")


def test_unknown_edge_on_the_only_path_makes_the_answer_unknown_not_false():
    """The curriculum lesson: an inferred edge on the only route means 'maybe', never 'no' and never 'yes'."""
    g = build([ev("a", "b", K), ev("b", "c", U)])
    j = reachable(g, "a", "c")
    assert j.status is Status.UNKNOWN and j.value is None
    assert j.reason == "uncertain edges on best candidate path: b->c (unknown)"


def test_reason_lists_every_uncertain_edge_in_path_order_with_its_status():
    """The reason names each uncertain edge on the best candidate path, in walking order, with its evidence."""
    g = build([ev("a", "b", N), ev("b", "c", K), ev("c", "d", U)])
    assert reachable(g, "a", "d").reason == \
        "uncertain edges on best candidate path: a->b (not_observed), c->d (unknown)"


def test_known_path_wins_over_a_shorter_uncertain_shortcut():
    """A known detour proves reachability even if a shorter uncertain edge exists: KNOWN True via the known path."""
    g = build([ev("a", "z", U), ev("a", "b", K), ev("b", "z", K)], ["a", "b", "z"])
    assert reachable(g, "a", "z") == Judgment(Status.KNOWN, True, "known path: a -> b -> z")


def test_candidate_path_with_equal_uncertainty_prefers_fewer_hops():
    """Both routes have exactly one uncertain edge, so the shorter route a->z is the best candidate."""
    g = build([ev("a", "z", U), ev("a", "b", K), ev("b", "c", K), ev("c", "z", N)], ["a", "b", "c", "z"])
    assert reachable(g, "a", "z").reason == "uncertain edges on best candidate path: a->z (unknown)"


def test_candidate_path_prefers_fewer_uncertain_edges_over_fewer_hops():
    """2 hops with 2 uncertain edges loses to 3 hops with 1 uncertain edge: uncertainty is compared first."""
    g = build([ev("a", "b", U), ev("b", "z", U), ev("a", "c", K), ev("c", "d", K), ev("d", "z", N)],
              ["a", "b", "c", "d", "z"])
    assert candidate_path(g, "a", "z") == ("a", "c", "d", "z")
    assert reachable(g, "a", "z").reason == "uncertain edges on best candidate path: d->z (not_observed)"


def test_open_world_without_any_path_is_unknown():
    """No path even counting uncertain edges, but the world is open: absence of evidence is not evidence of absence."""
    j = reachable(build([ev("a", "b", K)], ["a", "b", "c"]), "a", "c")
    assert j == Judgment(Status.UNKNOWN, None,
                         "open world: no path found, but absence of an edge is not proof of impossibility")


def test_closed_world_without_any_path_is_known_false():
    """Only a closed world may conclude impossibility."""
    g = build([ev("a", "b", K)], ["a", "b", "c"], closed_world=True)
    assert reachable(g, "a", "c") == Judgment(
        Status.KNOWN, False, "closed world: no path from a to c even counting uncertain edges")


def test_closed_world_with_an_uncertain_path_is_still_unknown():
    """Closing the world does not turn an uncertain edge into a known one: KNOWN False needs NO path at all."""
    g = build([ev("a", "b", U)], closed_world=True)
    assert reachable(g, "a", "b").status is Status.UNKNOWN


def test_known_false_value_is_the_boolean_false_not_none():
    """KNOWN False carries the value False (a legitimate known value), distinguishing it from UNKNOWN's None."""
    j = reachable(build([], ["a", "b"], closed_world=True), "a", "b")
    assert j.status is Status.KNOWN and j.value is False


def test_direction_matters_for_reachability():
    """a->b known does not give b->a: directed graph, reverse query is open-world unknown (or closed-world False)."""
    edges = [ev("a", "b", K)]
    assert reachable(build(edges), "b", "a").status is Status.UNKNOWN
    assert reachable(build(edges, closed_world=True), "b", "a").value is False
    assert reachable(build(edges, directed=False), "b", "a") == Judgment(Status.KNOWN, True, "known path: b -> a")


def test_undirected_uncertain_edge_is_reported_in_the_walking_direction():
    """The reason shows the direction the path walks the edge, not the storage orientation."""
    g = build([ev("a", "b", U)], ["a", "b"], directed=False)
    assert reachable(g, "b", "a").reason == "uncertain edges on best candidate path: b->a (unknown)"


def test_missing_nodes_give_an_invalid_judgment_not_an_exception():
    """Asking about a node the graph lacks is an ill-posed question: INVALID with the node named."""
    g = build([ev("a", "b", K)])
    j = reachable(g, "a", "ghost")
    assert j.status is Status.INVALID and j.value is None and "'ghost'" in j.reason
    assert reachable(g, "ghost", "a").status is Status.INVALID
    assert "'nope'" in reachable(g, "nope", "ghost").reason, "if both are missing the SOURCE is named"


def test_self_loop_does_not_create_reachability_between_different_nodes():
    """A known self-loop at a does not connect a to b."""
    g = build([ev("a", "a", K)], ["a", "b"], closed_world=True)
    assert reachable(g, "a", "b").value is False


def test_reachable_on_a_2000_node_known_chain_and_an_uncertain_last_edge():
    """No recursion limit and no quadratic blow-up on long chains, for both the known and the candidate search."""
    n = 2000
    chain = [ev(i, i + 1, K) for i in range(n - 1)]
    assert reachable(build(chain, list(range(n))), 0, n - 1).status is Status.KNOWN
    broken = chain[:-1] + [ev(n - 2, n - 1, U)]
    j = reachable(build(broken, list(range(n))), 0, n - 1)
    assert j.reason == f"uncertain edges on best candidate path: {n - 2}->{n - 1} (unknown)"


# ================================================================================= candidate_path
def test_candidate_path_tie_break_is_lexicographic_on_node_order():
    """Equal uncertainty and hops: the path with the smaller index sequence wins (b before c)."""
    g = build([ev("a", "b", U), ev("a", "c", U), ev("b", "d", K), ev("c", "d", K)], ["a", "b", "c", "d"])
    assert candidate_path(g, "a", "d") == ("a", "b", "d")
    g2 = build([ev("a", "b", U), ev("a", "c", U), ev("b", "d", K), ev("c", "d", K)], ["a", "c", "b", "d"])
    assert candidate_path(g2, "a", "d") == ("a", "c", "d")


def test_candidate_path_trivial_none_and_missing():
    """s == t is (s,); disconnected is None; missing nodes raise MissingNodeError."""
    g = build([ev("a", "b", K)], ["a", "b", "c"])
    assert candidate_path(g, "a", "a") == ("a",)
    assert candidate_path(g, "a", "c") is None
    with pytest.raises(MissingNodeError):
        candidate_path(g, "a", "ghost")
    with pytest.raises(MissingNodeError):
        candidate_path(g, "ghost", "a")


@given(evidence_edge_lists(), st.booleans(), st.data())
def test_reachable_agrees_with_independent_oracles_for_every_status_and_world(case, directed, data):
    """Property: the verdict equals the decision table computed from Floyd-Warshall on (known edges) / (all edges)."""
    nodes, edges = case
    closed = data.draw(st.booleans())
    s, t = data.draw(st.sampled_from(nodes)), data.draw(st.sampled_from(nodes))
    g = build([Edge(u, v, evidence=e) for u, v, e in edges], nodes, directed, closed)
    known_pairs = [(u, v) for u, v, e in edges if e is K]
    all_pairs = [(u, v) for u, v, e in edges]
    known_reach = (s, t) in fw_distances(nodes, known_pairs, directed)
    any_reach = (s, t) in fw_distances(nodes, all_pairs, directed)
    j = reachable(g, s, t)
    if known_reach:
        assert (j.status, j.value) == (Status.KNOWN, True), "a path of KNOWN edges proves reachability"
    elif any_reach:
        assert (j.status, j.value) == (Status.UNKNOWN, None), "only uncertain paths: must be UNKNOWN even if closed"
        assert j.reason.startswith("uncertain edges on best candidate path: ")
    elif closed:
        assert (j.status, j.value) == (Status.KNOWN, False), "closed world and no path at all: known unreachable"
    else:
        assert (j.status, j.value) == (Status.UNKNOWN, None), "open world: absence of an edge proves nothing"


@given(evidence_edge_lists(), st.booleans(), st.data())
def test_candidate_path_is_a_valid_path_with_minimal_uncertainty_then_hops(case, directed, data):
    """Property: candidate_path is a real path, and no path has fewer uncertain edges (or, equal, fewer hops)."""
    nodes, edges = case
    s, t = data.draw(st.sampled_from(nodes)), data.draw(st.sampled_from(nodes))
    g = build([Edge(u, v, evidence=e) for u, v, e in edges], nodes, directed)
    strength = merged_evidence(edges, directed)

    def key(u, v):
        return (u, v) if directed else frozenset((u, v))

    path = candidate_path(g, s, t)
    all_pairs = [(u, v) for u, v, _ in edges]
    if (s, t) not in fw_distances(nodes, all_pairs, directed):
        assert path is None
        return
    assert path[0] == s and path[-1] == t and len(set(path)) == len(path), "simple path from s to t"
    assert all(key(u, v) in strength for u, v in zip(path, path[1:])), "every step is an edge"
    cost = lambda p: (sum(strength[key(u, v)] is not K for u, v in zip(p, p[1:])), len(p) - 1)
    # brute-force all simple paths (<= 6 nodes) for the true optimum
    best = min(cost(p) for p in _simple_paths(nodes, strength, directed, s, t))
    assert cost(path) == best, f"{path} costs {cost(path)} but the optimum is {best}"


def _simple_paths(nodes, strength, directed, s, t):
    def key(u, v):
        return (u, v) if directed else frozenset((u, v))
    stack = [[s]]
    while stack:
        p = stack.pop()
        if p[-1] == t:
            yield tuple(p)
            continue
        for v in nodes:
            if v not in p and key(p[-1], v) in strength:
                stack.append(p + [v])
