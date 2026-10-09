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

Added for AUDIT-2 (the rewritten PROOFS.md):
  C11 Proof 2A: preservation holds for EVERY rule, with the rule that fired found by an independent classifier (``leaf_rule``) that
      follows congruence steps down to the computation rule; every rule must be exercised, or the check fails as vacuous.
  C12 Canonical forms under ARBITRARY environments: ``Gamma |- v : Int`` for a value v implies IntLit, in all 4 environments.
  C13 Substitution lemma, both ``let`` sub-cases: shadowing (binder == substituted name) and non-shadowing, each exercised, with the
      bound term ALWAYS substituted into (checked against ``substitute``) and the Exchange identities on environments.
  C14 Proof 3: progress for every typing-rule family (7 binary operators, not, if, let), each exercised on closed typed terms.
  C15 The broken-proof counterexamples: ``if true then 1 else (1 + true)``, ``false and (1 + true)`` are ill-typed and NOT stuck;
      ``let x = (1 + true) in 5`` is ill-typed and stuck; all three are in fixtures/lang/calc_programs.json.
"""
import itertools
import json
import sys
from collections import Counter
from pathlib import Path

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

# ------------------------------------------------------------------ AUDIT-2 additions
def leaf_rule(e):
    """The computation rule that finally fires for the step of ``e`` (following congruence into the child), by shape only."""
    if isinstance(e, BinOp):
        if e.op in ("and", "or"):
            if not is_value(e.left):
                return leaf_rule(e.left)
            if not isinstance(e.left, BoolLit):
                return None
            return {("and", False): "A2", ("and", True): "A3", ("or", True): "O2", ("or", False): "O3"}[(e.op, e.left.value)]
        if not is_value(e.left):
            return leaf_rule(e.left)
        if not is_value(e.right):
            return leaf_rule(e.right)
        l, r = e.left, e.right
        ok = (isinstance(l, IntLit) and isinstance(r, IntLit)) or (e.op == "==" and isinstance(l, BoolLit) and isinstance(r, BoolLit))
        return f"B3 {e.op}" if ok else None
    if isinstance(e, Not):
        return leaf_rule(e.operand) if not is_value(e.operand) else ("N" if isinstance(e.operand, BoolLit) else None)
    if isinstance(e, If):
        if not is_value(e.cond):
            return leaf_rule(e.cond)
        return ("I-true" if e.cond.value else "I-false") if isinstance(e.cond, BoolLit) else None
    if isinstance(e, Let):
        return leaf_rule(e.bound) if not is_value(e.bound) else "L"
    return None


EXPECTED_RULES = {"B3 +", "B3 -", "B3 *", "B3 <", "B3 ==", "A2", "A3", "O2", "O3", "N", "I-true", "I-false", "L"}
by_rule, families, shadow, noshadow = Counter(), Counter(), 0, 0
from dsdk.lang.calc import Let as _Let


def family(e):
    return e.op if isinstance(e, BinOp) else type(e).__name__


for e in TERMS:
    s_ = step(e)
    if s_ is not None:
        rule = leaf_rule(e)
        if rule is None:
            fail("C11", e, "step exists but the independent classifier finds no rule")
        for env in ENVS:
            t = ty(e, env)
            if t is not None:
                by_rule[rule] += 1
                if ty(s_, env) != t:
                    fail("C11", e, f"rule {rule}, env {env}")
    if is_value(e):
        for env in ENVS:
            t = ty(e, env)
            if t is not None and (isinstance(e, IntLit) != (t is Type.INT)):
                fail("C12", e, f"env {env}")
    t0 = ty(e, {})
    if t0 is not None and not isinstance(e, (IntLit, BoolLit, Var)):
        families[family(e)] += 1
        if not is_value(e) and step(e) is None:
            fail("C14", e)
    if isinstance(e, _Let):
        for v in (IntLit(0), BoolLit(True)):
            sub = substitute(e, "x", v)
            if not (isinstance(sub, _Let) and sub.bound == substitute(e.bound, "x", v)):
                fail("C13", e, "bound term not always substituted")
            if e.name == "x":
                ok_body = sub.body == e.body
            else:
                ok_body = sub.body == substitute(e.body, "x", v)
            if not ok_body:
                fail("C13", e, "body rule")
            for env in ENVS:
                tv = Type.INT if isinstance(v, IntLit) else Type.BOOL
                if env["x"] is tv and ty(e, env) is not None:
                    if e.name == "x":
                        shadow += 1
                    else:
                        noshadow += 1
                    if ty(sub, {k: val for k, val in env.items() if k != "x"}) != ty(e, env):
                        fail("C13", e, f"typing, env {env}")
missing = EXPECTED_RULES - set(by_rule)
if missing:
    fail("C11", None, f"rules never exercised (vacuous): {sorted(missing)}")
need_fams = {"+", "-", "*", "<", "==", "and", "or", "Not", "If", "Let"}
if need_fams - set(families):
    fail("C14", None, f"families never exercised: {sorted(need_fams - set(families))}")
if not (shadow and noshadow):
    fail("C13", None, f"shadow={shadow} noshadow={noshadow}")
for a, b, c in itertools.product((Type.INT, Type.BOOL), repeat=3):  # exchange identities on environments
    g = {"x": a, "y": b}
    assert {**{**g, "x": c}, "x": a} == {**g, "x": a} and {**{**g, "x": c}, "y": b} == {**{**g, "y": b}, "x": c}
fx = json.loads((Path(__file__).resolve().parents[3] / "fixtures/lang/calc_programs.json").read_text())
fx_text = json.dumps(fx)
for src, stuck in (("if true then 1 else (1 + true)", False), ("false and (1 + true)", False), ("let x = (1 + true) in 5", True)):
    e = parse_calc(src)
    if typecheck(e).status is Status.KNOWN or (classify(trace(e)[-1]) is Outcome.STUCK) != stuck:
        fail("C15", e, src)
    if src not in fx_text:
        fail("C15", e, f"{src!r} not in fixtures/lang/calc_programs.json")
stats.update({f"C11 steps for rule {k}": v for k, v in sorted(by_rule.items(), key=lambda kv: str(kv[0]))})
stats["C13 typed lets, shadowing / not"] = f"{shadow} / {noshadow}"
stats.update({f"C14 closed typed {k}": v for k, v in sorted(families.items())})

print(f"terms enumerated: {len(TERMS)} (max size {MAX}); " + "; ".join(f"{k}={v}" for k, v in sorted(stats.items())))
if bad:
    for claim, e, why in bad[:20]:
        print("COUNTEREXAMPLE", claim, repr(e)[:120], why)
    print(f"{len(bad)} counterexamples")
    sys.exit(1)
print("all claims C1-C15 hold on every enumerated term")
