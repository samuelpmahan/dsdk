"""Audit check for Proof 1 (BFS): run the REAL dsdk.graph.bfs unmodified under a tracer, snapshot `queue`, `distance`, `parent`,
`order` every time the `while queue:` test is reached, and assert the invariants the proof relies on, on ALL small graphs.

Exhaustive: every directed graph on <=3 nodes with self-loops (512), every loop-free directed graph on 4 nodes (4096), every
undirected graph on <=4 nodes with self-loops (1024), every source. Plus 1500 random directed graphs on 5 nodes.

Asserted at every loop test (front d = distance of the queue front):
  B1  the queue's distances are non-decreasing                                    (the proof's Lemma B, first half)
  B2  every queue entry has distance d or d+1                                      (what the proof's induction step really uses)
  B3  the weaker wording of Lemma B ("consecutive entries differ by at most 1") also holds
  L1  every assigned node's distance equals the independent Floyd-Warshall distance (stronger than Lemma A's ">=")
  L2  every node whose true distance is <= d is already assigned                   (the layer invariant: layers fill in order)
  L3  nodes in `order` (dequeued) all have distance <= d
At the end: distance == oracle for exactly the reachable nodes; parent chain has length dist and every parent arrow exists;
tie-break claim: parent[v] is the FIRST dequeued in-neighbour of v (which is also a shallowest one).
Also records whether the weaker wording B3 is strictly weaker than B2 (a queue like [0,1,2] satisfies B3, not B2).
"""
import inspect
import random
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import all_digraphs, all_undirected, arrows, build, floyd, trace_loop_states  # noqa: E402

import dsdk.graph.traverse as traverse  # noqa: E402

src, start = inspect.getsourcelines(traverse.bfs)
TEST_LINE = next(start + i for i, l in enumerate(src) if re.match(r"\s+while queue:", l))


def check(n, edges, directed, s, fn=None, line=None):
    g = build(n, edges, directed)
    res, snaps = trace_loop_states(fn or traverse.bfs, (g, s), "bfs", line or TEST_LINE)
    oracle = floyd(n, edges, directed)
    true = {j: d for (i, j), d in oracle.items() if i == s}
    assert snaps, "the loop test must be reached at least once"
    for sn in snaps:
        q, dist, order = sn["queue"], sn["distance"], sn["order"]
        if q:
            ds = [dist[x] for x in q]
            d = ds[0]
            assert ds == sorted(ds), ("B1", edges, s, ds)
            assert all(x in (d, d + 1) for x in ds), ("B2", edges, s, ds)
            assert all(b - a <= 1 for a, b in zip(ds, ds[1:])), ("B3", edges, s, ds)
            assert all(dist[v] <= d for v in order), ("L3", edges, s)
            assert all(v in dist for v, tv in true.items() if tv <= d), ("L2", edges, s, d)
        for v, dv in dist.items():
            assert true.get(v) == dv, ("L1", edges, s, v)
    assert res.distance == true, ("final distance", edges, s)
    assert set(res.parent) == set(true)
    pos = {v: i for i, v in enumerate(res.order)}
    arr = arrows(edges, directed)
    for v, p in res.parent.items():
        if v == s:
            assert p is None
            continue
        assert (p, v) in arr and res.distance[p] + 1 == res.distance[v], ("parent arrow", edges, s, v)
        inn = [u for u in res.order if (u, v) in arr and u in pos]
        assert p == inn[0], ("parent is first dequeued in-neighbour", edges, s, v)
        shallow = [u for u in inn if res.distance[u] == res.distance[v] - 1]
        assert p == shallow[0]
    return len(snaps)


def selftest():
    """The checker must not be vacuous: a BFS that uses a stack (pop instead of popleft) has to be rejected."""
    text = inspect.getsource(traverse.bfs).replace("queue.popleft()", "queue.pop()")
    ns = dict(vars(traverse))
    exec(compile(text, "<mutant>", "exec"), ns)
    line = next(i + 1 for i, l in enumerate(text.split("\n")) if re.match(r"\s+while queue:", l))
    caught = 0
    for e in all_digraphs(4, loops=False):
        for s in range(4):
            try:
                check(4, e, True, s, ns["bfs"], line)
            except AssertionError:
                caught += 1
    assert caught > 0
    return caught


def main():
    print("selftest: the stack-based mutant is rejected on", selftest(), "of 16384 (graph, source) runs")
    graphs = states = 0
    for n in (1, 2, 3):
        for e in all_digraphs(n):
            for s in range(n):
                states += check(n, e, True, s); graphs += 1
    for e in all_digraphs(4, loops=False):
        for s in range(4):
            states += check(4, e, True, s); graphs += 1
    for n in (1, 2, 3, 4):
        for e in all_undirected(n):
            for s in range(n):
                states += check(n, e, False, s); graphs += 1
    rng = random.Random(0)
    pairs = [(i, j) for i in range(5) for j in range(5)]
    for _ in range(1500):
        e = [p for p in pairs if rng.random() < 0.25]
        states += check(5, e, True, rng.randrange(5)); graphs += 1
    # the weaker wording of Lemma B is strictly weaker: [0,1,2] passes it and fails the needed property
    q = [0, 1, 2]
    assert all(b - a <= 1 for a, b in zip(q, q[1:])) and not all(x in (q[0], q[0] + 1) for x in q)
    print(f"PASS: {graphs} (graph, source) runs, {states} traced loop-test states")


if __name__ == "__main__":
    main()
