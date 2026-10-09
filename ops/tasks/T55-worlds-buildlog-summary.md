# T55-worlds-buildlog-summary

**Goal.** Implement `first_try_summary` and `round_throughput` in `src/dsdk/worlds/buildlog.py`. The first returns a Judgment whose value is a `FirstTry` (passes, attempts, rate, low, high, confidence) with the interval obtained by CALLING `dsdk.prob.exact_interval`; the second returns one `RoundStats` per dispatch round for the Lab's throughput chart.

**Files to edit.** `src/dsdk/worlds/buildlog.py` only, and ONLY the two functions named above (the dataclasses `FirstTry` and `RoundStats` are already written). The rest of the file is verified code: do not change it. Do NOT edit any file under `tests/`, `fixtures/`, `tracks.toml`, `tracks/`, `ops/`, `lab/`, `tools/`. Read the two docstrings first (they are decision tables with exact reason strings), then `tests/worlds/test_worlds_buildlog_summary.py`, then `exact_interval` in `src/dsdk/prob/sampling.py`.

**Done when.** `cd /home/user/dsdk && .venv/bin/python -m pytest tests/worlds/test_worlds_buildlog_summary.py tests/worlds/test_worlds_buildlog.py -q` passes (exit 0; 16 new tests plus the 35 existing ones). Also `cd /home/user/dsdk && .venv/bin/python -m pytest tests/core tests/logic tests/graph tests/prob tests/test_reuse.py -q` must stay green.

**Depends on.** none (`dsdk.prob.exact_interval` is implemented)

**Pitfalls.**
- Write NO interval arithmetic: no square root, no binomial coefficient, no `1.96`, no `**`. Call `exact_interval(passes, attempts, confidence)` and put its two numbers into `FirstTry` unchanged. A test fails if the function body contains interval maths.
- `bool` is an `int` in Python: `confidence=True` must be INVALID. Check the model first (empty or non-str model is INVALID before the confidence is looked at). `float('nan')` is not strictly between 0 and 1 (write the check as `0 < confidence < 1`, which is false for NaN). Never raise.
- Only `attempt == 1` entries of the named model count; only `outcome == "pass"` is a pass (partial, fail and error are not). No such entries at all is NOT_OBSERVED, not a KNOWN zero.
- The reason string is exact: `f"{passes}/{attempts} attempt-1 runs passed; exact {confidence * 100:g}% interval {low:.3f} to {high:.3f}"`, so `0.95` prints `95` and `0.99` prints `99`.
- `FirstTry.confidence` is `float(confidence)`; `rate` is `passes / attempts` (a float).
- `round_throughput`: skip entries whose `round` is `None`; group by round; output in ascending round number; `started`/`finished` are the MIN and MAX `ts` (not the first and last line); `models` is the sorted tuple of distinct names; `tests_green` adds `tests_passed` only for entries with outcome `pass` AND a non-`None` count; `agent_seconds` is the sum of `wall_s`. Both inputs may be one-shot iterators: consume once.

**Rules.** Use ONLY file reading/editing and Bash for pytest. Never create sessions, triggers, agents or remote resources. Do not run git commands that change state. Remove `raise NotImplementedError` only in the functions this task owns. Keep docstrings and the existing imports. Standard library only. Public API of `dsdk.core` / `dsdk.logic` only. 2 attempts total.
