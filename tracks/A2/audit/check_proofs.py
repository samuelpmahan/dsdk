"""Mechanical checks of tracks/A2/PROOFS.md claims over ENUMERATED small Calc terms (auditor W, not F).

Run: .venv/bin/python tracks/A2/audit/check_proofs.py [max_size]    (default 6; about a minute)

Terms: every Expr up to ``max_size`` nodes over atoms IntLit 0, IntLit 1, BoolLit True/False, Var x, Var y, with all 7
binary operators, Not, If, and Let (binder x or y). Typing environments: all four assignments of {Int, Bool} to (x, y)
for open terms, and the empty environment for closed terms. Checked, per PROOFS.md claim:

  C1 Preservation (Proof 1, 2): typed e (any env) and e -> e'  =>  e' typed with the SAME type under that env.
  C2 Progress (Proof 3): closed typed e is a value or steps.
  C3 Size decrease (Proof 4): e -> e'  =>  size(e') < size(e), for ALL e (ill-typed and open included).
  C4 Step bound: len(trace(e)) - 1 <= size(e) - 1.
  C5 Lemma S: size(e[x:=v]) == size(e) for literal v.
  C6 Type safety corollary: closed typed e: trace ends in a value of the static type; a stuck term is ill-typed.
  C7 Substitution lemma: Gamma[x:=T1] |- e : T and |- v : T1  =>  Gamma |- e[x:=v] : T.
  C8 The call-by-name size-growth example in Proof 4 (9 -> 11), and that the real semantics does NOT grow.
  C9 A2 discards the right operand unexamined (ill-typed r), and the term is still ill-typed overall.
  C10 Canonical forms: a closed typed value of type Int is an IntLit, of type Bool a BoolLit.
"""
import itertools
import sys
from collections import Counter

from dsdk.core import Status
from dsdk.lang.calc import (
    BinOp, BoolLit, If, IntLit, Let, Not, OPS, Outcome, Type, Var, classify, is_value, parse_calc, size, step,
    substitute, trace, typecheck,
)

MAX = int(sys.argv[1]) if len(sys.argv) > 1 else 6
ATOMS = [IntLit(0), IntLit(1), BoolLit(True), BoolLit(False), Var("x"), Var("y")]
by_size = {1: list(ATOMS)}
for n in range(2, MAX + 1):
    out = []
    for e in by_size[n - 1]:
        out.append(Not(e))
    for a in range(1, n - 1):
        b = n - 1 - a
        for l in by_size[a]:
            for r in by_size[b]:
                for op in OPS:
                    out.append(BinOp(op, l, r))
                for name in ("x", "y"):
                    out.append(Let(name, l, r))
    for a in range(1, n - 2):
        for b in range(1, n - 1 - a):
            c = n - 1 - a - b
            if c < 1:
                continue
            for k in by_size[a]:
                for t in by_size[b]:
                    for f in by_size[c]:
                        out.append(If(k, t, f))
    by_size[n] = out
TERMS = [e for n in sorted(by_size) for e in by_size[n]]
ENVS = [dict(zip("xy", ts)) for ts in itertools.product((Type.INT, Type.BOOL), repeat=2)]


def ty(e, env):
    j = typecheck(e, env)
    return j.value if j.status is Status.KNOWN else None


stats = Counter()
bad = []


def fail(claim, e, why=""):
    bad.append((claim, e, why))


for e in TERMS:
    s = step(e)
    # C3 / C4 on every term
    if s is not None:
        stats["C3 steps"] += 1
        if not size(s) < size(e):
            fail("C3", e, f"{e} -> {s}")
    tr = trace(e)
    if not len(tr) - 1 <= size(e) - 1:
        fail("C4", e)
    stats["C4 traces"] += 1
    # C1 under every env, open terms included
    for env in ENVS:
        t = ty(e, env)
        if t is None:
            continue
        stats["C1 typed (term, env)"] += 1
        if s is not None:
            stats["C1 typed steps"] += 1
            t2 = ty(s, env)
            if t2 != t:
                fail("C1", e, f"env {env}: {t} -> {t2} via {s}")
    # closed terms
    t0 = ty(e, {})
    if t0 is not None:
        stats["C2 closed typed"] += 1
        if is_value(e):
            want = IntLit if t0 is Type.INT else BoolLit
            stats["C10 typed values"] += 1
            if not isinstance(e, want):
                fail("C10", e)
        elif s is None:
            fail("C2", e, "closed typed term neither value nor step")
        end = tr[-1]
        if not (is_value(end) and ty(end, {}) == t0):
            fail("C6", e, f"trace ends in {end}")
    else:
        pass
    if classify(e) is Outcome.STUCK:
        stats["C6 stuck terms"] += 1
        if ty(e, {}) is not None and not e.__class__ is Var:
            fail("C6", e, "stuck but typed")
    # C5 / C7
    for v in (IntLit(0), IntLit(1), BoolLit(True)):
        sub = substitute(e, "x", v)
        stats["C5 substitutions"] += 1
        if size(sub) != size(e):
            fail("C5", e, f"{v}")
        for env in ENVS:
            tv = Type.INT if isinstance(v, IntLit) else Type.BOOL
            if env["x"] is tv:
                t = ty(e, env)
                if t is not None:
                    stats["C7 typed substitutions"] += 1
                    env2 = {k: val for k, val in env.items() if k != "x"}
                    if ty(sub, env2) != t:
                        # y may still be free; the lemma keeps y's binding
                        fail("C7", e, f"env {env} v={v}")

# C8 call-by-name growth example
cbn = parse_calc("let x = (1 + 1) in ((x * x) * x)")
red_cbn = parse_calc("(((1 + 1) * (1 + 1)) * (1 + 1))")
stats["C8 example"] = 1
if (size(cbn), size(red_cbn)) != (9, 11):
    fail("C8", cbn, f"sizes {(size(cbn), size(red_cbn))}")
real = trace(cbn)
if any(size(a) <= size(b) for a, b in zip(real, real[1:])):
    fail("C8", cbn, "real semantics grew")
# C9 A2 discards r
e9 = parse_calc("false and (1 + true)")
if step(e9) != BoolLit(False) or typecheck(e9).status is Status.KNOWN:
    fail("C9", e9)

print(f"terms enumerated: {len(TERMS)} (max size {MAX}); " + "; ".join(f"{k}={v}" for k, v in sorted(stats.items())))
if bad:
    for claim, e, why in bad[:20]:
        print("COUNTEREXAMPLE", claim, repr(e)[:120], why)
    print(f"{len(bad)} counterexamples")
    sys.exit(1)
print("all claims C1-C10 hold on every enumerated term")
