# T36-prob-updates

**Goal.** Implement belief updates as `dsdk.core` ticks in `src/dsdk/prob/updates.py`: `start_series`, `belief_history`, `current_belief`, `observe`.

**Files to edit.** `src/dsdk/prob/updates.py`, only those four functions. (`_check_series`, `_record_evidence`, `_apply_condition` and the two module-level calculation Parts `_RECORD_EVIDENCE` / `_CONDITION` are already written; use them, do not rewrite them.) Do NOT edit any file under `tests/`, `fixtures/`, `tracks.toml`, `tracks/`, `ops/`, or functions owned by other tasks. The docstrings in the stub files are the spec: read them first (module docstring, then each function), then the tests named in the done command.

**Done when.** `cd /home/user/dsdk && uv run pytest tests/prob/test_updates.py -q` passes (exit 0). Then run `cd /home/user/dsdk && uv run pytest -q tests/core tests/logic tests/test_reuse.py` and confirm it still passes.

**Depends on.** T30, T31.

**Pitfalls.**
- Address layout: `px.<name>.belief.0` (set by `start_series` with `store.set(addr, Part(belief))` and returned), then for update `k >= 1` the Parts `px.<name>.evidence.<k>` and `px.<name>.belief.<k>`. Call `_check_series(store, name)` first in every function.
- `belief_history`: `parts = [store.get("px.<name>.belief.0")]` (raises `MissingPartError` if absent) and keep appending `store.get(...belief.<len(parts)>)` while `store.has(...)`. `current_belief` is its last element.
- `observe`: check `evidence` is a `Formula` (TypeError). Get the history, `prev = history[-1]`, `k = len(history)`, `b = prev.value`. If the evidence mentions variables not in `b.variables` return UNKNOWN (reason `"unmodelled variables: " + ", ".join(sorted(missing))`). Compute `p = probability(b, evidence)`; if it is not KNOWN or its value is 0 return `Judgment(Status.INVALID, None, ...)` whose reason contains the word "impossible". In BOTH early returns the store must not be touched: no compose, no tick, no receipts.
- Otherwise open ONE tick and do the two composes in this order: `with store.tick(f"{name}.observe.{k}") as tx:` then `ev_part = tx.compose(f"px.{name}.evidence.{k}", _RECORD_EVIDENCE, {"formula": Part(evidence)})` and `new_part = tx.compose(f"px.{name}.belief.{k}", _CONDITION, {"prev": prev, "evidence": ev_part})`. The input dict key ORDER matters (`prev` first, then `evidence`). Pass `prev` itself (the stored Part object), NOT `Part(prev.value)`, or the lineage chain breaks. Return `Judgment(Status.KNOWN, new_part, "")`.
- Do not catch exceptions around the tick: if a compose raises (an address already taken) the tick rolls back by itself and the exception must propagate unchanged. If a tick is already open, `store.tick` raises `TickInProgressError`; let it propagate.

**Rules.** Use ONLY file reading/editing and Bash for pytest. Never create sessions, triggers, agents or remote resources. Do not run git commands that change state. Remove `raise NotImplementedError` only in the functions this task owns. Keep docstrings. No new dependencies. 2 attempts total.
