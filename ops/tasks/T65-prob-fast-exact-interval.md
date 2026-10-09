# T65-prob-fast-exact-interval

**Goal.** Make `dsdk.prob.exact_interval(successes, trials, confidence=0.95)` at least 100x faster for `trials <= 2000` WITHOUT changing its results (they must stay within 1e-12 absolute of today's output on the whole frozen grid), its signature, its argument checks and errors, or its guarantee that the returned interval is never narrower than the exact Clopper-Pearson interval. Today `exact_interval(146, 300)` takes about 6.3 s and `exact_interval(3, 300)` the same; the Worlds risk curve calls it 12+ times and the Lab build calls it too. Target: about 3 ms at n = 300.

**Real cause (measured, not a guess).** It is not the number of terms: it is the SIZE of the numbers. The bisection midpoints are dyadic Fractions with denominator `2**j` (j up to 60). `p**i * (1-p)**(n-i)` therefore has a numerator and denominator of about `60 * n` bits (18,000 bits at n = 300), `math.comb` is added on top, and the `sum` of `n + 1` such Fractions makes Python normalise with a gcd every addition. That is 2 sides x 60 steps x (n + 1) terms of 18,000-bit arithmetic (time grows roughly like n cubed: 0.4 s at n = 100, 6 s at n = 300, minutes at n = 1000, half an hour at n = 2000). Nothing here needs exact arithmetic to ~1e-12 accuracy: tracks/A3/PROOFS.md, Proof 9 shows the float version solves the same equations.

**Files to edit.** `src/dsdk/prob/sampling.py` only, and only these names (owned by this card):
- `exact_interval`: new body (docstring: keep the definition and argument paragraphs, rewrite the "Method" and "Cost" paragraphs to describe the float method and the outward widening).
- `_binom_tail_ge` and `_binom_tail_le`: replace the Fraction versions by float ones `(n, k, p: float, logc: Sequence[float]) -> float` (or similar; nothing outside this module uses them; you may rename or add small private helpers, e.g. `_log_choose_table(n)`).
- `EXACT_BISECTION_STEPS` (keep the name; its meaning may change to the float step count, 60 is fine) and a new private constant `_WIDEN` (see below).
- NEW `_exact_interval_reference(successes, trials, confidence=0.95)`: the CURRENT code, moved here unchanged (exact Fraction bisection, with its own `_reference_tail_ge` / `_reference_tail_le` helpers), so that the fixture can be regenerated and the fast version can be compared against it. It is private and not exported.

Do NOT edit any file under `tests/`, `fixtures/`, `tools/`, `tracks.toml`, `tracks/`, `ops/`, or any other function in `sampling.py`, or `src/dsdk/prob/__init__.py`. Standard library only (`math.lgamma`, `math.log`, `math.log1p`, `math.exp`, `math.fsum`, `math.nextafter`).

**Done when.** `cd /home/user/dsdk && .venv/bin/python -m pytest tests/prob/test_prob_exact_interval_speed.py tests/prob/test_exact_interval.py -q` passes (exit 0). Never use uv. Then `.venv/bin/python -m pytest -q tests/prob tests/core tests/logic tests/test_reuse.py` still passes, and this prints a time under 0.05 s:
`.venv/bin/python -c "import time; from dsdk.prob import exact_interval; t=time.time(); print(exact_interval(146,300), time.time()-t)"`

**Depends on.** the existing exact interval (the Fraction implementation in `sampling.py`, its 53 tests in `tests/prob/test_exact_interval.py` must keep passing unchanged).

**The method (this is the contract; Proof 9 in tracks/A3/PROOFS.md proves it).**
1. Validate exactly as today, in the same order (`_check_int(trials)`, `_check_int(successes)`, `successes > trials`, `to_prob(confidence, "confidence")`, then `level == 0 or level == 1` -> ValueError). `half = float((1 - level) / 2)`, computed from the exact Fraction, then converted once.
2. Precompute once per call `logc[i] = lgamma(n+1) - lgamma(i+1) - lgamma(n-i+1)` for `i = 0..n`.
3. Tails in LOG space, summed with `math.fsum`: `P(X = i) = exp(logc[i] + i*log(p) + (n-i)*log1p(-p))`. `tail_ge(k, p)` sums `i = k..n` and `tail_le(k, p)` sums `i = 0..k`, DIRECTLY (never `1 - other side`: the complement loses all precision when `confidence` is close to 1 and the tail is tiny). Never compute `math.comb(...) * p**i * ...` in floats: `p**i` underflows to 0 at n = 2000 and the `comb` product overflows.
4. Same bisection as today, on floats: `lo, hi = 0.0, 1.0`; 60 halvings with `mid = (lo + hi) / 2`; lower end uses `tail_ge(k, mid) >= half -> hi = mid else lo = mid` and returns the LEFT end; upper end uses `tail_le(k, mid) > half -> lo = mid else hi = mid` and returns the RIGHT end. (Newton or secant steps with a bisection safeguard are allowed if you want more speed, but they must end with the same bracket logic; plain bisection already gives about 3 ms at n = 300.) `k = 0` gives `low == 0.0` and `k == n` gives `high == 1.0` EXACTLY, with no search.
5. Widen outward by `_WIDEN = 1e-13` (absolute): `low = max(0.0, low_bracket - _WIDEN)`, `high = min(1.0, high_bracket + _WIDEN)`. This replaces the `nextafter` step: the float tails are only accurate to about 1e-12 relative, so the end can be off by up to about 1e-14 in `p` for n <= 2000 (Proof 9), and the widening makes sure the returned float is never inside the exact end. It costs 1e-13, well inside the 1e-12 agreement budget. Do not make `_WIDEN` larger than 2e-13 and do not set it to 0.
6. Return a tuple of two Python `float`s.

**Pitfalls.**
- Passing `tests/prob/test_exact_interval.py` is not enough: those tests only reach n = 50. The new file also checks n = 300, 1000 and 2000 against frozen slow outputs, and checks with independent exact Fractions that the returned ends are on the safe side of the tail equations. A version that is within 1e-12 of the exact ends but NOT outward (widening forgotten) passes the agreement tests and fails the certificate test.
- `half` must be `a / 2` per side (a = 1 - confidence). Using `a` or `a / 4` is a plausible-looking bug that makes the interval too narrow or too wide.
- The lower end's equation is `P(X >= k) = half` (the tail INCLUDES `k`); the upper end's is `P(X <= k) = half`. An off-by-one (summing from `k + 1` or to `k - 1`) shifts both ends noticeably even at n = 300.
- Do not return `(high, low)`; do not return the midpoint of the final bracket.
- `lgamma` has absolute error about 1e-16 times its size (13,000 at n = 2000), so the tail has a relative error around 1e-12 at n = 2000: this is exactly why the widening is absolute 1e-13 and the card is limited to n <= 2000 (beyond that the result is still a good interval but the 1e-13 argument in Proof 9 does not cover it).
- The error and Judgment behaviour: this function raises (`TypeError` / `ValueError`) and returns a plain tuple; there is no Judgment/Status in it today and none may be added. The same messages are not tested but the same exception types and the same check ORDER are.

**Rules.** Use ONLY file reading/editing and Bash for pytest. Never create sessions, triggers, agents or remote resources. Do not run git commands that change state. Keep docstrings. No new dependencies. 2 attempts total.
