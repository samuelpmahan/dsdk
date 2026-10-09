"""Audit-2: execute the REAL dsdk.logic.structures._fold under sys.settrace and check
invariant J (PROOFS.md Lemma F) and the weight measure at the top of EVERY loop test,
for every binary tree with <= 5 internal nodes (distinct leaf labels).

Method: the real function runs unmodified. A line-event hook on the `while work:` line
snapshots the locals `work` and `results`. Leaf/combine are symbolic ('L',label) / ('N',p,q),
so F(x) is computed independently by plain recursion and D(W,R) by the PROOFS definition.
"""
import sys, inspect, itertools
from dsdk.logic import structures as S
from dsdk.logic.structures import Leaf, Node, Tree

CODE = S._fold.__code__
src, first = inspect.getsourcelines(S._fold)
WHILE_LINE = next(first + i for i, l in enumerate(src) if l.strip() == "while work:")

a = lambda leaf: ("L", leaf.value)
c = lambda p, q: ("N", p, q)

def F(x):
    return a(x) if isinstance(x, Leaf) else c(F(x.left), F(x.right))

def size(x):
    return 1 if isinstance(x, Leaf) else 1 + size(x.left) + size(x.right)

def weight(W):
    return sum(2 * size(x) if not e else 1 for x, e in W)

def D(W, R):
    R = list(R)
    for x, e in reversed(W):          # process top (last) first
        if not e:
            R.append(F(x))
        else:
            if len(R) < 2:
                return None           # undefined
            q = R.pop(); p = R.pop(); R.append(c(p, q))
    return R

def check_tree(t):
    snaps = []
    def tracer(frame, event, arg):
        if frame.f_code is not CODE:
            return None
        def local(frame, event, arg):
            if event == "line" and frame.f_lineno == WHILE_LINE:
                snaps.append((list(frame.f_locals["work"]), list(frame.f_locals["results"])))
            return local
        return local
    sys.settrace(tracer)
    try:
        out = S._fold(t, a, c)
    finally:
        sys.settrace(None)
    nodes = sum(1 for _ in nodes_of(t)); leaves = size(t) - nodes
    iters = leaves + 2 * nodes
    assert len(snaps) == iters + 1, (len(snaps), iters)   # one test per iteration + final
    assert out == F(t)
    counts = {"leaf": 0, "expanded": 0, "unexpanded": 0}
    for k, (W, R) in enumerate(snaps):
        for x, e in W:
            assert isinstance(x, Tree)                                # (ii)
            if e: assert isinstance(x, Node)                          # (i)
        d = D(W, R)
        assert d is not None and d == [F(t)], (k, W, R, d)            # (iii)
        if k + 1 < len(snaps):
            W2, R2 = snaps[k + 1]
            cur, e = W[-1]
            if isinstance(cur, Leaf):
                counts["leaf"] += 1
                assert W2 == W[:-1] and R2 == R + [a(cur)]
                assert weight(W) - weight(W2) == 2 * size(cur) == 2
            elif e:
                counts["expanded"] += 1
                assert W2 == W[:-1] and R2 == R[:-2] + [c(R[-2], R[-1])]
                assert weight(W) - weight(W2) == 1
            else:
                counts["unexpanded"] += 1
                assert W2 == W[:-1] + [(cur, True), (cur.right, False), (cur.left, False)] and R2 == R
                assert weight(W) - weight(W2) == 1
            assert weight(W2) < weight(W)                              # strict decrease
            assert weight(W2) >= 0
        else:
            assert W == [] and R == [F(t)]                             # exit
    assert weight(snaps[0][0]) == 2 * size(t)
    return len(snaps), counts

def nodes_of(t):
    st = [t]
    while st:
        x = st.pop()
        if isinstance(x, Node):
            yield x; st += [x.left, x.right]

def shapes(k):                      # all shapes with k internal nodes
    if k == 0:
        yield None; return
    for i in range(k):
        for l in shapes(i):
            for r in shapes(k - 1 - i):
                yield (l, r)

def build(shape, it):
    if shape is None:
        return Leaf(next(it))
    l = build(shape[0], it); r = build(shape[1], it)
    return Node(l, r)

if __name__ == "__main__":
    total = steps = 0
    for k in range(6):
        n = 0
        for sh in shapes(k):
            t = build(sh, itertools.count())
            s, _ = check_tree(t); steps += s; n += 1
        print(f"internal={k}: {n} trees OK"); total += n
    print(f"PASS: {total} trees, {steps} loop-test states; J (i)-(iii) and strict weight decrease hold at every step "
          f"(while-line = source line {WHILE_LINE})")
