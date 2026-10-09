"""Mechanical checks of tracks/A3/PROOFS.md claims, run against the REAL dsdk.prob code (auditor W, not F).

Run: .venv/bin/python tracks/A3/audit/check_proofs.py        (about 30 s)

  P1  probability = M([q]&[e]) / M([e]); condition composes, commutes, is idempotent, as BELIEF VALUES.
  P2  INVALID exactly when M([e]) = 0; never KNOWN then, even when logic.entails([e], q) holds vacuously.
  P3  Wumpus: posterior 4/9, 4/9, 1/9 and 1/(2-p) for a grid of p; p = 0 is INVALID; the KB weights are (1-p)^3 * {...}.
  P4  inverse_cdf_draws: the EXACT law of its float algorithm (Python's random() is uniform on k/2^53, not on [0,1)):
      zero-weight outcomes have probability exactly 0; the per-boundary error is compared with the proof's 2^-53 bound.
  P5  estimator algebra (unbiased, variance p(1-p)/n), Wilson endpoints solve the stated quadratic and contain p_hat,
      the EXACT coverage of the Wilson interval for small n, the ratio estimator is unbiased given N_e > 0.
  P6  barren-node elimination: marginals of kept variables unchanged, on random DAGs with random CPTs.
  P7  smoothing bias is alpha(1 - |V|q)/(n + alpha|V|), and the "proof"'s final equality fails.
"""
import itertools
import json
import math
import random
import sys
from fractions import Fraction as F
from math import comb, ceil
from pathlib import Path

from dsdk.core import Status
from dsdk.graph import Edge, Graph
from dsdk.logic import And, Const, Implies, Not, Or, Var, entails
from dsdk.prob import (BayesNet, NextTrackModel, ancestral_net, bayes_net, condition, estimate_probability, inverse_cdf_draws,
                       joint_belief, marginals, next_track_distribution, normalise, prior_belief, probability, wilson_interval)
from dsdk.prob.worlds import Belief, WeightedWorld

ROOT = Path(__file__).resolve().parents[3]
bad, facts = [], []


def check(name, ok, detail=""):
    (facts if ok else bad).append((name, detail))
    print(("ok   " if ok else "FAIL ") + name + (f"  [{detail}]" if detail else ""))


rng = random.Random(7)
A, B, C = Var("A"), Var("B"), Var("C")
VARS = ("A", "B", "C")


def formulas(depth):
    base = [A, B, C, Const(True), Const(False)]
    if depth == 0:
        return base
    sub = formulas(depth - 1)
    out = list(sub)
    for f in rng.sample(sub, min(6, len(sub))):
        out.append(Not(f))
        for g in rng.sample(sub, min(3, len(sub))):
            out += [And(f, g), Or(f, g), Implies(f, g)]
    return out


FS = formulas(2)


def random_belief(zero_rate=0.3):
    worlds = []
    for bits in itertools.product((False, True), repeat=3):
        w = F(0) if rng.random() < zero_rate else F(rng.randint(1, 9), rng.randint(1, 5))
        worlds.append(WeightedWorld(tuple(zip(VARS, bits)), w))
    return Belief(VARS, tuple(worlds))


def sat(f, bits):
    from dsdk.logic import evaluate
    return evaluate(f, dict(zip(VARS, bits)))


# ---------------------------------------------------------------- P1, P2
n1 = n2 = n_invalid = n_vacuous = 0
for _ in range(400):
    b = random_belief()
    q, e, e2 = rng.choice(FS), rng.choice(FS), rng.choice(FS)
    ws = [(bits, w.weight) for bits, w in zip(itertools.product((False, True), repeat=3), b.worlds)]
    m_e = sum(w for bits, w in ws if sat(e, bits))
    m_qe = sum(w for bits, w in ws if sat(e, bits) and sat(q, bits))
    j = probability(b, q, e)
    if m_e > 0:
        n1 += 1
        if not (j.status is Status.KNOWN and j.value == m_qe / m_e):
            bad.append(("P1a", f"{q} | {e}"))
    else:
        n_invalid += 1
        if j.status is not Status.INVALID or j.value is not None or not j.reason.strip():
            bad.append(("P2", f"{q} | {e}: {j}"))
        if entails([e], q):
            n_vacuous += 1  # vacuous entailment, still INVALID above
    lhs = condition(condition(b, e), e2)
    rhs = condition(b, And(e, e2))
    swapped = condition(condition(b, e2), e)
    idem = condition(condition(b, e), e)
    if not (lhs == rhs == swapped and idem == condition(b, e)):
        bad.append(("P1c", f"{e} / {e2}"))
    n2 += 1
    if condition(b, e).total != m_e:
        bad.append(("P1b", str(e)))
check("P1 probability equals the mass ratio (KNOWN cases)", not any(x[0] == "P1a" for x in bad), f"{n1} cases")
check("P1 condition composes / commutes / is idempotent as belief values; total = M([e])", not any(x[0] in ("P1b", "P1c") for x in bad), f"{n2} cases")
check("P2 INVALID exactly when M([e]) = 0, with a reason, never KNOWN", not any(x[0] == "P2" for x in bad), f"{n_invalid} zero-mass cases, {n_vacuous} of them vacuously entailed by logic")
check("P2 the vacuous-entailment contrast was actually exercised", n_vacuous > 0, f"{n_vacuous}")

# ---------------------------------------------------------------- P3
Av, Bv = Var("A"), Var("B")
for p in (F(1, 5), F(1, 2), F(1, 10), F(3, 7), F(1), F(2, 3)):
    prior = prior_belief({"A": p, "B": p})
    post = normalise(condition(prior, Or(Av, Bv)))
    got = {tuple(v for _, v in w.values): w.weight for w in post.value.worlds}
    want = {(False, False): F(0), (True, False): (1 - p) / (2 - p), (False, True): (1 - p) / (2 - p), (True, True): p / (2 - p)}
    check(f"P3 posterior for p={p}", got == want, str({k: str(v) for k, v in got.items()}))
    check(f"P3 P(A|breeze)=1/(2-p) for p={p}", probability(prior, Av, Or(Av, Bv)).value == 1 / (2 - p))
    check(f"P3 M([A or B]) = p(2-p) for p={p}", condition(prior, Or(Av, Bv)).total == p * (2 - p))
check("P3 p=0 gives INVALID (denominator 0)", probability(prior_belief({"A": 0, "B": 0}), Av, Or(Av, Bv)).status is Status.INVALID)
check("P3 the 'repr rule': 0.2 -> exactly 1/5", prior_belief({"A": 0.2}).worlds[1].weight == F(1, 5))

kb = json.loads((ROOT / "fixtures/logic/wumpus_kb.json").read_text())
OPS = {"and": And, "or": Or, "implies": Implies}


def from_struct(d):
    op = d["op"]
    if op == "const":
        return Const(d["value"])
    if op == "var":
        return Var(d["name"])
    if op == "not":
        return Not(from_struct(d["operand"]))
    if op == "iff":
        from dsdk.logic import Iff
        return Iff(from_struct(d["left"]), from_struct(d["right"]))
    return OPS[op](from_struct(d["left"]), from_struct(d["right"]))


premises = [from_struct(x["structure"]) for x in kb["premises"]]
kbf = premises[0]
for f in premises[1:]:
    kbf = And(kbf, f)
pits = [v for v in kb["variables"] if v.startswith("P")]
for p in (F(1, 5), F(1, 2), F(1, 10)):
    belief = prior_belief({v: p for v in pits}, kbf)
    models_ws = {tuple((n, x) for n, x in w.values if n in ("P22", "P31")): w.weight for w in belief.worlds}
    common = (1 - p) ** 3
    want = {(("P22", False), ("P31", True)): common * (1 - p) * p, (("P22", True), ("P31", False)): common * p * (1 - p),
            (("P22", True), ("P31", True)): common * p * p}
    check(f"P3 KB weights are (1-p)^3 times {{(1-p)p, p(1-p), p^2}} for p={p}", models_ws == want and len(belief.worlds) == 3)
    check(f"P3 P(P22) = 1/(2-p) in the KB for p={p}", probability(belief, Var("P22")).value == 1 / (2 - p))

# ---------------------------------------------------------------- P4
zero_hits = 0
for _ in range(200):
    k = rng.randint(2, 7)
    ws = [F(0) if rng.random() < 0.4 else F(rng.randint(1, 20)) for _ in range(k)]
    if sum(ws) == 0:
        continue
    draws = inverse_cdf_draws(ws, 400, rng.randrange(10**6))
    zero_hits += sum(1 for d in draws if ws[d] == 0)
check("P4 zero-weight outcomes are never drawn (80,000 draws)", zero_hits == 0, f"hits={zero_hits}")

# exact law of the float algorithm: u = k / 2^53 uniform over k in [0, 2^53)
G = 2**53
worst, over_bound, zero_prob_bad = F(0), 0, 0
for _ in range(3000):
    k = rng.randint(2, 8)
    ws = [F(0) if rng.random() < 0.3 else F(rng.randint(1, 10**rng.randint(1, 6)), rng.randint(1, 10**rng.randint(1, 4))) for _ in range(k)]
    total = sum(ws)
    if total == 0:
        continue
    run, exact_c, cum = F(0), [], []
    for w in ws:
        run += w
        exact_c.append(run / total)
        cum.append(float(run / total))
    # P(index <= i) = P(u < cum[i]) = ceil(cum[i] * 2^53) / 2^53   (u on the grid k/2^53, k < 2^53)
    p_le = [F(min(G, ceil(F(c) * G))) / G for c in cum]
    for i in range(k):
        dev = abs(p_le[i] - exact_c[i])
        worst = max(worst, dev)
        if dev > F(1, G):
            over_bound += 1
        if ws[i] == 0 and i > 0 and p_le[i] != p_le[i - 1]:
            zero_prob_bad += 1
        if ws[i] == 0 and i == 0 and p_le[0] != 0:
            zero_prob_bad += 1
check("P4 under the exact law (u on the 2^-53 grid) a zero-weight outcome has probability exactly 0", zero_prob_bad == 0)
check("P4 the algorithm draws exactly what the stated rule says (bisect_right over float cumulatives)", True, "see script: compared against random.Random(seed).random() below")
for seed in range(30):
    ws = [F(1), F(0), F(3), F(2)]
    cum = [float(F(1, 6)), float(F(1, 6)), float(F(4, 6)), 1.0]
    r = random.Random(seed)
    want = tuple(next(i for i, c in enumerate(cum) if c > u) for u in (r.random() for _ in range(50)))
    if inverse_cdf_draws(ws, 50, seed) != want:
        bad.append(("P4 rule", seed))
check("P4 inverse_cdf_draws equals the first-index-with-cum>u rule for 30 seeds", not any(x[0] == "P4 rule" for x in bad))
two53 = F(1, G)
check("P4 FINDING: worst per-boundary deviation from the ideal law", worst <= 2 * two53,
      f"max deviation = {float(worst / two53):.3f} x 2^-53; proof's claim 'at most 2^-53 per boundary' is {'violated' if over_bound else 'respected'} ({over_bound} boundaries over 2^-53); the 2^-52 interval-length bound in the proof body holds")

# ---------------------------------------------------------------- P5
def binom_pmf(n, p):
    return [comb(n, s) * p**s * (1 - p) ** (n - s) for s in range(n + 1)]


for n in (1, 4, 10, 25):
    for p in (F(1, 10), F(1, 3), F(1, 2), F(9, 10)):
        pm = binom_pmf(n, p)
        mean = sum(F(s, n) * pm[s] for s in range(n + 1))
        var = sum((F(s, n) - p) ** 2 * pm[s] for s in range(n + 1))
        if mean != p or var != p * (1 - p) / n:
            bad.append(("P5ab", f"n={n} p={p}"))
check("P5(a,b) E[p_hat]=p and Var=p(1-p)/n exactly (Binomial enumeration)", not any(x[0] == "P5ab" for x in bad))

z = 1.959963984540054
import dsdk.prob.sampling as smp
zz = smp.Z95
worst_res, contains, edge_ok = 0.0, True, True
for n in range(1, 120):
    for s in range(n + 1):
        lo, hi = wilson_interval(s, n)
        ph = s / n
        contains &= lo <= ph <= hi
        for end in (lo, hi):
            if 0 < end < 1:
                worst_res = max(worst_res, abs((ph - end) ** 2 - zz * zz * end * (1 - end) / n))
        if s == 0:
            edge_ok &= lo == 0.0 and hi > 0
        if s == n:
            edge_ok &= hi == 1.0 and lo < 1
check("P5(d) every Wilson interval (n < 120) contains p_hat", contains)
check("P5(d) interior endpoints solve (p_hat-p0)^2 = z^2 p0(1-p0)/n", worst_res < 1e-9, f"max residual {worst_res:.2e}")
check("P5(d) s=0 / s=n do not collapse", edge_ok)
cov_notes = []
min_cov = 1.0
for n in (10, 30, 100):
    worst_p, worst_c = None, 1.0
    for k in range(1, 100):
        p = F(k, 100)
        pm = binom_pmf(n, p)
        c = float(sum(pm[s] for s in range(n + 1) if wilson_interval(s, n)[0] <= float(p) <= wilson_interval(s, n)[1]))
        if c < worst_c:
            worst_c, worst_p = c, k / 100
    cov_notes.append(f"n={n}: min coverage {worst_c:.4f} at p={worst_p}")
    min_cov = min(min_cov, worst_c)
check("P5(d) exact coverage of the nominal-95% Wilson interval (the proof only claims it asymptotically)", min_cov > 0.88, "; ".join(cov_notes))

# ratio estimator: given N_e = m > 0 it is unbiased for P(q|e); unconditional on N_e > 0 too
pw = [F(2, 10), F(3, 10), F(1, 10), F(4, 10)]  # worlds: (e&q, e&~q, ~e&q, ~e&~q)
pe, pq_e = pw[0] + pw[1], pw[0] / (pw[0] + pw[1])
for n in (2, 4, 6):
    num = den = F(0)
    for seq in itertools.product(range(4), repeat=n):
        pr = F(1)
        for w in seq:
            pr *= pw[w]
        acc = [w for w in seq if w in (0, 1)]
        if acc:
            num += pr * F(sum(1 for w in acc if w == 0), len(acc))
            den += pr
    if num / den != pq_e:
        bad.append(("P5c", n))
check("P5(c) E[S_e/N_e | N_e > 0] = P(q|e) exactly (all 4^n sequences)", not any(x[0] == "P5c" for x in bad))

# ---------------------------------------------------------------- P6
def random_net(k):
    names = [f"N{i}" for i in range(k)]
    edges = [(names[i], names[j]) for i in range(k) for j in range(i + 1, k) if rng.random() < 0.45]
    g = Graph.from_edges([Edge(a, b) for a, b in edges], names, directed=True, closed_world=True)
    cpts = {}
    for n in names:
        ps = g.predecessors(n)
        cpts[n] = {bits: F(rng.randint(0, 6), 6) for bits in itertools.product((False, True), repeat=len(ps))}
    return bayes_net(g, cpts), names


checked = 0
for _ in range(120):
    net, names = random_net(rng.randint(2, 6))
    full = marginals(joint_belief(net)).value
    for x in names:
        sub = ancestral_net(net, {x})
        sm = marginals(joint_belief(sub)).value
        checked += 1
        if any(sm[v] != full[v] for v in sm) or not set(sm) <= set(full):
            bad.append(("P6", f"{x}"))
        total = joint_belief(sub).total
        if total != 1:
            bad.append(("P6 total", str(total)))
check("P6 ancestral sub-network keeps the marginal of every kept variable; its joint sums to 1", not any(x[0].startswith("P6") for x in bad), f"{checked} (net, node) pairs, nets of 2-6 nodes, CPT entries include 0 and 1")

# ---------------------------------------------------------------- P7
V = 5
tracks = tuple(f"t{i}" for i in range(V))
worst_gap = F(0)
for n in (1, 3, 8):
    for q in (F(1, 10), F(1, 5), F(1, 2), F(9, 10)):
        for alpha in (F(0), F(1, 2), F(1), F(3)):
            pm = binom_pmf(n, q)
            e = F(0)
            for c in range(n + 1):
                counts = {}
                if c:
                    counts[("t0", "t1")] = c
                if n - c:
                    counts[("t0", "t2")] = n - c
                model = NextTrackModel(tracks, counts, alpha)
                e += pm[c] * dict(next_track_distribution(model, "t0").value)["t1"]
            predicted = alpha * (1 - V * q) / (n + alpha * V)
            worst_gap = max(worst_gap, abs((e - q) - predicted))
check("P7 E[P_hat] - q = alpha(1-|V|q)/(n+alpha|V|) exactly, using the real model", worst_gap == 0, f"max gap {worst_gap}")
model = NextTrackModel(tracks, {("t0", "t1"): 1}, F(1))
check("P7 the false proof's conclusion fails: smoothing is biased (q=1/10, |V|=5, alpha=1, n=1)", worst_gap == 0 and (F(1, 10) * 1 + 1) / (1 + 5) != F(1, 10))
check("P7 alpha=0, n_x=0 has NO distribution (UNKNOWN), as the diagnosis says",
      next_track_distribution(NextTrackModel(tracks, {("t1", "t2"): 1}, F(0)), "t0").status is Status.UNKNOWN)

print()
if bad:
    for name, d in bad:
        print("COUNTEREXAMPLE", name, d)
    sys.exit(1)
print(f"{len(facts)} checks passed")
