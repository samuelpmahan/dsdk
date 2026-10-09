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


# ------------------------------------------------------------------ Bayes-net fixtures and oracle
from dsdk.graph import Edge, Graph  # noqa: E402  (kept at the bottom so the helpers above stay importable on their own)
from dsdk.prob import bayes_net  # noqa: E402


def make_net(nodes, edges, cpts):
    """Build a BayesNet through the public constructor. ``nodes`` fixes the graph's node order (hence the CPT parent order)."""
    return bayes_net(Graph.from_edges(edges, nodes, directed=True), cpts)


# Russell & Norvig burglary network. Parents in node order: Alarm has (Burglary, Earthquake).
BURGLARY_NODES = ["Burglary", "Earthquake", "Alarm", "JohnCalls", "MaryCalls"]
BURGLARY_EDGES = [("Burglary", "Alarm"), ("Earthquake", "Alarm"), ("Alarm", "JohnCalls"), ("Alarm", "MaryCalls")]
BURGLARY_CPTS = {
    "Burglary": {(): Fr(1, 1000)},
    "Earthquake": {(): Fr(2, 1000)},
    "Alarm": {(True, True): Fr(95, 100), (True, False): Fr(94, 100), (False, True): Fr(29, 100), (False, False): Fr(1, 1000)},
    "JohnCalls": {(True,): Fr(90, 100), (False,): Fr(5, 100)},
    "MaryCalls": {(True,): Fr(70, 100), (False,): Fr(1, 100)},
}

# Russell & Norvig sprinkler network: Cloudy -> Sprinkler, Cloudy -> Rain, (Sprinkler, Rain) -> WetGrass. Node order matters for CPT keys.
SPRINKLER_NODES = ["Cloudy", "Sprinkler", "Rain", "WetGrass"]
SPRINKLER_EDGES = [("Cloudy", "Sprinkler"), ("Cloudy", "Rain"), ("Sprinkler", "WetGrass"), ("Rain", "WetGrass")]
SPRINKLER_CPTS = {
    "Cloudy": {(): Fr(1, 2)},
    "Sprinkler": {(True,): Fr(1, 10), (False,): Fr(1, 2)},
    "Rain": {(True,): Fr(8, 10), (False,): Fr(2, 10)},
    "WetGrass": {(True, True): Fr(99, 100), (True, False): Fr(9, 10), (False, True): Fr(9, 10), (False, False): Fr(0)},
}


def burglary():
    return make_net(BURGLARY_NODES, BURGLARY_EDGES, BURGLARY_CPTS)


def sprinkler():
    return make_net(SPRINKLER_NODES, SPRINKLER_EDGES, SPRINKLER_CPTS)


def ref_net_joint(nodes, edges, cpts):
    """Independent joint: {tuple of values in sorted-name order: Fraction}. Parent order = order of ``nodes`` (the graph's node order)."""
    parents = {n: [p for p in nodes if (p, n) in set(edges)] for n in nodes}
    names = sorted(nodes)
    out = {}
    for combo in itertools.product([False, True], repeat=len(names)):
        env = dict(zip(names, combo))
        w = Fr(1)
        for n in nodes:
            p = cpts[n][tuple(env[q] for q in parents[n])]
            w *= p if env[n] else 1 - p
        out[combo] = w
    return out, names


def ref_net_prob(nodes, edges, cpts, query, evidence=None):
    """P(query | evidence) where both are dicts {name: bool} (conjunctions of literals)."""
    joint, names = ref_net_joint(nodes, edges, cpts)
    evidence = evidence or {}
    den = num = Fr(0)
    for combo, w in joint.items():
        env = dict(zip(names, combo))
        if all(env[k] == v for k, v in evidence.items()):
            den += w
            if all(env[k] == v for k, v in query.items()):
                num += w
    return None if den == 0 else num / den


@st.composite
def random_nets(draw, max_nodes=4):
    """A random DAG over n0..n{k-1} (edges only from lower to higher index, so acyclic), with random CPTs. Returns (nodes, edges, cpts)."""
    k = draw(st.integers(min_value=1, max_value=max_nodes))
    nodes = [f"n{i}" for i in range(k)]
    edges = [(nodes[i], nodes[j]) for i in range(k) for j in range(i + 1, k) if draw(st.booleans())]
    cpts = {}
    for n in nodes:
        ps = [p for p in nodes if (p, n) in set(edges)]
        cpts[n] = {key: draw(probs()) for key in itertools.product([False, True], repeat=len(ps))}
    return nodes, edges, cpts
