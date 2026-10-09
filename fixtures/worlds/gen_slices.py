#!/usr/bin/env python3
"""Independent oracle for dsdk.worlds: writes fixtures/worlds/lostlands_slices.json.

Run:  python3 fixtures/worlds/gen_slices.py            (writes the JSON next to this file)
      python3 fixtures/worlds/gen_slices.py --print    (also prints the slices in words, for the human hand-check)

This script imports NOTHING from dsdk. It reads the vendored gzip with ``json`` + ``gzip`` and recomputes every
number with plain dicts and loops, using DIFFERENT algorithms from the library:

* counts / neighbours: dictionaries keyed by IDs;
* known paths: level-by-level breadth-first search over sorted adjacency lists (the library uses a FIFO queue);
* best candidate path: Bellman-Ford on (inferred, hops) pairs, then the lexicographically smallest minimum path
  rebuilt by a backward distance table (the library uses Dijkstra over path tuples).

A disagreement between this file's output and ``dsdk.worlds`` means one of them is wrong; never edit the JSON by
hand. The slices were also read by a person against the track names printed by ``--print``.
"""
import gzip
import hashlib
import json
import random
import sys
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

HERE = Path(__file__).resolve().parent
GZ = HERE / "lostlands-2018.jukebox.json.gz"
OUT = HERE / "lostlands_slices.json"
PINNED = "7e0b652aac543fbe89e80e8b47b5e7f0e67ac622ee20ae2426bd6d07492eb8a5"

raw = GZ.read_bytes()
assert hashlib.sha256(raw).hexdigest() == PINNED, "vendored store does not match the pinned SHA-256"
doc = json.loads(gzip.decompress(raw))
ART, TRK, GRP, DAT = doc["artists"], doc["tracks"], doc["selectorGroups"], doc["dates"]
SEL, TRN = doc["selections"], doc["transitions"]
N = len(TRK)


def K(i):
    """The track's string key: graph nodes are named by key in dsdk.worlds."""
    return TRK[i][0]


def label(i):
    t = TRK[i]
    s = " & ".join(ART[a] for a in t[2]) + " - " + t[1]
    return s + (f" ({t[4]})" if t[4] else "")


# ---- sets, in first-appearance order
sets = {}
for t, g, d in SEL:
    sets.setdefault((g, d), []).append(t)
assert all(d != -1 for _, d in sets)  # the real file has no undated set
skey = lambda s: (s[0], s[1])

# ---- observed transitions: (a, b) -> (count, distinct sets)
obs = defaultdict(lambda: [0, set()])
for a, b, g, d in TRN:
    obs[(a, b)][0] += 1
    obs[(a, b)][1].add((g, d))
# ---- co-selection: unordered pair -> distinct sets
co = defaultdict(set)
for key, tracks in sets.items():
    for a, b in combinations(sorted(set(tracks)), 2):
        co[(a, b)].add(key)
track_sets = defaultdict(set)
for key, tracks in sets.items():
    for t in tracks:
        track_sets[t].add(key)

# ---- six-degrees edges: dst -> evidence; src -> {dst: inferred?}
succ = defaultdict(dict)
for (a, b) in co:
    succ[a][b] = True
    succ[b][a] = True
for (a, b) in obs:
    succ[a][b] = False  # observed wins
known_succ = defaultdict(list)
for (a, b) in obs:
    known_succ[a].append(b)
for a in known_succ:
    known_succ[a].sort()


def known_path(s, t):
    """Level-synchronous BFS; the parent of a node is the first node (in frontier order) that reaches it."""
    if s == t:
        return [s]
    parent = {s: None}
    frontier = [s]
    while frontier and t not in parent:
        nxt = []
        for u in frontier:
            for v in known_succ[u]:
                if v not in parent:
                    parent[v] = u
                    nxt.append(v)
        frontier = nxt
    if t not in parent:
        return None
    path = [t]
    while parent[path[-1]] is not None:
        path.append(parent[path[-1]])
    return path[::-1]


INF = (10**9, 10**9)


def best_path(s, t):
    """Minimum (inferred, hops) path; among minima the lexicographically smallest node sequence."""
    # backward distance to t by Bellman-Ford rounds over all edges
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
        need = dist[here]
        for v in sorted(succ[here]):  # smallest id first
            if v in dist and (dist[v][0] + succ[here][v], dist[v][1] + 1) == need:
                path.append(v)
                here = v
                break
        else:  # pragma: no cover
            raise AssertionError("no continuation")
    return path


def hop(a, b):
    if (a, b) in obs:
        c, ss = obs[(a, b)]
        return {"evidence": "known", "count": c, "sets": sorted(map(list, ss))}
    both = track_sets[a] & track_sets[b]
    assert both and a != b
    return {"evidence": "unknown", "count": len(both), "sets": sorted(map(list, both))}


def degrees(s, t):
    p = known_path(s, t)
    if p is not None:
        status, reason = "known", "known path: " + " -> ".join(K(x) for x in p)
    else:
        p = best_path(s, t)
        if p is None:
            return {"source": s, "target": t, "status": "unknown", "reason": "open world: no path found, but absence of an edge is not proof of impossibility", "path": None, "path_keys": None, "hops": []}
        hops = [hop(a, b) | {"source": a, "target": b} for a, b in zip(p, p[1:])]
        bad = [f"{K(h['source'])}->{K(h['target'])} ({h['evidence']})" for h in hops if h["evidence"] != "known"]
        return {"source": s, "target": t, "status": "unknown", "reason": "uncertain edges on best candidate path: " + ", ".join(bad), "path": p, "path_keys": [K(x) for x in p], "hops": hops}
    hops = [hop(a, b) | {"source": a, "target": b} for a, b in zip(p, p[1:])]
    return {"source": s, "target": t, "status": status, "reason": reason, "path": p, "path_keys": [K(x) for x in p], "hops": hops}


# ---- slices ----------------------------------------------------------------------------------------------
SLICE_TRACKS = [483, 237, 0, 1351]  # 483 and 237 are the two most-played tracks; 0 and 1351 are the first/last IDs


def track_slice(i):
    out_c, in_c = Counter(), Counter()
    for (a, b), (c, _) in obs.items():
        if a == i:
            out_c[b] += c
        if b == i:
            in_c[a] += c
    return {
        "label": label(i), "key": TRK[i][0], "artist": " & ".join(ART[a] for a in TRK[i][2]), "artists": [ART[a] for a in TRK[i][2]],
        "featured": [ART[a] for a in TRK[i][3]], "variation": TRK[i][4],
        "sets": sorted(map(list, track_sets[i])),
        "selections": sum(1 for t, _, _ in SEL if t == i),
        "out": {str(k): v for k, v in sorted(out_c.items())},
        "in": {str(k): v for k, v in sorted(in_c.items())},
        "co_neighbours": sorted(b if a == i else a for (a, b) in co if i in (a, b)),
    }


SMALL = sorted(sets, key=lambda k: (len(sets[k]), k))[:2]  # the two shortest sets
KTN = [k for k in sets if GRP[k[0]][1] in ("Kill The Noise", "Figure & Space Laces & Kill The Noise & Bare & Kill Rex") and DAT[k[1]] == "2018-09-14"]
MEGA = max(sets, key=lambda k: len(sets[k]))


def set_slice(key):
    v = sets[key]
    return {"group": key[0], "date": key[1], "group_label": GRP[key[0]][1], "date_label": DAT[key[1]], "tracks": v,
            "transitions": [[a, b] for a, b in zip(v, v[1:])]}


def comp_count_undirected(edges, nodes):
    parent = {n: n for n in nodes}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    for a, b in edges:
        parent[find(a)] = find(b)
    return len({find(n) for n in nodes})


own = defaultdict(set)
for t, g, d in SEL:
    own[g].add(t)
dj_tracks = {}
dj_members = {}
for a, b in combinations(range(len(GRP)), 2):
    n = len(own[a] & own[b])
    if n:
        dj_tracks[f"{a},{b}"] = n
    m = len(set(GRP[a][0]) & set(GRP[b][0]))
    if m:
        dj_members[f"{a},{b}"] = m

rng = random.Random(2018)
pairs = [(0, 1), (7, 7), (483, 237), (5, 900), (100, 1300), (0, 1351), (1351, 0)]
pairs += [(rng.randrange(N), rng.randrange(N)) for _ in range(40)]
# crowd-pleasers for the Lab demo (looked up by label so a person can read them)
BY_LABEL = {label(i): i for i in range(N)}
for a, b in [("Darude - Sandstorm", "Excision & Space Laces - 1 On 1"), ("Darude - Sandstorm", "Excision - Codename X (REMIX)"),
             ("Rick Ross - Hustlin'", "Skrillex & Rick Ross - Purple Lamborghini (EDIT)"), ("Drake - God's Plan", "Darude - Sandstorm")]:
    pairs.append((BY_LABEL[a], BY_LABEL[b]))
cases = [degrees(s, t) for s, t in pairs]
# make sure every category is represented
kinds = Counter((c["status"], c["path"] is None, any(h["evidence"] == "unknown" for h in c["hops"])) for c in cases)
assert ("known", False, False) in kinds and ("unknown", False, True) in kinds and ("unknown", True, False) in kinds, kinds

out = {
    "about": "Generated by fixtures/worlds/gen_slices.py (independent of dsdk). Do not edit by hand.",
    "source": {"sha256": PINNED, "meta": doc["meta"]},
    "counts": {"artists": len(ART), "tracks": N, "selectorGroups": len(GRP), "dates": len(DAT), "selections": len(SEL),
               "transitions": len(TRN), "sets": len(sets), "mega_set": [list(MEGA), len(sets[MEGA])]},
    "graph_totals": {
        "transition_edges": len(obs), "transition_self_loops": sum(1 for a, b in obs if a == b),
        "transition_total_weight": sum(c for c, _ in obs.values()),
        "coselection_edges": len(co), "coselection_total_weight": sum(len(s) for s in co.values()),
        "six_degrees_edges": sum(len(r) for r in succ.values()),
        "dj_edges_tracks": len(dj_tracks), "dj_edges_members": len(dj_members),
        "transition_weak_components": comp_count_undirected(list(obs), range(N)),
        "six_degrees_weak_components": comp_count_undirected([(a, b) for a, r in succ.items() for b in r], range(N)),
    },
    "tracks": {str(i): track_slice(i) for i in SLICE_TRACKS},
    "sets": {f"{k[0]},{k[1]}": set_slice(k) for k in SMALL + KTN + [MEGA]},
    "dj_tracks": dj_tracks, "dj_members": dj_members,
    "co_pairs": {f"{a},{b}": len(s) for (a, b), s in sorted(co.items(), key=lambda kv: (-len(kv[1]), kv[0]))[:12]},
    "degrees": cases,
}
OUT.write_text(json.dumps(out, indent=1) + "\n")

if "--print" in sys.argv:
    print("counts", out["counts"])
    print("totals", out["graph_totals"])
    for i, s in out["tracks"].items():
        print(f"\ntrack {i}: {s['label']}  [{s['selections']} selections in {len(s['sets'])} sets]")
        print("  followed by:", {label(int(k)): v for k, v in s["out"].items()})
        print("  preceded by:", {label(int(k)): v for k, v in s["in"].items()})
    for k, s in out["sets"].items():
        print(f"\nset {k}: {s['group_label']} on {s['date_label']} ({len(s['tracks'])} tracks)")
        for t in s["tracks"][:6]:
            print("   ", t, label(t))
    for c in cases[:14]:
        names = " -> ".join(label(p) for p in c["path"]) if c["path"] else "(no path)"
        print(f"\ndegrees {c['source']} -> {c['target']}: {c['status']} :: {c['reason'][:90]}\n   {names}")
