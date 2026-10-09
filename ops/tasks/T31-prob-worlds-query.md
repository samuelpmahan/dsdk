# T31-prob-worlds-query

**Goal.** Implement conditioning and exact queries in `src/dsdk/prob/worlds.py`: `reweight`, `condition`, `probability`, `marginals`, `normalise`.

**Files to edit.** `src/dsdk/prob/worlds.py`, only those five functions. Do NOT edit any file under `tests/`, `fixtures/`, `tracks.toml`, `tracks/`, `ops/`, or functions owned by other tasks. The docstrings in the stub files are the spec: read them first (module docstring, then each function), then the tests named in the done command.

**Done when.** `cd /home/user/dsdk && uv run pytest tests/prob/test_worlds_query.py tests/prob/test_wumpus_oracle.py -q` passes (exit 0). Then run `cd /home/user/dsdk && uv run pytest -q tests/core tests/logic tests/test_reuse.py` and confirm it still passes.

**Depends on.** T30 (to_weight, prior_belief, Belief.total/mass are used by the tests and the functions).

**Pitfalls.**
- `reweight`: call the likelihood exactly ONCE per world, in world order, with a FRESH dict from `w.assignment()`; convert the result with `to_weight(value, "likelihood")` (so bad values raise there). Keep every world, even when the new weight is 0. `TypeError` if `b` is not a `Belief` or `likelihood` is not callable.
- `condition` is `reweight` with likelihood `1 if evaluate(evidence, a) else 0`. It raises (does NOT return a Judgment): `TypeError` for wrong types, `UnmodelledVariableError(tuple(sorted(missing)))` for unmodelled variables. Impossible evidence returns a belief with total 0, not an exception, and nothing is normalised.
- `probability` returns a `Judgment`. Check order: types (TypeError), then unmodelled variables of query and given together -> `Judgment(Status.UNKNOWN, None, "unmodelled variables: " + ", ".join(sorted(missing)))`, then the denominator: `b.total` when `given is None`, else `b.mass(given)`. A zero denominator gives `Judgment(Status.INVALID, None, reason)`: the reason must contain "zero total weight" in the no-`given` case and "probability zero" in the `given` case (tests match these substrings). NEVER return KNOWN 0 or 1 for a zero denominator. Otherwise `Judgment(Status.KNOWN, numerator / denominator, "")` where the numerator is `b.mass(query)` or `b.mass(And(query, given))`; the value is a `Fraction` (0 and 1 are fine, only `None` is forbidden for KNOWN).
- `marginals`: INVALID (reason contains "zero total weight") when `b.total == 0`; else KNOWN with a dict `{name: Fraction}` in `b.variables` order, each the sum of weights of worlds where that variable is true, divided by the total. Use index `i` into `w.values[i][1]`.
- `normalise`: INVALID (reason contains "zero total weight") for total 0; else KNOWN with a NEW `Belief(b.variables, worlds)` whose weights are `w.weight / total`, same world order. Do not mutate `b`.
- Import what you need from the existing imports at the top of the file; `And`, `Const`, `evaluate`, `variables`, `Judgment`, `Status`, `to_weight` are already imported.

**Rules.** Use ONLY file reading/editing and Bash for pytest. Never create sessions, triggers, agents or remote resources. Do not run git commands that change state. Remove `raise NotImplementedError` only in the functions this task owns. Keep docstrings. No new dependencies. 2 attempts total.
