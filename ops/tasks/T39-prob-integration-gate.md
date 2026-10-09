# T39-prob-integration-gate

**Goal.** Integration gate for track A3: run the whole `tests/prob` directory and fix only integration slips (no new behaviour).

**Files to edit.** `src/dsdk/prob/*.py` only, and only where a failing test points to a mistake in already-implemented code. Do not change any docstring contract; if a test and a docstring disagree, stop and report instead of editing. Do NOT edit any file under `tests/`, `fixtures/`, `tracks.toml`, `tracks/`, `ops/`, or functions owned by other tasks. The docstrings in the stub files are the spec: read them first (module docstring, then each function), then the tests named in the done command.

**Done when.** `cd /home/user/dsdk && uv run pytest tests/prob -q` passes (exit 0). Then run `cd /home/user/dsdk && uv run pytest -q tests/core tests/logic tests/test_reuse.py` and confirm it still passes.

**Depends on.** T30, T31, T32, T33, T34, T35, T36, T37, T38 (all).

**Pitfalls.**
- The whole directory takes about 15 seconds (Hypothesis and 200-seed coverage tests). If a single test is slow or flaky, report its name; do not add sleeps or change seeds.
- `tests/prob/test_prob_reuse.py` checks that `dsdk.prob` imports `dsdk.logic`, `dsdk.core` and `dsdk.graph` in the modules named there; do not remove those imports, and do not import any package of order >= 4 from `tracks.toml`.
- `tests/prob/test_wumpus_oracle.py` has one live-parity test that runs `node` against `embodiedwumpusworld`; it skips itself when node or the checkout is absent. A failure there means a real disagreement with the JS oracle: report it, do not weaken anything.

**Rules.** Use ONLY file reading/editing and Bash for pytest. Never create sessions, triggers, agents or remote resources. Do not run git commands that change state. Remove `raise NotImplementedError` only in the functions this task owns. Keep docstrings. No new dependencies. 2 attempts total.
