# A3 written proofs (exact conditioning, the Wumpus numbers, sampling error, barren-node elimination, smoothing)

The code in `dsdk.prob` is the executable counterpart of Proofs 1-6. The tests in `tests/prob` only SAMPLE these statements
(against an independent itertools oracle, the JS `priors.js` oracle, and textbook numbers); the proofs establish them for ALL finite
beliefs and networks. Proof 7 is **deliberately wrong**: find the flaw before you read the diagnosis.

**Conventions.** A *belief* is a finite list of worlds `w` (truth assignments to a finite variable set `V`) with weights
`m(w) >= 0` in `Q` (exact rationals). `M(S) = sum of m(w) over w in S`; `T = M(all worlds)` is `Belief.total`. For a formula `f`,
`[f]` is the set of worlds satisfying it. Probabilities are ratios of masses: `P(f) = M([f]) / T`, defined iff `T > 0`.

---

## Proof 1 -- `probability(b, q, e)` is the conditional probability, and `condition` composes

**Claim.** (a) If `M([e]) > 0`, then `probability(b, q, e) = M([q] ∩ [e]) / M([e]) = P(q | e)` where `P` is the normalised
distribution `m / T`. (b) `condition(b, e)` has mass function `m_e(w) = m(w) * 1[w ⊨ e]`; so `T_e = M([e])`. (c)
`condition(condition(b, e1), e2) = condition(b, e1 ∧ e2)` (as belief values, not just up to normalisation), and conditioning
commutes and is idempotent.

*Proof.* (a) `P(q | e) = P(q ∧ e) / P(e) = (M([q ∧ e]) / T) / (M([e]) / T) = M([q] ∩ [e]) / M([e])`, since `[q ∧ e] = [q] ∩ [e]`
(semantics of `And`) and `T > 0` cancels (if `M([e]) > 0` then `T >= M([e]) > 0`). The code computes exactly this ratio with
`Fraction` arithmetic, so there is no rounding to argue about. (b) `condition = reweight` with likelihood `1[. ⊨ e]`, which
multiplies each weight by 1 or 0 by definition of `reweight`. (c) `m_{e1,e2}(w) = m(w) 1[w ⊨ e1] 1[w ⊨ e2] = m(w) 1[w ⊨ e1 ∧ e2]`
because `w ⊨ e1 ∧ e2` iff `w ⊨ e1` and `w ⊨ e2`. Multiplication of indicators is commutative and `1[.]^2 = 1[.]`. Worlds are
never dropped (weights become 0), so the world lists coincide too. ∎

*Where the tests fit:* `test_condition_is_idempotent_commutative_and_equals_conditioning_on_the_conjunction`,
`test_probability_matches_the_brute_force_oracle`.

## Proof 2 -- impossible evidence is exactly the INVALID case (never a fabricated number)

**Claim.** `probability(b, q, e)` returns INVALID iff `M([e]) = 0` (or `T = 0` when `e` is absent). In particular if `e` is
unsatisfiable, `logic.entails([e], q)` holds for every `q` (vacuous truth) yet the code does not report probability 1.

*Proof.* The only division in the function is by `M([e])` (resp. `T`); the code tests that denominator against 0 first. If the
denominator is 0 the quotient `0/0` has no value in any consistent extension of the rationals: for every `c`, `c * 0 = 0 = M([q ∧ e])`,
so `P(q | e) = c` satisfies the defining equation `P(q | e) P(e) = P(q ∧ e)` for ALL `c`. The conditional probability is therefore
*undetermined*, not 0 and not 1, and the contract reports INVALID. For unsatisfiable `e`, `[e] = ∅` so `M([e]) = 0`: the logic's
"everything follows" is a statement about the *empty* set of worlds and says nothing about the weights. Conversely if `M([e]) > 0`
there is a division with a positive denominator and the answer is KNOWN. ∎

*Remark (what the sampler can and cannot prove).* The exact side computes `M([e])` and can prove it is 0. A rejection sampler that
accepts nothing has observed only `Binomial(n, P(e)) = 0`, which has probability `(1 - P(e))^n > 0` even when `P(e) > 0`; so it
cannot distinguish impossible from rare, and the contract makes it return UNKNOWN. `compare_with_exact` therefore lets the exact
INVALID win.

## Proof 3 -- the Wumpus numbers and the closed form `1 / (2 - p)`

**Setting.** Two cells A, B with independent pit prior `p` and a perfect breeze: the evidence is `A ∨ B`. Worlds and prior masses:
`(F,F): (1-p)^2`, `(F,T): (1-p)p`, `(T,F): p(1-p)`, `(T,T): p^2`.

**Claim.** If `0 < p <= 1`: `M([A ∨ B]) = 1 - (1-p)^2 = p(2-p)`, the posterior of the three surviving worlds is
`P(B only) = P(A only) = p(1-p) / (p(2-p)) = (1-p)/(2-p)` and `P(both) = p^2 / (p(2-p)) = p/(2-p)`, and `P(A | breeze) = (1-p)/(2-p) + p/(2-p) = 1/(2-p)`.

*Proof.* The three worlds satisfying `A ∨ B` have masses `p(1-p), p(1-p), p^2`; they sum to `2p - 2p^2 + p^2 = 2p - p^2 = p(2-p)`.
Divide each by it (Proof 1a) after cancelling the factor `p > 0`. `P(A)` adds the worlds with A true. ∎

*Numbers.* `p = 1/5`: `(1-p)/(2-p) = (4/5)/(9/5) = 4/9`, `p/(2-p) = (1/5)/(9/5) = 1/9`, `P(A) = 1/(9/5) = 5/9 = 55.56 %`.
`p = 1/2`: `(1/2)/(3/2) = 1/3` for each of the three, `P(A) = 2/3 = 66.67 %`. These are the values `priors.js` prints; the repr rule of
`exact.to_prob` (`0.2 -> 1/5`) is what makes the code produce them *exactly*.
*Edge:* `p = 0` makes `p(2-p) = 0`: the denominator is 0, so Proof 2 gives INVALID (the JS throws `RangeError`); `p = 1` gives
`P(both) = 1`.
*The knowledge base.* In `wumpus_kb.json` the three models differ only in `(P22, P31) ∈ {(F,T), (T,F), (T,T)}`; all other pit cells are
false in every model, contributing the common factor `(1-p)^3`, and the percept variables have no prior (factor 1), so the
weights are `(1-p)^3 * {(1-p)p, p(1-p), p^2}`, the same proportions as above. Hence `P(P22) = P(P31) = 1/(2-p)`.

## Proof 4 -- inverse-CDF draws have the right law (and never pick a zero-weight outcome)

**Algorithm.** `cum[i] = float((w_0 + ... + w_i) / W)`, `u = rng.random()` uniform on `[0,1)`, index = first `i` with `cum[i] > u`
(`bisect_right`).

**Claim.** With exact cumulatives `C_i = (w_0 + ... + w_i) / W` (`C_{-1} = 0`, `C_last = 1`), `P(index = i) = C_i - C_{i-1} = w_i / W`.
With the floats of the code, the law differs from it by at most `2^-53` per boundary, and an outcome with `w_i = 0` has probability exactly 0.

*Proof.* `index = i` iff `C_{i-1} <= u < C_i` (first `i` whose cumulative exceeds `u`), an interval of length `w_i / W` for the uniform
`u`. If `w_i = 0` the interval is empty, and `cum[i] = cum[i-1]` as floats (the same exact value is rounded once), so the first index
with `cum > u` can never be `i`. Since `u < 1 = cum[last]` an index always exists. Rounding each boundary to the nearest double moves
it by at most `2^-53` (relative to values in `[0,1]`), changing each interval's length by at most `2^-52`. ∎

## Proof 5 -- the Monte Carlo estimator: unbiased, variance `p(1-p)/n`, and what the interval means

**Claim.** Let `X_1..X_n` be i.i.d. draws from a normalised belief and `S = #{X_j ⊨ q}`. (a) `p_hat = S/n` is unbiased for `p = P(q)`.
(b) `Var(p_hat) = p(1-p)/n`, so the reported `stderr = sqrt(p_hat (1-p_hat)/n)` estimates the standard deviation of `p_hat`. (c) For
rejection sampling with evidence `e`, the accepted draws are i.i.d. from `P(. | e)` and `p_hat = S_e / N_e` estimates `P(q | e)`.
(d) The Wilson interval has asymptotic coverage 95 % (it is not exact for finite `n`; the test only asserts empirical coverage within
a band).

*Proof.* (a,b) `S ~ Binomial(n, p)` because the indicator `1[X_j ⊨ q]` is Bernoulli(p) and independent. `E[S] = np`,
`Var(S) = np(1-p)`; divide by `n` and `n^2`. (c) For a measurable set `A` of worlds, `P(X ∈ A | X ⊨ e) = P(X ∈ A ∩ [e]) / P(e)`, and
conditioning an i.i.d. sequence on "accept" independently for each draw gives an i.i.d. sequence from that conditional law; the number
of accepted draws `N_e` is random (Binomial(n, P(e))), so the estimator is a ratio and is only *consistent*, not unbiased, for finite
`n` (given `N_e = m > 0` it is unbiased for `P(q|e)`). When `N_e = 0` nothing can be said: UNKNOWN (Proof 2 remark). (d) The Wilson
interval is the set of `p0` with `|p_hat - p0| <= z sqrt(p0(1-p0)/n)`, obtained by inverting the CLT test; by the CLT its coverage tends
to `P(|Z| <= 1.96) = 0.95`. Solving the quadratic `(p_hat - p0)^2 = z^2 p0 (1-p0)/n` for `p0` gives
`(p_hat + z^2/2n ± z sqrt(p_hat(1-p_hat)/n + z^2/4n^2)) / (1 + z^2/n)`, the formula in `wilson_interval`. It contains `p_hat` and,
unlike `p_hat ± z·se`, does not collapse when `p_hat ∈ {0,1}` (the root of the quadratic is positive when `p_hat = 0`). ∎

## Proof 6 -- barren-node elimination (why `ancestral_net` preserves marginals)

**Claim.** Let `N` be a Bayes net over a DAG `G`, `X` a node, `A` the set of `X` and its ancestors. Then the marginal of every variable in
`A` under the joint of `N` equals its marginal under the joint of the sub-network on `A` (same CPTs).

*Proof.* The joint is `P(v) = ∏_{n ∈ G} P(v_n | v_{parents(n)})`. Suppose `G ≠ A`. The nodes outside `A` form a DAG, so it has a
node `L` with no children outside `A`. `L` also has no child inside `A`: such a child would make `L` an ancestor of a node of `A`, hence
`L ∈ A`. So `L` is a sink of `G`. Summing the joint over `v_L` factors out the CPT of `L`:
`Σ_{v_L} P(v_L | v_{pa(L)}) = P(v_L = T | .) + (1 - P(v_L = T | .)) = 1`, and no other factor mentions `v_L` (it has no children). So
the marginal over `V \ {L}` is the joint of the net with `L` removed, and every CPT that remains is unchanged. Repeat until only `A` is
left (`A` is closed under ancestors, so every kept node keeps all its parents and its CPT still makes sense). ∎

*Where the tests fit:* `test_ancestral_marginals_agree_with_the_full_joint_for_random_dags`.

---

## Proof 7 -- DELIBERATELY WRONG: "additive smoothing is unbiased"

**Claim (false).** For the next-track model with pseudo-count `alpha`, `P_hat(y | x) = (c(x,y) + alpha) / (n_x + alpha |V|)` is an unbiased
estimator of the true transition probability `q = P(y | x)`, where `n_x` is the number of observed transitions out of `x` and
`c(x,y) ~ Binomial(n_x, q)`.

*"Proof".* `E[c(x,y)] = n_x q`. Therefore
`E[P_hat] = (E[c] + alpha) / (n_x + alpha |V|) = (n_x q + alpha) / (n_x + alpha |V|)`.
Now take `alpha` to be the pseudo-count that makes the two terms cancel: the numerator is `n_x q + alpha` and the denominator
`n_x + alpha |V|`, so for any `alpha >= 0` the ratio equals `q` because "the smoothing adds the same relative amount to numerator
and denominator". Hence `E[P_hat] = q`. ∎

*Diagnosis (do not read before finding it).* The last step is false. `(n_x q + alpha) / (n_x + alpha |V|) = q` iff
`n_x q + alpha = n_x q + alpha |V| q` iff `alpha = alpha |V| q` iff `alpha = 0` or `q = 1/|V|`. The numerator adds `alpha`, the denominator
adds `alpha |V|`: the *relative* amounts are `alpha / (n_x q)` and `alpha |V| / n_x`, equal only when `q = 1/|V|`. In general
`E[P_hat] - q = alpha (1 - |V| q) / (n_x + alpha |V|)`: smoothing is biased towards the uniform distribution `1/|V|`, upward for
rare transitions (`q < 1/|V|`) and downward for common ones. That bias is the price paid for never assigning probability 0 to an
unseen transition; `test_larger_alpha_flattens_towards_uniform` and `test_smaller_alpha_is_better_on_training_pairs_larger_on_unseen_ones`
pin the behaviour the correct analysis predicts (variance falls, bias grows with `alpha`). With `alpha = 0` the estimator is unbiased
whenever `n_x > 0`, but then rows with `n_x = 0` have no value at all, which is why the contract answers UNKNOWN there.
