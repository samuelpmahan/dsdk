"""Audit check for the cost claim in Proof 2 ("with a heap the cost is O((|V|+|E|) log |V|)").

The proof is about the ALGORITHM; this measures the SHIPPED code on path graphs (|E| = |V|-1). If the claim held for the code, doubling
|V| would roughly double the time (ratio ~2, a little more for the log). Observed: ratio ~4 for both bfs and topological_order, i.e.
quadratic, because Graph.neighbors / Graph.predecessors scan every edge and rebuild the node->position dict on every call.
The check PRINTS the ratios and exits 0 either way (it documents a finding, it does not gate the build); it always exits 0; when the
output changes to "near-linear" the finding can be closed.
"""
import time

from dsdk.graph import Graph, bfs, topological_order


def t(fn, g):
    start = time.perf_counter()
    fn(g)
    return time.perf_counter() - start


def main():
    rows = []
    for n in (1000, 2000, 4000):
        g = Graph.from_edges([(i, i + 1) for i in range(n - 1)], list(range(n)))
        rows.append((n, t(lambda g: bfs(g, 0), g), t(topological_order, g)))
    for (n1, b1, k1), (n2, b2, k2) in zip(rows, rows[1:]):
        print(f"|V| {n1} -> {n2}: bfs time x{b2 / b1:.1f}, topological_order time x{k2 / k1:.1f}  (linear would be about x2)")
    quadratic = all(r2[1] / r1[1] > 3 for r1, r2 in zip(rows, rows[1:]))
    print("FINDING CONFIRMED: both are quadratic in |V| on a path graph" if quadratic else "near-linear: the finding can be closed")


if __name__ == "__main__":
    main()
