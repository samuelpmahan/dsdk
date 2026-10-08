"""Test-only helpers: an independent oracle (reference evaluator/parser) and Hypothesis strategies.

Uses ONLY the public dsdk.logic API; the oracle is deliberately naive so it can be trusted by inspection.
"""
import itertools

from hypothesis import strategies as st

from dsdk.logic import And, Const, Formula, Iff, Implies, Not, Or, Var

NAMES = ["a", "b", "c"]
BINARY = {"and": And, "or": Or, "implies": Implies, "iff": Iff}


def formulas(names=NAMES, max_leaves=8):
    """Hypothesis strategy for small formulas over a few variables (keeps 2**n tiny)."""
    leaf = st.sampled_from(names).map(Var) | st.booleans().map(Const)
    return st.recursive(
        leaf,
        lambda c: c.map(Not) | st.builds(And, c, c) | st.builds(Or, c, c) | st.builds(Implies, c, c) | st.builds(Iff, c, c),
        max_leaves=max_leaves,
    )


def ref_vars(f):
    if isinstance(f, Var):
        return {f.name}
    if isinstance(f, Const):
        return set()
    if isinstance(f, Not):
        return ref_vars(f.operand)
    return ref_vars(f.left) | ref_vars(f.right)


def ref_eval(f, env):
    """Naive two-valued oracle."""
    if isinstance(f, Const):
        return f.value
    if isinstance(f, Var):
        return env[f.name]
    if isinstance(f, Not):
        return not ref_eval(f.operand, env)
    l, r = ref_eval(f.left, env), ref_eval(f.right, env)
    if isinstance(f, And):
        return l and r
    if isinstance(f, Or):
        return l or r
    if isinstance(f, Implies):
        return (not l) or r
    assert isinstance(f, Iff)
    return l == r


def ref_assignments(names):
    """All assignments in the contract's order: sorted names, False<True, first name slowest."""
    names = sorted(set(names))
    for combo in itertools.product([False, True], repeat=len(names)):
        yield dict(zip(names, combo))


def ref_models(f, over=None):
    names = sorted(ref_vars(f) if over is None else set(over))
    return [a for a in ref_assignments(names) if ref_eval(f, a)]


def ref_countermodel(premises, conclusion):
    names = set(ref_vars(conclusion))
    for p in premises:
        names |= ref_vars(p)
    for a in ref_assignments(names):
        if all(ref_eval(p, a) for p in premises) and not ref_eval(conclusion, a):
            return a
    return None


def parse(s):
    """Reference parser for the canonical grammar in dsdk.logic.formula (strict: no extra spaces)."""
    pos = 0

    def expect(tok):
        nonlocal pos
        assert s.startswith(tok, pos), f"expected {tok!r} at {pos} in {s!r}"
        pos += len(tok)

    def go():
        nonlocal pos
        if s[pos] == "(":
            pos += 1
            if s[pos] == "~":
                pos += 1
                inner = go()
                expect(")")
                return Not(inner)
            left = go()
            expect(" ")
            for tok, cls in (("<->", Iff), ("->", Implies), ("&", And), ("|", Or)):
                if s.startswith(tok, pos):
                    pos += len(tok)
                    break
            else:
                raise AssertionError(f"no operator at {pos} in {s!r}")
            expect(" ")
            right = go()
            expect(")")
            return cls(left, right)
        start = pos
        while pos < len(s) and (s[pos].isalnum() or s[pos] == "_"):
            pos += 1
        word = s[start:pos]
        assert word, f"expected atom at {start} in {s!r}"
        return Const(True) if word == "true" else Const(False) if word == "false" else Var(word)

    out = go()
    assert pos == len(s), f"trailing text in {s!r}"
    return out


def decode(d):
    """JSON structure (fixtures) -> Formula."""
    op = d["op"]
    if op == "const":
        return Const(d["value"])
    if op == "var":
        return Var(d["name"])
    if op == "not":
        return Not(decode(d["operand"]))
    return BINARY[op](decode(d["left"]), decode(d["right"]))


def not_chain(n, base):
    f = base
    for _ in range(n):
        f = Not(f)
    return f


def left_chain(cls, n, leaf):
    """cls(cls(cls(leaf, leaf), leaf), leaf)... with n applications (depth n)."""
    f = leaf
    for _ in range(n):
        f = cls(f, leaf)
    return f


def right_chain(cls, n, leaf):
    f = leaf
    for _ in range(n):
        f = cls(leaf, f)
    return f
