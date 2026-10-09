"""Shared helpers for the A5 audit checks: graph enumeration, an independent distance oracle, a tracer for real code locals."""
import itertools
import sys

from dsdk.graph import Graph


def all_digraphs(n, loops=True):
    """Every directed graph on nodes 0..n-1 (as edge lists), with or without self-loops."""
    pairs = [(i, j) for i in range(n) for j in range(n) if loops or i != j]
    for mask in range(1 << len(pairs)):
        yield [pairs[k] for k in range(len(pairs)) if mask >> k & 1]


def all_undirected(n, loops=True):
    pairs = [(i, j) for i in range(n) for j in range(i, n) if loops or i != j]
    for mask in range(1 << len(pairs)):
        yield [pairs[k] for k in range(len(pairs)) if mask >> k & 1]


def build(n, edges, directed=True):
    return Graph.from_edges(edges, list(range(n)), directed=directed)


def arrows(edges, directed):
    out = set(edges)
    if not directed:
        out |= {(b, a) for a, b in edges}
    return out


def floyd(n, edges, directed):
    """Independent oracle: {(i, j): hops} for every reachable pair (i to itself is 0)."""
    INF = 10 ** 9
    d = [[0 if i == j else INF for j in range(n)] for i in range(n)]
    for a, b in arrows(edges, directed):
        if a != b:
            d[a][b] = min(d[a][b], 1)
    for k in range(n):
        for i in range(n):
            for j in range(n):
                if d[i][k] + d[k][j] < d[i][j]:
                    d[i][j] = d[i][k] + d[k][j]
    return {(i, j): d[i][j] for i in range(n) for j in range(n) if d[i][j] < INF}


def _copy(v):
    import collections
    if isinstance(v, dict):
        return dict(v)
    if isinstance(v, (list, set, collections.deque)):
        return list(v)
    return v


def trace_loop_states(func, args, code_name, line_of_test):
    """Run the REAL function unmodified under sys.settrace and snapshot its locals every time execution reaches
    ``line_of_test`` (the line number of the ``while`` test inside ``code_name``). Returns (result, [snapshots])."""
    snaps = []

    def tracer(frame, event, arg):
        if frame.f_code.co_name != code_name:
            return None

        def local(frame, event, arg):
            if event == "line" and frame.f_lineno == line_of_test:
                snaps.append({k: _copy(v) for k, v in frame.f_locals.items()})
            return local

        return local

    sys.settrace(tracer)
    try:
        result = func(*args)
    finally:
        sys.settrace(None)
    return result, snaps
