# A3 proof audit (probability)

Auditor: Manager W (Sonnet). I did not write `tracks/A3/PROOFS.md` or `src/dsdk/prob/`. Stance: adversarial, the proofs are not
trusted. `P` = `tracks/A3/PROOFS.md`; `S` = `src/dsdk/prob/sampling.py`, `W` = `worlds.py`, `T` = `transitions.py`. Written here: this
file and `tracks/A3/audit/` only. PROOFS.md and the prob code were not edited.

Mechanical evidence: `.venv/bin/python tracks/A3/audit/check_proofs.py` (about 1 s) runs 46 checks on the REAL `dsdk.prob` code
with exact `Fraction` arithmetic wherever possible: 400 random beliefs over 3 variables (30 % zero weights) against random
formulas, the Wumpus numbers for six values of p and the real `wumpus_kb.json`, the exact law of the sampler's float algorithm,
every Wilson interval for n < 120, exact binomial and exhaustive-sequence enumeration, 464 (random DAG, node) pairs for barren-node
elimination, and the real `NextTrackModel` for the smoothing bias. Result: **no counterexample to any claim**.
`tracks/A3/audit/negative_control.py` swaps in a `probability` that answers KNOWN 1 for impossible evidence and a `condition` that
drops zero-weight worlds; the checker then reports counterexamples, so the harness can fail.

## Verdicts

| Proof | Verdict |
|---|---|
| 1. `probability` is the conditional probability; `condition` composes (P13-29) | SOUND |
| 2. impossible evidence is exactly INVALID (P30-46) | SOUND WITH ONE OVERSTATED "iff" |
| 3. the Wumpus numbers and `1/(2-p)` (P47-66) | SOUND (every number re-derived; the KB factor claim confirmed on the real fixture) |
| 4. inverse-CDF draws have the right law (P67-79) | SOUND WITH GAPS (assumes a continuous uniform; the bound still holds) |
| 5. the Monte Carlo estimator and the interval (P80-97) | SOUND, with a claim worth stating more strongly (finite-n coverage) |
| 6. barren-node elimination (P98-113) | SOUND |
| 7. deliberately wrong: "additive smoothing is unbiased" (P114-133) | SOUND AS A FLAWED-PROOF EXHIBIT (flaw correctly named, diagnosis formula exact) |

## Findings

1. **Proof 2 says INVALID "iff" the evidence mass is 0, but the code answers UNKNOWN first when a variable is unmodelled
   (W `probability`, the `missing` check before the denominators).** So unsatisfiable evidence that mentions a variable the
   belief does not have is UNKNOWN, not INVALID (check "P2 SCOPE"). The proof is right under its own convention (every formula
   uses modelled variables); the statement should say so. Everything else in Proof 2 holds: 60 zero-mass cases, 59 of them
   vacuously entailed by `logic.entails`, all INVALID with a non-blank reason and never KNOWN.
2. **Proof 4 treats `u` as continuous on [0,1) (P67-79); Python's `random()` is uniform on the grid k/2^53.** I recomputed
   the exact law of the real algorithm, P(index <= i) = ceil(cum_i * 2^53) / 2^53, for 3,000 random weight vectors: the worst
   per-boundary deviation from the ideal law is 0.998 x 2^-53, so the proof's headline bound (2^-53 per boundary) holds. The
   argument is incomplete rather than wrong: the grid adds up to 2^-53 and the float rounding up to 2^-54, and the total stays
   below 2^-53 only because `cum` values in [0.5,1) are themselves multiples of 2^-53. The proof should say that.
3. **Consequence not stated in Proof 4: a POSITIVE weight below about 2^-53 of the total is never drawn.** With weights
   (1, 1e-20) the second outcome did not appear in 200,000 draws; its probability under the float algorithm is exactly 0. The
   claim "an outcome with w_i = 0 has probability exactly 0" is right (and checked on 80,000 draws), but "P(index = i) = w_i/W up
   to 2^-52" also permits this, so nothing is false; it is a limit users of `sample_worlds` should be told.
4. **Proof 5(d) claims only asymptotic coverage for the Wilson interval, which is honest; the finite-n numbers are worth
   stating.** Exact coverage (summing binomial probabilities over p = 0.01..0.99): minimum 90.4 % at n = 10 (p = 0.01), 93.0 % at
   n = 30 (p = 0.3), 92.1 % at n = 100 (p = 0.01). So a reader of the "95 %" label can be off by 5 points at the sample sizes the Lab
   will use. The endpoint formula, the quadratic it solves (residual 1.7e-16 over every n < 120), the containment of p_hat, and the
   non-collapse at 0 and n are all confirmed.
5. **Proof 5(c): the ratio estimator.** Confirmed by exhaustive enumeration of all 4^n sequences (n = 2, 4, 6): E[S_e/N_e | N_e > 0]
   = P(q|e) exactly. So the estimator is unbiased given at least one accepted draw, which is slightly stronger than the proof's "only
   consistent".
6. **Proof 3 numbers and the KB.** 4/9, 4/9, 1/9 and 5/9 at p = 1/5; 1/3, 1/3, 1/3 and 2/3 at p = 1/2; `1/(2-p)` for p in
   {1/5, 1/2, 1/10, 3/7, 1, 2/3}; p = 0 is INVALID; `0.2` converts to exactly 1/5. On the real `wumpus_kb.json` the three models
   have weights (1-p)^3 x {(1-p)p, p(1-p), p^2} for p = 1/5, 1/2, 1/10 (the three false cells are P11, P12, P21), and P(P22) = 1/(2-p).
7. **Proof 6 and Proof 7 hold exactly.** Barren-node elimination preserved every kept marginal on 464 random (DAG, node) pairs
   (CPT entries include 0 and 1) and each sub-network joint sums to 1. For the smoothing proof the diagnosis formula
   E[P_hat] - q = alpha(1 - |V|q)/(n + alpha|V|) is exact for n in {1,3,8}, q in {1/10,1/5,1/2,9/10}, alpha in {0,1/2,1,3}, computed with
   the real model; the false proof's conclusion fails (q = 1/10, |V| = 5, alpha = 1); alpha = 0 with nothing observed gives UNKNOWN as stated.
8. **Test references resolve.** All five test names quoted in PROOFS.md (conditioning identities, the brute-force oracle, ancestral marginals, and the two smoothing tests) exist in `tests/prob`.

## Not checked

- Proof 1 and 2 were checked over formulas on 3 variables with at most depth-2 nesting, not over all formulas.
- The sampler's statistical claims were checked by exact enumeration and the exact grid law, not by running many seeds and testing
  the output distribution (the prob tests do that).
- The graph-proof contract (`src/dsdk/graph/proofs.py`) and the text-question module (`src/dsdk/prob/ask.py`) were not touched or audited.
