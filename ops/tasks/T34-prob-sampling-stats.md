# T34-prob-sampling-stats

**Goal.** Implement the statistics layer in `src/dsdk/prob/sampling.py`: `standard_error`, `wilson_interval`, `make_estimate`, `make_comparison`, `inverse_cdf_draws`.

**Files to edit.** `src/dsdk/prob/sampling.py`, only those five functions. (`_check_int` is already written; use it. Do not touch the other functions: another task owns them.) Do NOT edit any file under `tests/`, `fixtures/`, `tracks.toml`, `tracks/`, `ops/`, or functions owned by other tasks. The docstrings in the stub files are the spec: read them first (module docstring, then each function), then the tests named in the done command.

**Done when.** `cd /home/user/dsdk && uv run pytest tests/prob/test_sampling_stats.py -q` passes (exit 0). Then run `cd /home/user/dsdk && uv run pytest -q tests/core tests/logic tests/test_reuse.py` and confirm it still passes.

**Depends on.** none (start here, in parallel with T30).

**Pitfalls.**
- `_check_int(x, name, minimum)` rejects bool and non-int with TypeError and values below `minimum` with ValueError. Use it for `trials` (minimum 1), `successes` (minimum 0), `drawn`, `n`. Then `successes > trials` is a ValueError. Do the int checks in the order trials, then successes.
- `standard_error` is `math.sqrt(p * (1 - p) / trials)` with `p = successes / trials`. `wilson_interval` implements the formula in its docstring literally; `z` must be an int/float (not bool) that is finite and > 0. Set `low = 0.0` exactly when `successes == 0` and `high = 1.0` exactly when `successes == trials`, otherwise clamp `centre -/+ half` into [0, 1]: floating-point rounding must not put `p_hat` outside its own interval (a test uses 498 successes of 498).
- `make_estimate(successes, trials, drawn)` returns `Estimate(successes, trials, drawn, successes / trials, standard_error(...), low, high)` with `(low, high) = wilson_interval(successes, trials)`. `drawn < trials` is a ValueError.
- `make_comparison(exact, estimate)`: `target = float(exact)`, `error = abs(estimate.p_hat - target)`, `z_score = error / estimate.stderr` when `stderr > 0`, else `0.0` if `error == 0` and `math.inf` otherwise; `covered = estimate.low <= target <= estimate.high` (inclusive).
- `inverse_cdf_draws(weights, n, seed)`: validate `n` with `_check_int` and `seed` (an `int`, not a `bool`; TypeError otherwise); `weights` must be non-empty (ValueError), all `Fraction` (TypeError: ints and floats are rejected), all >= 0 and with a positive sum (ValueError). Cumulative shares are computed with EXACT Fractions and converted with ONE `float()` at the end: `cum.append(float(running / total))`. Then `rng = random.Random(seed)` and for each draw `bisect.bisect_right(cum, rng.random())`. Use ONLY `rng.random()`; never `choices`, `uniform` or `sample` (the exact stream of numbers is tested against a reference). `n == 0` returns `()`.
- `bisect`, `math`, `random`, `Fraction` are already imported.

**Rules.** Use ONLY file reading/editing and Bash for pytest. Never create sessions, triggers, agents or remote resources. Do not run git commands that change state. Remove `raise NotImplementedError` only in the functions this task owns. Keep docstrings. No new dependencies. 2 attempts total.
