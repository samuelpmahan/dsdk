"""Contract tests for dsdk.graph.traverse: BFS, shortest paths, DFS, cycles, topological order, components, SCC."""
import pytest
from hypothesis import given
from hypothesis import strategies as st

from dsdk.graph import (
    CycleError, Graph, GraphError, MissingNodeError, bfs, components, dfs_postorder, dfs_preorder, find_cycle,
    shortest_path, strongly_connected_components, topological_order,
)

from graph_oracles import (
    dag_edge_lists, edge_lists, fw_distances, has_cycle_oracle, is_cycle_witness, is_walk, scc_oracle,
    connected_components_oracle,
)


def build(edges, nodes=None, directed=True):
    return Graph.from_edges(edges, nodes, directed=directed)


def path_graph(n, directed=True):
    return build([(i, i + 1) for i in range(n - 1)], list(range(n)), directed)


DIAMOND = [("a", "b"), ("a", "c"), ("b", "d"), ("c", "d")]
DIAMOND_NODES = ["a", "b", "c", "d"]


# ======================================================================================== BFS
def test_bfs_distances_parents_and_order_on_a_diamond():
    """BFS gives hop counts; the parent is the earliest-dequeued shallowest in-neighbour (here b, not c)."""
    r = bfs(build(DIAMOND, DIAMOND_NODES), "a")
    assert r.source == "a"
    assert r.distance == {"a": 0, "b": 1, "c": 1, "d": 2}
    assert r.parent == {"a": None, "b": "a", "c": "a", "d": "b"}, "d is first discovered from b (b dequeued before c)"
    assert r.order == ("a", "b", "c", "d")


def test_bfs_unreachable_nodes_are_absent_not_infinite():
    """Unreachable nodes must not appear in distance/parent/order (absence is the signal)."""
    r = bfs(build([("a", "b")], ["a", "b", "z"]), "a")
    assert "z" not in r.distance and "z" not in r.parent and "z" not in r.order


def test_bfs_from_an_isolated_source():
    """An isolated source reaches only itself, at distance 0 and with parent None."""
    r = bfs(build([("a", "b")], ["a", "b", "iso"]), "iso")
    assert r.distance == {"iso": 0} and r.parent == {"iso": None} and r.order == ("iso",)


def test_bfs_ignores_self_loops_and_duplicate_edges():
    """A self-loop or repeated edge must not change distances or create a self-parent."""
    plain = bfs(build([("a", "b"), ("b", "c")]), "a")
    noisy = bfs(build([("a", "b"), ("b", "c"), ("a", "a"), ("b", "b"), ("a", "b"), ("a", "b")]), "a")
    assert plain.distance == noisy.distance and plain.parent == noisy.parent


def test_bfs_directed_follows_arrows_undirected_does_not():
    """Direction matters: from c the path a->b->c is unreachable if directed, distance 2 if undirected."""
    edges = [("a", "b"), ("b", "c")]
    assert bfs(build(edges), "c").distance == {"c": 0}
    assert bfs(build(edges, directed=False), "c").distance == {"c": 0, "b": 1, "a": 2}


def test_bfs_missing_source_raises():
    """BFS from a node the graph does not have is a contract violation."""
    with pytest.raises(MissingNodeError):
        bfs(build([("a", "b")]), "nope")


def test_bfs_on_a_2000_node_path_needs_no_recursion():
    """Algorithms must be iterative: a 2,000-node path exceeds Python's default recursion limit of 1000."""
    r = bfs(path_graph(2000), 0)
    assert r.distance[1999] == 1999 and len(r.order) == 2000


def test_bfs_distances_are_unchanged_by_relabelling_a_fixed_example():
    """Graph isomorphism invariance: renaming nodes renames the distances and parents and changes nothing else."""
    g = build(DIAMOND + [("d", "e")], DIAMOND_NODES + ["e", "iso"])
    m = {"a": 10, "b": 11, "c": 12, "d": 13, "e": 14, "iso": 15}
    r, rr = bfs(g, "a"), bfs(g.relabel(m), 10)
    assert rr.distance == {m[k]: v for k, v in r.distance.items()}
    assert rr.parent == {m[k]: (None if p is None else m[p]) for k, p in r.parent.items()}
    assert rr.order == tuple(m[k] for k in r.order)


@given(edge_lists(), st.booleans(), st.data())
def test_bfs_distances_are_invariant_under_relabelling(case, directed, data):
    """Property: for any permutation of names, dist'(pi(s), pi(v)) == dist(s, v). This is the invariance proved in PROOFS."""
    nodes, edges = case
    g = build(edges, nodes, directed)
    perm = data.draw(st.permutations(list(range(len(nodes)))))
    mapping = {n: 100 + perm[n] for n in nodes}
    s = data.draw(st.sampled_from(nodes))
    original = bfs(g, s).distance
    renamed = bfs(g.relabel(mapping), mapping[s]).distance
    assert renamed == {mapping[k]: v for k, v in original.items()}


@given(edge_lists(), st.booleans(), st.data())
def test_bfs_matches_floyd_warshall_and_witness_length_equals_distance(case, directed, data):
    """BFS distance == length of the shortest_path witness == the Floyd-Warshall oracle; every witness edge exists."""
    nodes, edges = case
    g = build(edges, nodes, directed)
    s = data.draw(st.sampled_from(nodes))
    t = data.draw(st.sampled_from(nodes))
    oracle = fw_distances(nodes, edges, directed)
    dist = bfs(g, s).distance
    assert dist == {b: d for (a, b), d in oracle.items() if a == s}, "BFS must equal the independent oracle"
    path = shortest_path(g, s, t)
    if t not in dist:
        assert path is None, "unreachable target must give None"
    else:
        assert path[0] == s and path[-1] == t
        assert len(path) - 1 == dist[t], "witness length must equal the BFS distance"
        assert all(g.has_edge(a, b) for a, b in zip(path, path[1:])), "every witness edge must exist in the graph"
        assert is_walk(path, edges, directed)


# ============================================================================== shortest_path
def test_shortest_path_tie_break_uses_node_order():
    """On a diamond the witness goes through b (earlier in node order), deterministically."""
    assert shortest_path(build(DIAMOND, DIAMOND_NODES), "a", "d") == ("a", "b", "d")
    swapped = build(DIAMOND, ["a", "c", "b", "d"])
    assert shortest_path(swapped, "a", "d") == ("a", "c", "d"), "changing node order changes the tie-break"


def test_shortest_path_source_equals_target_is_the_trivial_path():
    """s == t gives (s,) -- even when s has a self-loop (a self-loop is never a shorter path)."""
    assert shortest_path(build([("a", "a")]), "a", "a") == ("a",)
    assert shortest_path(build([("a", "b")]), "b", "b") == ("b",)


def test_shortest_path_to_an_isolated_node_is_none():
    """No edges reach the isolated node, so there is no witness."""
    assert shortest_path(build([("a", "b")], ["a", "b", "z"]), "a", "z") is None


def test_shortest_path_from_an_isolated_source_to_itself():
    """An isolated node still reaches itself by the empty walk."""
    assert shortest_path(build([], ["z"]), "z", "z") == ("z",)


def test_shortest_path_missing_target_raises_and_missing_source_raises():
    """A target (or source) that is not in the graph is an error, NOT 'unreachable'."""
    g = build([("a", "b")])
    with pytest.raises(MissingNodeError):
        shortest_path(g, "a", "ghost")
    with pytest.raises(MissingNodeError):
        shortest_path(g, "ghost", "a")


def test_shortest_path_asymmetry_between_directed_and_undirected():
    """Reverse direction: no path in the directed graph, a path in the undirected one."""
    edges = [("a", "b"), ("b", "c")]
    assert shortest_path(build(edges), "c", "a") is None
    assert shortest_path(build(edges, directed=False), "c", "a") == ("c", "b", "a")


def test_shortest_path_prefers_fewer_hops_over_earlier_nodes():
    """A 1-hop edge beats a 2-hop route through earlier-ordered nodes."""
    g = build([("a", "b"), ("b", "z"), ("a", "z")], ["a", "b", "z"])
    assert shortest_path(g, "a", "z") == ("a", "z")


def test_shortest_path_on_a_2000_node_path():
    """The witness for the far end of a 2,000-node path has 2,000 nodes and no recursion error."""
    assert shortest_path(path_graph(2000), 0, 1999) == tuple(range(2000))


# ============================================================================================ DFS
def test_dfs_preorder_follows_the_recursive_definition():
    """a->b, a->c, b->d: recursive DFS gives a, b, d, c. (Pushing all neighbours on a stack gives a, c, b, d: wrong.)"""
    g = build([("a", "b"), ("a", "c"), ("b", "d")], ["a", "b", "c", "d"])
    assert dfs_preorder(g, "a") == ("a", "b", "d", "c")


def test_dfs_postorder_follows_the_recursive_definition():
    """Postorder appends a node after all its children: d, b, c, a."""
    g = build([("a", "b"), ("a", "c"), ("b", "d")], ["a", "b", "c", "d"])
    assert dfs_postorder(g, "a") == ("d", "b", "c", "a")


def test_dfs_with_source_visits_only_what_is_reachable():
    """A rooted DFS must not wander to unreachable nodes."""
    g = build([("a", "b")], ["a", "b", "z"])
    assert dfs_preorder(g, "a") == ("a", "b")


def test_dfs_without_source_covers_every_node_once_roots_in_node_order():
    """source=None restarts from the next unmarked node, so isolated nodes and other components are included."""
    g = build([("b", "c")], ["a", "b", "c", "d"])
    assert dfs_preorder(g) == ("a", "b", "c", "d") and sorted(dfs_postorder(g)) == ["a", "b", "c", "d"]


def test_dfs_handles_cycles_without_repeating_nodes():
    """Marked nodes are never revisited, so a cycle terminates."""
    g = build([("a", "b"), ("b", "a"), ("b", "b")])
    assert dfs_preorder(g, "a") == ("a", "b")


def test_dfs_missing_source_raises():
    """A bad root is a MissingNodeError for both orders."""
    g = build([("a", "b")])
    with pytest.raises(MissingNodeError):
        dfs_preorder(g, "ghost")
    with pytest.raises(MissingNodeError):
        dfs_postorder(g, "ghost")


def test_dfs_on_a_2000_node_path_needs_no_recursion():
    """Explicit-stack DFS: pre- and postorder of a 2,000-node path are the path and its reverse."""
    g = path_graph(2000)
    assert dfs_preorder(g, 0) == tuple(range(2000))
    assert dfs_postorder(g, 0) == tuple(reversed(range(2000)))


def test_dfs_does_not_find_shortest_paths():
    """Counter-example to the false claim 'DFS finds shortest paths' (see PROOFS): DFS reaches d via the long route."""
    g = build([("s", "a"), ("a", "b"), ("b", "t"), ("s", "t")], ["s", "a", "b", "t"])
    order = dfs_preorder(g, "s")
    assert order == ("s", "a", "b", "t"), "DFS dives down a-b before it ever tries the direct edge s->t"
    assert shortest_path(g, "s", "t") == ("s", "t")


# ====================================================================================== find_cycle
def test_find_cycle_none_on_a_dag_including_cross_edges():
    """A diamond has two paths to d but no cycle; a finished node reached again is NOT a back edge."""
    assert find_cycle(build(DIAMOND, DIAMOND_NODES)) is None


def test_find_cycle_none_on_empty_and_single_node_graphs():
    """Boundary cases: nothing to find."""
    assert find_cycle(build([])) is None and find_cycle(build([], ["a"])) is None


def test_find_cycle_directed_self_loop():
    """A self-loop is a cycle of length 1, reported as (u, u)."""
    assert find_cycle(build([("a", "b"), ("b", "b")])) == ("b", "b")


def test_find_cycle_exact_witness_on_a_three_cycle_with_a_tail():
    """The witness starts at the first node of the cycle reached by DFS and closes on itself."""
    g = build([("t", "a"), ("a", "b"), ("b", "c"), ("c", "a")], ["t", "a", "b", "c"])
    assert find_cycle(g) == ("a", "b", "c", "a")


def test_find_cycle_reports_the_first_back_edge_in_dfs_order():
    """Two cycles: the DFS from a meets the back edge b->a first (via a, b) before c->b is ever scanned."""
    g = build([("a", "b"), ("b", "a"), ("b", "c"), ("c", "b")], ["a", "b", "c"])
    assert find_cycle(g) == ("a", "b", "a")


def test_find_cycle_two_cycle_directed_is_a_cycle_but_undirected_edge_is_not():
    """a<->b is a directed cycle; the single undirected edge a-b is just an edge (it would reuse itself)."""
    assert find_cycle(build([("a", "b"), ("b", "a")])) == ("a", "b", "a")
    assert find_cycle(build([("a", "b")], directed=False)) is None
    assert find_cycle(build([("a", "b"), ("b", "a")], directed=False)) is None, "duplicates merged: still one edge"


def test_find_cycle_undirected_triangle_and_self_loop():
    """Undirected: a triangle is a cycle (exact witness), and so is a self-loop."""
    tri = build([("a", "b"), ("b", "c"), ("c", "a")], ["a", "b", "c"], directed=False)
    assert find_cycle(tri) == ("a", "b", "c", "a")
    assert find_cycle(build([("a", "a")], directed=False)) == ("a", "a")


def test_find_cycle_undirected_tree_has_none():
    """A tree (any orientation of edge listing) is acyclic."""
    assert find_cycle(build([("a", "b"), ("c", "b"), ("b", "d")], directed=False)) is None


def test_find_cycle_on_a_2000_node_cycle():
    """A single 2,000-cycle is found without recursion; the witness has 2,001 entries."""
    n = 2000
    g = build([(i, (i + 1) % n) for i in range(n)], list(range(n)))
    assert find_cycle(g) == tuple(range(n)) + (0,)


@given(edge_lists(), st.booleans())
def test_find_cycle_verdict_matches_oracle_and_witness_is_valid(case, directed):
    """Verdict == independent oracle; a returned cycle is closed, simple and made of real edges."""
    nodes, edges = case
    cyc = find_cycle(build(edges, nodes, directed))
    assert (cyc is not None) == has_cycle_oracle(nodes, edges, directed), "cycle verdict disagrees with the oracle"
    if cyc is not None:
        assert is_cycle_witness(cyc, edges, directed), f"{cyc} is not a valid cycle witness"


# ============================================================================= topological_order
def test_topological_order_uses_smallest_index_first_tie_break():
    """c->a, c->b with node order a,b,c: c is the only ready node, then a before b."""
    assert topological_order(build([("c", "a"), ("c", "b")], ["a", "b", "c"])) == ("c", "a", "b")


def test_topological_order_picks_the_smallest_ready_node_each_time():
    """Several valid orders exist; Kahn with a min-index choice yields exactly this one."""
    g = build([("a", "c"), ("b", "c"), ("c", "d"), ("b", "e"), ("e", "d")], ["a", "b", "c", "d", "e", "f"])
    assert topological_order(g) == ("a", "b", "c", "e", "d", "f"), "min-index Kahn: a, b, then c(2) beats e(4) and f(5); then e(4) beats f(5); d(3) beats f(5); f last"


def test_topological_order_includes_isolated_nodes_and_empty_graph():
    """Isolated nodes appear exactly once; the empty graph gives ()."""
    assert topological_order(build([])) == ()
    assert topological_order(build([("b", "c")], ["a", "b", "c", "d"])) == ("a", "b", "c", "d")


def test_topological_order_with_duplicate_edges_counts_each_dependency_once():
    """Duplicate edges are merged, so indegree is not inflated and the sink is still emitted."""
    assert topological_order(build([("a", "b"), ("a", "b")])) == ("a", "b")


def test_topological_order_cycle_raises_with_a_real_witness():
    """A cyclic graph raises CycleError whose .cycle is a genuine cycle of the graph (the proof of failure)."""
    edges = [("t", "a"), ("a", "b"), ("b", "a"), ("b", "c")]
    with pytest.raises(CycleError) as info:
        topological_order(build(edges, ["t", "a", "b", "c"]))
    cyc = info.value.cycle
    assert cyc == ("a", "b", "a")
    assert is_cycle_witness(cyc, edges, True)
    assert isinstance(info.value, GraphError)


def test_topological_order_self_loop_is_a_cycle_error():
    """A self-loop keeps its node's indegree above zero forever, so Kahn stalls and reports (u, u)."""
    with pytest.raises(CycleError) as info:
        topological_order(build([("a", "b"), ("b", "b")]))
    assert info.value.cycle == ("b", "b")


def test_topological_order_rejects_undirected_graphs():
    """An undirected graph has no edge directions to order; GraphError (even for a tree, even if empty-edged)."""
    with pytest.raises(GraphError):
        topological_order(build([("a", "b")], directed=False))
    with pytest.raises(GraphError):
        topological_order(build([], ["a"], directed=False))


def test_topological_order_on_a_2000_node_path():
    """Kahn is iterative by nature; a 2,000-node chain must come out in chain order."""
    assert topological_order(path_graph(2000)) == tuple(range(2000))


@given(dag_edge_lists())
def test_topological_order_respects_every_edge_on_random_dags(case):
    """Property: the order is a permutation of the nodes and every edge u->v has u before v."""
    nodes, edges = case
    order = topological_order(build(edges, nodes))
    assert sorted(order) == nodes, "every node exactly once"
    pos = {n: i for i, n in enumerate(order)}
    for u, v in edges:
        assert pos[u] < pos[v], f"edge {u}->{v} is violated by the order {order}"


@given(dag_edge_lists())
def test_topological_order_is_the_lexicographically_smallest_in_node_order(case):
    """Tie-break property: among ready nodes the smallest index is always emitted (greedy-min is checked by replay)."""
    nodes, edges = case
    order = topological_order(build(edges, nodes))
    remaining_edges = set(edges)
    emitted = set()
    for n in order:
        ready = [m for m in nodes if m not in emitted and not any(v == m and u not in emitted for u, v in remaining_edges)]
        assert n == min(ready), f"at this step {min(ready)} was ready but {n} was emitted"
        emitted.add(n)


@given(edge_lists(), st.booleans())
def test_topological_order_raises_exactly_when_a_cycle_exists(case, directed):
    """For directed graphs CycleError <=> oracle says cyclic; the witness is valid. Undirected: always GraphError."""
    nodes, edges = case
    g = build(edges, nodes, directed)
    if not directed:
        with pytest.raises(GraphError):
            topological_order(g)
        return
    cyclic = has_cycle_oracle(nodes, edges, True)
    if cyclic:
        with pytest.raises(CycleError) as info:
            topological_order(g)
        assert is_cycle_witness(info.value.cycle, edges, True)
    else:
        assert len(topological_order(g)) == len(nodes)


# ===================================================================================== components
def test_components_directed_ignores_direction():
    """Weak connectivity: a->b and c->b land in one component even though a cannot reach c."""
    g = build([("a", "b"), ("c", "b")], ["a", "b", "c", "d"])
    assert components(g) == (("a", "b", "c"), ("d",))


def test_components_canonical_order_follows_node_order():
    """Output is canonical: nodes inside a component and components themselves are in node order."""
    g = build([("z", "y"), ("b", "a")], ["z", "b", "y", "a"], directed=False)
    assert components(g) == (("z", "y"), ("b", "a"))


def test_components_isolated_nodes_and_empty_graph():
    """Isolated nodes are singleton components; the empty graph has none."""
    assert components(build([], ["a", "b"])) == (("a",), ("b",))
    assert components(build([])) == ()


def test_components_on_a_2000_node_path():
    """A long path is one component (no recursion)."""
    assert components(path_graph(2000, directed=False)) == (tuple(range(2000)),)


@given(edge_lists(), st.booleans())
def test_components_match_union_find_oracle_and_partition_the_nodes(case, directed):
    """Property: components are a partition of the nodes equal to the independent union-find answer."""
    nodes, edges = case
    result = components(build(edges, nodes, directed))
    assert {frozenset(c) for c in result} == connected_components_oracle(nodes, edges, directed)
    assert sorted(n for c in result for n in c) == nodes, "partition: every node exactly once"
    assert [c[0] for c in result] == sorted(c[0] for c in result), "components ordered by first node"


# ================================================================================================ SCC
def test_scc_cycle_with_tail_and_dag_parts():
    """a->b->c->a is one SCC; the tail d (c->d) and the isolated e are their own."""
    g = build([("a", "b"), ("b", "c"), ("c", "a"), ("c", "d")], ["a", "b", "c", "d", "e"])
    assert strongly_connected_components(g) == (("a", "b", "c"), ("d",), ("e",))


def test_scc_one_way_edge_between_two_cycles_does_not_merge_them():
    """Mutual reachability is required: a<->b and c<->d joined by b->c stay separate."""
    g = build([("a", "b"), ("b", "a"), ("c", "d"), ("d", "c"), ("b", "c")], ["a", "b", "c", "d"])
    assert strongly_connected_components(g) == (("a", "b"), ("c", "d"))


def test_scc_self_loop_does_not_merge_anything():
    """A self-loop node stays a singleton SCC."""
    assert strongly_connected_components(build([("a", "a"), ("a", "b")])) == (("a",), ("b",))


def test_scc_on_a_dag_is_all_singletons_in_node_order():
    """Acyclic graph: every node is its own component, listed in node order."""
    assert strongly_connected_components(build(DIAMOND, DIAMOND_NODES)) == (("a",), ("b",), ("c",), ("d",))


def test_scc_undirected_equals_components_and_empty_graph():
    """For undirected graphs SCC == components; the empty graph gives ()."""
    g = build([("a", "b")], ["a", "b", "c"], directed=False)
    assert strongly_connected_components(g) == components(g) == (("a", "b"), ("c",))
    assert strongly_connected_components(build([])) == ()


def test_scc_on_a_2000_node_cycle_and_a_2000_node_path():
    """Iterative SCC: a 2,000-cycle is one component, a 2,000-path is 2,000 singletons."""
    n = 2000
    cyc = build([(i, (i + 1) % n) for i in range(n)], list(range(n)))
    assert strongly_connected_components(cyc) == (tuple(range(n)),)
    assert len(strongly_connected_components(path_graph(n))) == n


@given(edge_lists(), st.booleans())
def test_scc_matches_mutual_reachability_oracle(case, directed):
    """Property: SCCs equal the classes of 'a reaches b and b reaches a' computed by Floyd-Warshall."""
    nodes, edges = case
    result = strongly_connected_components(build(edges, nodes, directed))
    expected = scc_oracle(nodes, edges) if directed else connected_components_oracle(nodes, edges, False)
    assert {frozenset(c) for c in result} == expected
    assert sorted(n for c in result for n in c) == nodes
