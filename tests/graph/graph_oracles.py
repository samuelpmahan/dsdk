"""Test-only helpers for tests/graph: independent oracles and Hypothesis strategies.

The oracles use ONLY plain Python data (sets of pairs, dicts), never dsdk.graph, so a bug in dsdk.graph cannot
make an oracle agree with it by accident. Floyd-Warshall / transitive closure are deliberately naive.
(This file is named graph_oracles.py, not helpers.py: tests/logic/helpers.py already owns that module name.)
"""
from __future__ import annotations

import itertools

from hypothesis import strategies as st

from dsdk.core import Status
from dsdk.logic import And, Const, Iff, Implies, Not, Or, Var


# ----------------------------------------------------------------------------------------- oracles
def pair_set(edges, directed):
    """Edge list [(u, v), ...] -> set of directed pairs (undirected edges become both directions)."""
    pairs = set()
    for e in edges:
        u, v = e[0], e[1]
        pairs.add((u, v))
        if not directed:
            pairs.add((v, u))
    return pairs


def fw_distances(nodes, edges, directed):
    """Floyd-Warshall hop distances: {(a, b): int} for reachable pairs only (a == b gives 0)."""
    inf = float("inf")
    d = {(a, b): inf for a in nodes for b in nodes}
    for a in nodes:
        d[(a, a)] = 0
    for u, v in pair_set(edges, directed):
        if u != v:
            d[(u, v)] = 1
    for k in nodes:
        for a in nodes:
            for b in nodes:
                if d[(a, k)] + d[(k, b)] < d[(a, b)]:
                    d[(a, b)] = d[(a, k)] + d[(k, b)]
    return {pair: int(x) for pair, x in d.items() if x != inf}


def reach_positive(nodes, edges, directed):
    """Pairs (a, b) joined by a walk of length >= 1 (so (a, a) is in it iff a lies on a cycle or self-loop)."""
    reach = set(pair_set(edges, directed))
    changed = True
    while changed:
        changed = False
        for (a, b), (c, d) in itertools.product(list(reach), list(reach)):
            if b == c and (a, d) not in reach:
                reach.add((a, d))
                changed = True
    return reach


def has_cycle_oracle(nodes, edges, directed):
    """True iff the graph has a cycle in the sense of dsdk.graph.traverse (see its module docstring)."""
    pairs = pair_set(edges, directed)
    if any(u == v for u, v in pairs):
        return True
    if directed:
        return any((n, n) in reach_positive(nodes, edges, True) for n in nodes)
    # undirected, no self-loops: a cycle exists iff some component has more edges than a spanning forest
    und = {frozenset(p) for p in pairs}
    comps = connected_components_oracle(nodes, edges, False)
    return len(und) > len(nodes) - len(comps)


def connected_components_oracle(nodes, edges, directed):
    """Weak components as a set of frozensets (union-find)."""
    parent = {n: n for n in nodes}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for e in edges:
        parent[find(e[0])] = find(e[1])
    groups = {}
    for n in nodes:
        groups.setdefault(find(n), set()).add(n)
    return {frozenset(g) for g in groups.values()}


def scc_oracle(nodes, edges):
    """Strongly connected components as a set of frozensets, via mutual reachability."""
    dist = fw_distances(nodes, edges, True)
    groups = {frozenset(b for b in nodes if (a, b) in dist and (b, a) in dist) for a in nodes}
    return groups


def is_walk(path, edges, directed):
    """Every consecutive pair of `path` is an edge (undirected: either orientation)."""
    pairs = pair_set(edges, directed)
    return all((a, b) in pairs for a, b in zip(path, path[1:]))


def is_cycle_witness(cycle, edges, directed):
    """Closed, simple, every step an edge; undirected cycles may not reuse an edge (so no (a, b, a))."""
    if cycle is None or len(cycle) < 2 or cycle[0] != cycle[-1]:
        return False
    if len(set(cycle[:-1])) != len(cycle) - 1:
        return False
    if not is_walk(cycle, edges, directed):
        return False
    if not directed and len(cycle) == 3:  # (a, b, a): same edge twice
        return False
    return True


# ------------------------------------------------------------------------------------- strategies
@st.composite
def edge_lists(draw, max_nodes=7, allow_loops=True, allow_dups=True):
    """(nodes, edges): nodes are ints 0..n-1, edges a list of (u, v) that may repeat and may be loops."""
    n = draw(st.integers(min_value=1, max_value=max_nodes))
    node = st.integers(min_value=0, max_value=n - 1)
    edge = st.tuples(node, node)
    if not allow_loops:
        edge = edge.filter(lambda e: e[0] != e[1])
    edges = draw(st.lists(edge, max_size=3 * n, unique=not allow_dups))
    return list(range(n)), edges


@st.composite
def dag_edge_lists(draw, max_nodes=7):
    """(nodes, edges) that is acyclic by construction: edges go forward in a random permutation."""
    n = draw(st.integers(min_value=1, max_value=max_nodes))
    perm = draw(st.permutations(list(range(n))))
    forward = [(perm[i], perm[j]) for i in range(n) for j in range(i + 1, n)]
    edges = draw(st.lists(st.sampled_from(forward), max_size=2 * n)) if forward else []
    return list(range(n)), edges


UNCERTAIN_OR_KNOWN = [Status.KNOWN, Status.UNKNOWN, Status.NOT_OBSERVED]


@st.composite
def evidence_edge_lists(draw, max_nodes=6):
    """(nodes, [(u, v, Status)]) with possibly repeated pairs; the test merges them itself."""
    n = draw(st.integers(min_value=1, max_value=max_nodes))
    node = st.integers(min_value=0, max_value=n - 1)
    edges = draw(st.lists(st.tuples(node, node, st.sampled_from(UNCERTAIN_OR_KNOWN)), max_size=2 * n))
    return list(range(n)), edges


def merged_evidence(edges, directed):
    """Strongest evidence per pair, like Graph.from_edges: {(u, v) or frozenset: Status}."""
    rank = {Status.KNOWN: 0, Status.UNKNOWN: 1, Status.NOT_OBSERVED: 2}
    out = {}
    for u, v, s in edges:
        key = (u, v) if directed else frozenset((u, v))
        if key not in out or rank[s] < rank[out[key]]:
            out[key] = s
    return out


def formulas(max_leaves=8):
    leaf = st.sampled_from(["a", "b", "c"]).map(Var) | st.booleans().map(Const)
    return st.recursive(
        leaf,
        lambda c: c.map(Not) | st.builds(And, c, c) | st.builds(Or, c, c) | st.builds(Implies, c, c) | st.builds(Iff, c, c),
        max_leaves=max_leaves,
    )


def formula_height(f):
    """Independent iterative height: leaf 0, Not 1 + child, binary 1 + max(children)."""
    best = 0
    todo = [(f, 0)]
    while todo:
        node, depth = todo.pop()
        best = max(best, depth)
        if isinstance(node, Not):
            todo.append((node.operand, depth + 1))
        elif isinstance(node, (And, Or, Implies, Iff)):
            todo.append((node.left, depth + 1))
            todo.append((node.right, depth + 1))
    return best


def preorder_nodes(f):
    """List of (node, parent_index, child_slot_name) in preorder, left before right."""
    out = []
    todo = [(f, None, None)]
    while todo:
        node, parent, slot = todo.pop()
        me = len(out)
        out.append((node, parent, slot))
        if isinstance(node, Not):
            todo.append((node.operand, me, "operand"))
        elif isinstance(node, (And, Or, Implies, Iff)):
            todo.append((node.right, me, "right"))
            todo.append((node.left, me, "left"))
    return out
