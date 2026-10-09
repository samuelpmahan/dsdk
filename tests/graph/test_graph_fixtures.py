"""Fixture-driven tests: fixtures/graph/graphs.json is the language-neutral oracle shared with the JS port.

The fixtures were produced by an independent script (recursive DFS, brute-force path enumeration) -- not by dsdk --
so a disagreement means the implementation (or the fixture) is wrong; never "fix" a fixture to match the code
without re-deriving the expected value by hand.
"""
import json
from pathlib import Path

import pytest

from dsdk.core import Status
from dsdk.graph import (
    CycleError, Edge, Graph, GraphError, MissingNodeError, bfs, components, dfs_postorder, dfs_preorder, find_cycle,
    reachable, shortest_path, strongly_connected_components, topological_order,
)

DOC = json.loads((Path(__file__).resolve().parents[2] / "fixtures" / "graph" / "graphs.json").read_text("utf-8"))
CASES = DOC["cases"]
IDS = [c["name"] for c in CASES]
PLAIN = [c for c in CASES if not c["reachability"]]
EVIDENCE = [c for c in CASES if c["reachability"]]


def build(case, with_dangling=False):
    """Graph from a fixture case; edges may be [u, v] or [u, v, evidence]."""
    edges = list(case["edges"]) + (list(case["dangling_edges"]) if with_dangling else [])
    items = [Edge(e[0], e[1], evidence=Status(e[2]) if len(e) > 2 else Status.KNOWN) for e in edges]
    return Graph.from_edges(items, case["nodes"], directed=case["directed"], closed_world=case["closed_world"])


def test_fixture_file_covers_the_promised_shapes():
    """The fixture set must contain every required shape, and building each case must succeed (broken fixtures fail loudly)."""
    assert len(CASES) >= 8 and len(set(IDS)) == len(IDS)
    needed = {"curriculum_8", "triangle_tail_undirected", "four_cycle_directed", "dag_many_orders", "disconnected_undirected"}
    assert needed <= set(IDS)
    assert len(next(c for c in CASES if c["name"] == "curriculum_8")["nodes"]) == 8
    for c in CASES:
        assert build(c).nodes == tuple(c["nodes"])


@pytest.mark.parametrize("case", CASES, ids=IDS)
def test_fixture_views(case):
    """Adjacency lists and the adjacency matrix equal the fixture (node-ordered neighbours, 0/1 matrix)."""
    g = build(case)
    assert {n: list(v) for n, v in g.adjacency().items()} == case["adjacency"]
    assert [list(r) for r in g.adjacency_matrix()] == case["adjacency_matrix"]


@pytest.mark.parametrize("case", CASES, ids=IDS)
def test_fixture_bfs_from_every_source(case):
    """BFS distances, parent pointers and discovery order from every node match the independent oracle."""
    g = build(case)
    for source, expected in case["bfs"].items():
        r = bfs(g, source)
        assert r.distance == expected["distance"], f"distances from {source}"
        assert r.parent == expected["parent"], f"parents from {source}"
        assert list(r.order) == expected["order"], f"discovery order from {source}"


@pytest.mark.parametrize("case", CASES, ids=IDS)
def test_fixture_shortest_path_witnesses_for_every_pair(case):
    """The exact witness (tie-break included) for all ordered pairs; None where unreachable."""
    g = build(case)
    for row in case["shortest_paths"]:
        got = shortest_path(g, row["source"], row["target"])
        want = row["path"]
        assert (None if got is None else list(got)) == want, f"{row['source']} -> {row['target']}"


@pytest.mark.parametrize("case", CASES, ids=IDS)
def test_fixture_dfs_orders(case):
    """Whole-graph and rooted DFS pre/post orders follow the recursive definition."""
    g = build(case)
    assert list(dfs_preorder(g)) == case["dfs_preorder"]
    assert list(dfs_postorder(g)) == case["dfs_postorder"]
    first = case["nodes"][0]
    assert list(dfs_preorder(g, first)) == case["dfs_from_first_node"]["preorder"]
    assert list(dfs_postorder(g, first)) == case["dfs_from_first_node"]["postorder"]


@pytest.mark.parametrize("case", CASES, ids=IDS)
def test_fixture_cycle_verdict_and_exact_witness(case):
    """find_cycle returns the first back edge in DFS order, or None; the verdict flag agrees."""
    cyc = find_cycle(build(case))
    assert (cyc is not None) == case["has_cycle"]
    assert (None if cyc is None else list(cyc)) == case["cycle"]


@pytest.mark.parametrize("case", CASES, ids=IDS)
def test_fixture_topological_order_or_error(case):
    """Kahn's order (smallest index first), a CycleError with the witness, or GraphError for undirected graphs."""
    g = build(case)
    expected = case["topological"]
    if "order" in expected:
        assert list(topological_order(g)) == expected["order"]
    elif expected["error"] == "cycle":
        with pytest.raises(CycleError) as info:
            topological_order(g)
        assert list(info.value.cycle) == expected["cycle"]
    else:
        assert expected["error"] == "undirected"
        with pytest.raises(GraphError) as info:
            topological_order(g)
        assert not isinstance(info.value, CycleError), "an undirected graph is a usage error, not a cycle"


@pytest.mark.parametrize("case", CASES, ids=IDS)
def test_fixture_components_and_sccs(case):
    """Weak components and SCCs in canonical form."""
    g = build(case)
    assert [list(c) for c in components(g)] == case["components"]
    assert [list(c) for c in strongly_connected_components(g)] == case["sccs"]


def test_curriculum_graph_dangling_reference_is_a_missing_node_error():
    """The 'missing reference' of the curriculum graph: E->Z with Z undeclared must raise, and name Z."""
    case = next(c for c in CASES if c["name"] == "curriculum_8")
    assert case["dangling_edges"] == [["E", "Z"]]
    with pytest.raises(MissingNodeError, match="Z"):
        build(case, with_dangling=True)
    declared = Graph.from_edges(
        [Edge(e[0], e[1]) for e in case["edges"] + case["dangling_edges"]], case["nodes"] + ["Z"])
    assert declared.has_edge("E", "Z") and len(declared.nodes) == 9


@pytest.mark.parametrize("case", EVIDENCE, ids=[c["name"] for c in EVIDENCE])
def test_fixture_reachability_judgments(case):
    """Every (source, target) Judgment -- status, value and exact reason -- including a missing source node."""
    assert case["reachability"], "evidence cases must carry expectations"
    g = build(case)
    for row in case["reachability"]:
        j = reachable(g, row["source"], row["target"])
        assert (j.status.value, j.value, j.reason) == (row["status"], row["value"], row["reason"]), \
            f"reachable({row['source']!r}, {row['target']!r}) in {case['name']}"
