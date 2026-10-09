"""Test-only helpers for tests/prob: an independent, deliberately naive oracle and Hypothesis strategies.

The oracle does NOT use dsdk.logic.models / dsdk.prob: it enumerates with itertools and evaluates formulas with its own tiny
evaluator, so a bug shared by the SDK's enumeration and its probability code cannot hide.
"""
import itertools
from fractions import Fraction

from hypothesis import strategies as st

from dsdk import logic
from dsdk.logic import And, Const, Iff, Implies, Not, Or, Var

NAMES = ["a", "b", "c"]
Fr = Fraction


def formulas(names=NAMES, max_leaves=6):
    leaf = st.sampled_from(names).map(Var) | st.booleans().map(Const)
    return st.recursive(
        leaf,
        lambda c: c.map(Not) | st.builds(And, c, c) | st.builds(Or, c, c) | st.builds(Implies, c, c) | st.builds(Iff, c, c),
        max_leaves=max_leaves,
    )


def probs():
    """Probabilities that are exact small fractions (so float conversion by repr never matters)."""
    return st.sampled_from([Fr(0), Fr(1, 10), Fr(1, 5), Fr(1, 4), Fr(1, 3), Fr(1, 2), Fr(2, 3), Fr(3, 4), Fr(9, 10), Fr(1)])


def prior_maps(names=NAMES):
    return st.dictionaries(st.sampled_from(names), probs(), min_size=1, max_size=len(names))


def ref_vars(f):
    if isinstance(f, Var):
        return {f.name}
    if isinstance(f, Const):
        return set()
    if isinstance(f, Not):
        return ref_vars(f.operand)
    return ref_vars(f.left) | ref_vars(f.right)


def ref_eval(f, env):
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
    if isinstance(f, Iff):
        return l == r
    raise AssertionError(f)


def ref_worlds(priors, constraint=None):
    """[(env, weight)] over sorted(priors | constraint variables), False before True, first variable slowest."""
    names = sorted(set(priors) | (ref_vars(constraint) if constraint is not None else set()))
    out = []
    for combo in itertools.product([False, True], repeat=len(names)):
        env = dict(zip(names, combo))
        if constraint is not None and not ref_eval(constraint, env):
            continue
        w = Fr(1)
        for n, p in priors.items():
            w *= p if env[n] else 1 - p
        out.append((env, w))
    return out


def ref_prob(priors, query, given=None, constraint=None):
    """Exact P(query | given) by brute force, or None when the denominator is 0."""
    worlds = ref_worlds(priors, constraint)
    den = sum((w for env, w in worlds if given is None or ref_eval(given, env)), Fr(0))
    if den == 0:
        return None
    num = sum((w for env, w in worlds if ref_eval(query, env) and (given is None or ref_eval(given, env))), Fr(0))
    return num / den


def conj(*fs):
    out = fs[0]
    for f in fs[1:]:
        out = And(out, f)
    return out


def values_of(world):
    return world.values


def total_of(belief):
    return sum((w.weight for w in belief.worlds), Fr(0))
