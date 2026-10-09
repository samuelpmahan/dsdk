"""Exhaustive check of mirror∘mirror = id over all shapes with <=6 internal nodes, 2 leaf values, using the real code
plus an independent recursive reference mirror (checks the iterative _fold against the proof's recursive definition)."""
import sys, itertools
sys.path.insert(0, "/home/user/dsdk/src")
from dsdk.logic.structures import Leaf, Node, mirror
def shapes(n):  # n internal nodes; None = leaf slot
    if n == 0: yield "L"; return
    for i in range(n):
        for l in shapes(i):
            for r in shapes(n-1-i): yield (l, r)
def build(s, it):
    return Leaf(next(it)) if s == "L" else Node(build(s[0], it), build(s[1], it))
def ref(t):  # proof's definition, literally recursive
    return t if isinstance(t, Leaf) else Node(ref(t.right), ref(t.left))
count = 0; nontriv = 0
for n in range(7):
    for s in shapes(n):
        nleaves = n+1
        for vals in itertools.product((0, 1), repeat=nleaves):
            t = build(s, iter(vals))
            assert mirror(mirror(t)) == t
            assert mirror(t) == ref(t) and ref(ref(t)) == t
            count += 1; nontriv += (mirror(t) != t)
print(f"PASS: {count} trees (<=6 internal nodes, leaves in {{0,1}}); {nontriv} with mirror(t)!=t")
