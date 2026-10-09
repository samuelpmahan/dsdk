#!/usr/bin/env python3
"""Read-only findings about Sam's Lost Lands 2018 data. Standard library only (no dsdk): an independent check.

Run:  python3 tools/lab/lostlands_findings.py          (about 5 seconds)
Each finding prints the claim, the numbers behind it, and the lines to look at.
"""
import gzip, json, random, statistics, itertools
from collections import Counter, defaultdict, deque
from pathlib import Path

GZ = Path(__file__).resolve().parents[2] / "fixtures" / "worlds" / "lostlands-2018.jukebox.json.gz"
d = json.loads(gzip.decompress(GZ.read_bytes()))
A, T, G, D = d["artists"], d["tracks"], d["selectorGroups"], d["dates"]


def label(i):
    t = T[i]
    return " & ".join(A[a] for a in t[2]) + " - " + t[1] + (f" ({t[4]})" if t[4] else "")


sets = {}
for t, g, dt in d["selections"]:
    sets.setdefault((g, dt), []).append(t)

print("=== Finding 1: the parser ate the '12' in '12th Planet' ===")
used = Counter()
for t in T:
    for a in t[2] + t[3]:
        used[A[a]] += 1
print(f"  artist 'th Planet' credited on {used['th Planet']} tracks; the real '12th Planet' on {used['12th Planet']} tracks")
print(f"  artist 'Chainz' (surely 2 Chainz) credited on {used['Chainz']} track(s)")
print("  artists whose name begins with a stray quote mark (CSV comma inside quotes):", [a for a in A if a.startswith('"')])
for i, t in enumerate(T):
    if "th Planet" in [A[a] for a in t[2]]:
        print("   e.g.", label(i)); break
print("  cause: jukebox src/parser.ts parseLine strips a leading number as a track index (regex ^\\s*\\d+[.)]?\\s*) so '12th Planet - X' loses '12'.")

print("\n=== Finding 2: one truncated credit holds 169 of 1,973 selections and a quarter of all 'played together' pairs ===")
mega = max(sets, key=lambda k: len(sets[k]))
pairs_all, pairs_mega = set(), set()
for k, v in sets.items():
    for p in itertools.combinations(sorted(set(v)), 2):
        pairs_all.add(p)
        if k == mega:
            pairs_mega.add(p)
only_mega = pairs_mega - {p for k, v in sets.items() if k != mega for p in itertools.combinations(sorted(set(v)), 2)}
print(f"  set: {G[mega[0]][1]!r} on {D[mega[1]]}: {len(sets[mega])} tracks, truncated credit = {bool(G[mega[0]][2])}")
print(f"  co-selection pairs total {len(pairs_all)}; inside that one set {len(pairs_mega)} ({100*len(pairs_mega)/len(pairs_all):.0f}%); only linked by it {len(only_mega)} ({100*len(only_mega)/len(pairs_all):.0f}%)")

print("\n=== Finding 3: two differently-credited 2018-09-14 sets share whole chains of identical transitions ===")
tr = {k: set(zip(v, v[1:])) for k, v in sets.items()}
best = max(((len(tr[a] & tr[b]) / max(1, len(tr[a] | tr[b])), len(tr[a] & tr[b]), a, b) for a, b in itertools.combinations(sets, 2) if sets[a] and sets[b]))
j, n, a, b = best
print(f"  {G[a[0]][1]!r} vs {G[b[0]][1]!r} on {D[a[1]]}: {n} identical back-to-back transitions (Jaccard {j:.2f}); next best pair shares at most 2")
chain = [x for x in sets[a] if x in set(sets[b])]
common = sorted(tr[a] & tr[b], key=lambda p: sets[a].index(p[0]))
for p in common:
    print("   both sets:", label(p[0]), "->", label(p[1]))
print("  most likely one stretch of music credited under both names (Kill The Noise is in both credits). That is an inference, not shown: only the matching moves are.")

print("\n=== Finding 4: 'six degrees' is about ten (observed moves only) ===")
n_t = len(T)
succ = defaultdict(set)
for a_, b_, g, dt in d["transitions"]:
    succ[a_].add(b_)
rng = random.Random(2018)
hops, none = [], 0
for _ in range(300):
    s, t = rng.randrange(n_t), rng.randrange(n_t)
    par = {s: None}; q = deque([s])
    while q and t not in par:
        u = q.popleft()
        for v in sorted(succ[u]):
            if v not in par:
                par[v] = u; q.append(v)
    if t in par:
        k = 0
        while par[t] is not None:
            t = par[t]; k += 1
        hops.append(k)
    else:
        none += 1
print(f"  300 random track pairs: {len(hops)} connected by observed moves only, median {statistics.median(hops)} hops, longest {max(hops)}; {none} not connected that way")
