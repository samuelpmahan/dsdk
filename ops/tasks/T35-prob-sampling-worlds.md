# T35-prob-sampling-worlds

**Goal.** Implement sampling of beliefs and Bayes nets in `src/dsdk/prob/sampling.py`: `sample_worlds`, `estimate_probability`, `compare_with_exact`, `forward_sample`.

**Files to edit.** `src/dsdk/prob/sampling.py`, only those four functions. Do NOT edit any file under `tests/`, `fixtures/`, `tracks.toml`, `tracks/`, `ops/`, or functions owned by other tasks. The docstrings in the stub files are the spec: read them first (module docstring, then each function), then the tests named in the done command.

**Done when.** `cd /home/user/dsdk && uv run pytest tests/prob/test_sampling_worlds.py -q` passes (exit 0). Then run `cd /home/user/dsdk && uv run pytest -q tests/core tests/logic tests/test_reuse.py` and confirm it still passes.

**Depends on.** T30, T31, T32, T34 (everything the file imports must work; `compare_with_exact` calls `probability`; the tests build nets with `bayes_net` and `joint_belief`).

**Pitfalls.**
- `sample_worlds`: argument checks FIRST (`TypeError` for non-Belief, `_check_int(n, "n", 0)`, `seed` int-not-bool), even when the belief is dead. Then `b.total == 0` -> `Judgment(Status.INVALID, None, ...)` with "zero total weight" in the reason. Else `picks = inverse_cdf_draws([w.weight for w in b.worlds], n, seed)` and the answer is `Judgment(Status.KNOWN, tuple(b.worlds[i].values for i in picks), "")`. Do not draw random numbers yourself.
- `estimate_probability`: argument checks, then unmodelled variables of query/given -> `Judgment(Status.UNKNOWN, None, "unmodelled variables: " + ", ".join(sorted(missing)))` (same text as `probability`), then `drawn = sample_worlds(b, n, seed)` and if that is not KNOWN return it unchanged (INVALID for a dead belief). Loop over the drawn worlds (`dict(values)`): skip it if `given` is not None and `evaluate(given, a)` is false; otherwise `trials += 1` and `successes += 1` if `evaluate(query, a)`. If `trials == 0` return UNKNOWN (NOT INVALID; the reason must contain both "impossible" and "rare"). Else KNOWN with `make_estimate(successes, trials, n)`.
- `compare_with_exact`: `exact = probability(b, query, given)`; if its status is not KNOWN return it AS IS (so impossible evidence stays INVALID even though the sampler would say UNKNOWN). Then `sampled = estimate_probability(...)`; if not KNOWN return it as is. Else `Judgment(Status.KNOWN, make_comparison(exact.value, sampled.value), "")`.
- `forward_sample`: argument checks (non-BayesNet TypeError, n, seed). `order = topological_order(net.structure)`; ONE `rng = random.Random(seed)` for all samples; for each sample visit nodes in `order`; for each node exactly one `rng.random()`; the node is true iff `rng.random() < float(p)` where `p = net.cpts[node][tuple(value[q] for q in net.structure.predecessors(node))]`. Each sample is returned as `tuple((name, value[name]) for name in sorted(value))`, and the result is a tuple of samples.
- These tests take a few seconds (coverage over 200 seeds); that is expected.

**Rules.** Use ONLY file reading/editing and Bash for pytest. Never create sessions, triggers, agents or remote resources. Do not run git commands that change state. Remove `raise NotImplementedError` only in the functions this task owns. Keep docstrings. No new dependencies. 2 attempts total.
