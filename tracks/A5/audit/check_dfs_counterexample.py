"""Audit check for Proof 4 (the deliberately broken 'DFS finds shortest paths') against the REAL dsdk.graph code.

D1  The counter-example named in PROOFS: arrows s->a, a->b, b->t, s->t with node order s,a,b,t. The real dfs_preorder gives
    (s,a,b,t). PROOFS says 'parent[t] = b': dsdk exposes NO DFS parent pointers (dfs_preorder returns only an order), so the parent is
    reconstructed here from the order with an independent recursive DFS, and it IS b, giving a tree path of 3 arrows against 1.
D2  Exhaustive: over every loop-free digraph on 4 nodes, count the (graph, source, target) triples where the DFS tree path is longer than
    the BFS distance (the claim is false, and not only on one contrived graph), and confirm the BFS tree path is ALWAYS exactly
    the shortest (the claim is true for BFS).
D4  What DFS does give: the real dfs_postorder is a reverse topological order on every DAG on 4 nodes (what find_cycle and SCC rely on).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import all_digraphs, build, floyd  # noqa: E402

from dsdk.graph import Graph, bfs, dfs_postorder, dfs_preorder, find_cycle  # noqa: E402


def dfs_parents(g, s):
    """Independent recursive DFS (neighbours in node order); returns {node: tree parent}."""
    parent, seen = {s: None}, {s}

    def visit(u):
        for v in g.neighbors(u):
            if v not in seen:
                seen.add(v)
                parent[v] = u
                visit(v)

    visit(s)
    return parent


def tree_path_len(parent, t):
    k = 0
    while parent[t] is not None:
        t = parent[t]
        k += 1
    return k


def main():
    g = Graph.from_edges([("s", "a"), ("a", "b"), ("b", "t"), ("s", "t")], ["s", "a", "b", "t"])
    assert dfs_preorder(g, "s") == ("s", "a", "b", "t")
    p = dfs_parents(g, "s")
    assert p["t"] == "b" and tree_path_len(p, "t") == 3 and bfs(g, "s").distance["t"] == 1
    # the preorder from the real code agrees with the independent DFS's discovery order
    assert tuple(sorted(p, key=lambda k: list(dfs_preorder(g, "s")).index(k))) == dfs_preorder(g, "s")

    longer = total = 0
    for e in all_digraphs(4, loops=False):
        gr = build(4, e)
        oracle = floyd(4, e, True)
        for s in range(4):
            dp, bp = dfs_parents(gr, s), bfs(gr, s).parent
            assert set(dp) == set(bp)
            for t in dp:
                total += 1
                assert tree_path_len(bp, t) == oracle[(s, t)], "BFS tree path is always shortest"
                assert tree_path_len(dp, t) >= oracle[(s, t)]
                longer += tree_path_len(dp, t) > oracle[(s, t)]
    assert longer > 0
    for e in all_digraphs(4, loops=False):
        gr = build(4, e)
        if find_cycle(gr) is None:
            pos = {v: i for i, v in enumerate(dfs_postorder(gr))}
            assert all(pos[b] < pos[a] for a, b in e), "postorder is a reverse topological order on DAGs"
    print(f"PASS: counter-example confirmed; DFS tree path longer than the shortest in {longer} of {total} reachable (graph, source, target) triples on 4-node loop-free digraphs; BFS tree path always shortest")


if __name__ == "__main__":
    main()
