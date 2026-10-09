"""An independent six-degrees oracle for tests: plain dicts and loops, NO dsdk imports.

Works from the raw rows of a world (selections and transitions as tuples of ints) and uses algorithms different from the
library's: level-synchronous breadth-first search for the observed path, and Bellman-Ford on (inferred, hops) pairs plus a
backward distance table for the best path (the library uses a FIFO queue and Dijkstra over path tuples).
"""
from collections import defaultdict
from itertools import combinations

INF = (10**9, 10**9)


def edges_of(selections, transitions):
    """({(a, b): inferred?}, observed-adjacency) over track IDs; an observed transition beats an inferred edge."""
    sets = defaultdict(set)
    for track, group, date in selections:
        sets[(group, date)].add(track)
    succ = defaultdict(dict)
    for tracks in sets.values():
        for a, b in combinations(sorted(tracks), 2):
            succ[a][b] = True
            succ[b][a] = True
    known = defaultdict(list)
    for a, b, _g, _d in transitions:
        succ[a][b] = False
    for a, row in succ.items():
        known[a] = sorted(b for b, inferred in row.items() if not inferred)
    return succ, known


def known_path(known, s, t):
    if s == t:
        return [s]
    parent, frontier = {s: None}, [s]
    while frontier and t not in parent:
        nxt = []
        for u in frontier:
            for v in known.get(u, ()):
                if v not in parent:
                    parent[v] = u
                    nxt.append(v)
        frontier = nxt
    if t not in parent:
        return None
    out = [t]
    while parent[out[-1]] is not None:
        out.append(parent[out[-1]])
    return out[::-1]


def best_path(succ, s, t):
    dist = {t: (0, 0)}
    changed = True
    while changed:
        changed = False
        for u, row in succ.items():
            for v, inferred in row.items():
                if v in dist:
                    cand = (dist[v][0] + inferred, dist[v][1] + 1)
                    if cand < dist.get(u, INF):
                        dist[u] = cand
                        changed = True
    if s not in dist:
        return None
    path, here = [s], s
    while here != t:
        for v in sorted(succ[here]):
            if v in dist and (dist[v][0] + succ[here][v], dist[v][1] + 1) == dist[here]:
                path.append(v)
                here = v
                break
    return path


def answer(selections, transitions, s, t):
    """(status, reason-with-ids, path-of-ids) for track IDs s and t (both valid)."""
    succ, known = edges_of(selections, transitions)
    p = known_path(known, s, t)
    if p is not None:
        return "known", "known path: " + " -> ".join(map(str, p)), p
    p = best_path(succ, s, t)
    if p is None:
        return "unknown", "open world", None
    bad = [f"{a}->{b} (unknown)" for a, b in zip(p, p[1:]) if succ[a][b]]
    return "unknown", "uncertain edges on best candidate path: " + ", ".join(bad), p
