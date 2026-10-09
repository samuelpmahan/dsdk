# T62-prob-exact-interval

**Goal.** Implement the exact (Clopper-Pearson) confidence interval with guaranteed coverage in `src/dsdk/prob/sampling.py`: `_binom_tail_ge`, `_binom_tail_le` and `exact_interval`. It replaces "approximately 95%" (the Wilson interval really covers only about 84% for rare events) with "at least 95%".

**Files to edit.** `src/dsdk/prob/sampling.py` only, only the three functions named in the goal (the constant `EXACT_BISECTION_STEPS` and the import of `to_prob` are already there; the export in `__init__.py` is already there). Do NOT edit any other function or file: nothing under `tests/`, `fixtures/`, `lab/`, `tracks/`, `tracks.toml` or `ops/`. The docstrings are the spec; read the `exact_interval` docstring word by word, then `tests/prob/test_exact_interval.py`.

**Done when.** `cd /home/user/dsdk && uv run pytest tests/prob/test_exact_interval.py -q` passes (exit 0; about 10 seconds; the last two tests are skipped if `node` is missing). Then run `cd /home/user/dsdk && uv run pytest -q tests/core tests/logic tests/prob tests/test_reuse.py` and confirm it still passes.

**Depends on.** none (the other sampling functions and `to_prob` are implemented).

**Pitfalls.**
- Use EXACT arithmetic inside the search: `Fraction` for the probabilities and `math.comb` for the binomial coefficients. No `float`, no `scipy`, no `numpy`.
- `_binom_tail_ge(n, k, p)` is `sum(math.comb(n, i) * p**i * (1 - p)**(n - i) for i in range(k, n + 1))` and `_binom_tail_le(n, k, p)` is the same sum over `range(0, k + 1)`, both starting from `Fraction(0)` so the result is a `Fraction`. `p` is a `Fraction`.
- Argument order of checks in `exact_interval`: `_check_int(trials, "trials", 1)`, `_check_int(successes, "successes", 0)`, then `successes > trials` is a `ValueError`, then `level = to_prob(confidence, "confidence")` (this already rejects bool, strings, None, nan, values outside [0, 1]); finally `level == 0` or `level == 1` is a `ValueError`. `half = (1 - level) / 2`.
- Lower end (only when `successes > 0`; otherwise it is exactly `Fraction(0)`): start `lo, hi = Fraction(0), Fraction(1)`; repeat `EXACT_BISECTION_STEPS` times: `mid = (lo + hi) / 2`; if `_binom_tail_ge(n, k, mid) >= half` then `hi = mid` else `lo = mid`. The lower end is `lo` (the LEFT end of the final bracket, never `hi` and never the midpoint).
- Upper end (only when `successes < trials`; otherwise exactly `Fraction(1)`): start the same; if `_binom_tail_le(n, k, mid) > half` then `lo = mid` else `hi = mid`. The upper end is `hi` (the RIGHT end of the final bracket).
- Convert to floats: `low_f = float(low)`, `high_f = float(high)`. If `Fraction(low_f) > low` set `low_f = math.nextafter(low_f, 0.0)`. If `Fraction(high_f) < high` set `high_f = min(1.0, math.nextafter(high_f, 1.0))`. This guarantees the float interval is never narrower than the exact one. Return `(low_f, high_f)` as a tuple of Python floats.
- Known values the tests pin: 5 of 10 gives about (0.1871, 0.8129); 0 of 10 gives (0.0, 0.3085); 33 of 35 gives (0.8084, 0.9930). A result of exactly `0.0` for zero successes and exactly `1.0` for all successes is required.
- Do not make it faster by approximating: the tests check the tail equations to 1e-9 and the coverage of the returned float ends. Trials in the hundreds are slow-ish (a few seconds); that is expected.

**Rules.** Use ONLY file reading/editing and Bash for pytest. Never create sessions, triggers, agents or remote resources. Do not run git commands that change state. Remove `raise NotImplementedError` only in the functions this task owns. Keep docstrings. No new dependencies. 2 attempts total.
