"""Audit check for Proof 2 (Kahn): run the REAL dsdk.graph.topological_order unmodified under a tracer and snapshot `order`,
`indegree` and `ready` at every `while ready:` test, on EVERY directed graph on <=3 nodes with self-loops and EVERY directed
graph on 4 nodes with self-loops (65536). Asserts the four invariant clauses of the proof, the termination measure, the exit
claims, and the one thing the proof does not cover: that `find_cycle` supplies a real cycle exactly when Kahn comes up short.

  I1  `order` has no repeated node
  I2  for every position i, all predecessors of order[i] sit at positions < i
  I3  indegree[v] == number of predecessors of v that are not in `order`
  I4  `ready` (a heap of node indices) is exactly { v not in order : indegree[v] == 0 }, with no duplicates
  M   |V| - |order| decreases by exactly 1 per iteration; number of loop tests = |order at exit| + 1
Exit: |order| == |V| iff the graph is acyclic (independent test: no node reaches itself in the transitive closure);
      otherwise CycleError is raised and its witness is a closed walk of real arrows (first == last), of length >= 1 arrow.
Gap check: whenever Kahn is short, find_cycle(g) is not None (otherwise CycleError(None) would crash while building its message).
"""
import inspect
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import all_digraphs, build, trace_loop_states  # noqa: E402

import dsdk.graph.traverse as traverse  # noqa: E402
from dsdk.graph import CycleError, find_cycle  # noqa: E402

src, start = inspect.getsourcelines(traverse.topological_order)
TEST_LINE = next(start + i for i, l in enumerate(src) if re.match(r"\s+while ready:", l))


def reaches_itself(n, edges):
    """Independent cyclicity test: transitive closure by repeated squaring on a boolean matrix."""
    m = [[False] * n for _ in range(n)]
    for a, b in edges:
        m[a][b] = True
    for k in range(n):
        for i in range(n):
            for j in range(n):
                if m[i][k] and m[k][j]:
                    m[i][j] = True
    return any(m[i][i] for i in range(n))


def run(n, edges, fn=None, line=None):
    g = build(n, edges)
    preds = {v: {a for a, b in edges if b == v} for v in range(n)}
    outcome = {}

    def call(g):
        try:
            outcome["order"] = (fn or traverse.topological_order)(g)
        except CycleError as exc:
            outcome["cycle"] = exc.cycle
        return None

    _, snaps = trace_loop_states(call, (g,), "topological_order", line or TEST_LINE)
    for k, sn in enumerate(snaps):
        order, ind, ready = sn["order"], sn["indegree"], sn["ready"]
        assert len(set(order)) == len(order), ("I1", edges)
        where = {v: i for i, v in enumerate(order)}
        for i, v in enumerate(order):
            assert all(where.get(p, 10 ** 9) < i for p in preds[v]), ("I2", edges, order)
        for v in range(n):
            assert ind[v] == len([p for p in preds[v] if p not in where]), ("I3", edges, v)
        idx = sorted(ready)
        assert idx == sorted(set(idx)), ("I4 duplicates", edges)
        assert set(idx) == {v for v in range(n) if v not in where and ind[v] == 0}, ("I4", edges)
        assert len(order) == k, ("M: one node per iteration", edges)
    final = len(snaps) - 1
    acyclic = not reaches_itself(n, edges)
    if acyclic:
        assert "order" in outcome and sorted(outcome["order"]) == list(range(n)), ("acyclic must emit all", edges)
        pos = {v: i for i, v in enumerate(outcome["order"])}
        assert all(pos[a] < pos[b] for a, b in edges), ("topological property", edges)
        assert final == n
    else:
        assert "cycle" in outcome, ("cyclic must raise", edges)
        w = outcome["cycle"]
        assert w is not None and len(w) >= 2 and w[0] == w[-1] and all((a, b) in set(edges) for a, b in zip(w, w[1:])), ("witness", edges, w)
        assert final < n
    assert (find_cycle(g) is not None) == (not acyclic), ("find_cycle agrees with the independent test", edges)
    return len(snaps)


def selftest():
    """Non-vacuity: a Kahn that forgets to count self-loops (skips decrement bookkeeping wrongly) must be rejected."""
    text = inspect.getsource(traverse.topological_order).replace("indegree[succ] -= 1", "indegree[succ] -= 2")
    ns = dict(vars(traverse))
    exec(compile(text, "<mutant>", "exec"), ns)
    line = next(i + 1 for i, l in enumerate(text.split("\n")) if re.match(r"\s+while ready:", l))
    caught = 0
    for e in all_digraphs(3):
        try:
            run(3, e, ns["topological_order"], line)
        except (AssertionError, TypeError):  # TypeError: CycleError(None) -- find_cycle found nothing for a wrongly 'cyclic' graph
            caught += 1
    assert caught > 0
    return caught


def main():
    print("selftest: the double-decrement mutant is rejected on", selftest(), "of 512 graphs")
    graphs = states = 0
    for n in (1, 2, 3, 4):
        for e in all_digraphs(n):
            states += run(n, e); graphs += 1
    print(f"PASS: {graphs} directed graphs (n<=4, self-loops included), {states} traced loop-test states")


if __name__ == "__main__":
    main()
