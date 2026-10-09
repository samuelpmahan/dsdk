"""Audit check for Proof 3 (relabelling) on the REAL Graph.relabel and bfs, exhaustively on small graphs.

For every directed graph on <=3 nodes (self-loops included) and every undirected graph on <=4 nodes, and EVERY permutation of the
names (a relabel keeping each node at its position):
  R1  BFS distances correspond:    dist'(pi(s), pi(v)) == dist(s, v) and the same nodes are unreachable
  R2  the whole BFS run corresponds (distance, parent, order), i.e. the proof's stronger remark that a position-preserving relabel
      also preserves parents, discovery order and witnesses
  R3  shortest_path witnesses correspond for every (s, t)
Then the claims about what is NOT invariant:
  R4  the diamond a->b, a->c, b->d, c->d: swapping the NAMES b and c with Graph.relabel keeps the witness (a,b,d) -> (a,c,d) as the
      image of the old one (so a pure relabel does not "move the witness"), while REORDERING the node list does move it
      (this is the operation the proof means by "a renaming that reorders nodes"; the wording of the proof is ambiguous)
  R5  relabel is only INJECTIVE on the nodes in the code (it raises GraphError otherwise, MissingNodeError for a missing key);
      the proof says "bijection V -> V'" which is the same thing onto the image.
"""
import itertools
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import all_digraphs, all_undirected, build  # noqa: E402

from dsdk.graph import Graph, GraphError, MissingNodeError, bfs, shortest_path  # noqa: E402


def check(n, edges, directed):
    g = build(n, edges, directed)
    for perm in itertools.permutations(range(n)):
        m = {i: 10 + perm[i] for i in range(n)}
        h = g.relabel(m)
        for s in range(n):
            a, b = bfs(g, s), bfs(h, m[s])
            assert b.distance == {m[k]: v for k, v in a.distance.items()}, ("R1", edges, perm)
            assert b.parent == {m[k]: (None if v is None else m[v]) for k, v in a.parent.items()}, ("R2 parent", edges, perm)
            assert b.order == tuple(m[x] for x in a.order), ("R2 order", edges, perm)
            for t in range(n):
                p, q = shortest_path(g, s, t), shortest_path(h, m[s], m[t])
                assert (p is None) == (q is None) and (p is None or q == tuple(m[x] for x in p)), ("R3", edges, perm)


def main():
    count = 0
    for n in (1, 2, 3):
        for e in all_digraphs(n):
            check(n, e, True); count += 1
    for n in (1, 2, 3, 4):
        for e in all_undirected(n):
            check(n, e, False); count += 1
    diamond = [("a", "b"), ("a", "c"), ("b", "d"), ("c", "d")]
    g = Graph.from_edges(diamond, list("abcd"))
    swapped_names = g.relabel({"a": "a", "b": "c", "c": "b", "d": "d"})
    assert shortest_path(g, "a", "d") == ("a", "b", "d")
    assert shortest_path(swapped_names, "a", "d") == ("a", "c", "d"), "image of the old witness under the renaming"
    reordered = Graph.from_edges(diamond, list("acbd"))
    assert shortest_path(reordered, "a", "d") == ("a", "c", "d"), "reordering the node list changes which witness is reported"
    assert shortest_path(reordered, "a", "d") != tuple({"a": "a", "b": "b", "c": "c", "d": "d"}[x] for x in shortest_path(g, "a", "d"))
    for bad, exc in (({"a": 1, "b": 1, "c": 2, "d": 3}, GraphError), ({"a": 1, "b": 2, "c": 3}, MissingNodeError)):
        try:
            g.relabel(bad)
        except exc:
            pass
        else:
            raise AssertionError(bad)
    print(f"PASS: {count} graphs x all permutations x all sources; diamond example and error cases confirmed")


if __name__ == "__main__":
    main()
