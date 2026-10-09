# T54-worlds-buildlog

**Goal.** Implement the build-ledger world in `src/dsdk/worlds/buildlog.py`: `parse_ledger`, `load_ledger`, `models`, `first_try_rate` (plus private helpers).

**Files to edit.** `src/dsdk/worlds/buildlog.py` only. Do NOT edit any file under `tests/`, `fixtures/`, `tracks.toml`, `tracks/`, `ops/`, or other modules. Read the module docstring (strict line schema) and every stub docstring first. Read `tests/worlds/test_worlds_buildlog.py` before coding.

**Done when.** `cd /home/user/dsdk && .venv/bin/python -m pytest tests/worlds/test_worlds_buildlog.py -q` passes (exit 0). Also `cd /home/user/dsdk && .venv/bin/python -m pytest tests/core tests/logic tests/graph tests/test_reuse.py -q` must stay green.

**Depends on.** none

**Pitfalls.**
- `bool` is an `int` in Python: reject `True`/`False` for `ts`, `attempt`, `wall_s`, `tests_*`, `round`. `wall_s` may be int or float, must be finite (`json` accepts `NaN`/`Infinity`; use `math.isfinite`) and >= 0; store it as `float`.
- Every error is `LedgerError` and its message starts `line N:` where N is the 1-based PHYSICAL line number (blank lines are skipped but still counted). `LedgerEntry.line` uses the same number.
- Check order per line: JSON, object, missing required keys, unknown keys, then field values in the order ts, task/model, attempt, outcome, wall_s, tests, round, note.
- `None` for `tests_passed` means "not run", not zero. `tests_passed <= tests_total` is checked only when both are ints.
- `first_try_rate` returns a `Judgment`: INVALID (bad arguments), NOT_OBSERVED (no attempt-1 rows), UNKNOWN (fewer than `min_n`), KNOWN (a float, 0.0 allowed). `entries` may be a one-shot iterator: consume it once. Never raise.
- `load_ledger`: read UTF-8, `splitlines()`, delegate to `parse_ledger`. Do not catch `FileNotFoundError`.

**Rules.** Use ONLY file reading/editing and Bash for pytest. Never create sessions, triggers, agents or remote resources. Do not run git commands that change state. Remove `raise NotImplementedError` only in the functions this task owns. Keep docstrings and the existing imports. Standard library only. Public API of `dsdk.core` / `dsdk.logic` only. 2 attempts total.
