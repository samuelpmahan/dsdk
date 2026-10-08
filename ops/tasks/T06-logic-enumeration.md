# T06-logic-enumeration

**Goal.** Implement `models`, `truth_table`, `is_satisfiable`, `is_valid`, `entails`, `countermodel` in `src/dsdk/logic/semantics.py`, then confirm the fixture suite.

**Files to edit.** `src/dsdk/logic/semantics.py` only. Do NOT edit any file under `tests/`, `fixtures/`, `tracks.toml`, or other tasks' functions. Stub signatures and docstrings are the spec: read them before coding.

**Done when.** `uv run pytest tests/logic/test_semantics.py tests/logic/test_fixtures.py -q` passes (exit 0). Also keep previously finished tasks green: `uv run pytest -q` must not regress anything you did not own.

**Depends on.** T04, T05

**Pitfalls.**
- Order is the contract: `names = sorted(set(over or variables(f)))`, then `itertools.product([False, True], repeat=len(names))`, `dict(zip(names, combo))` (fresh dict per yield; keys in sorted order).
- `models` is lazy: return a generator, but validate `over` covers `variables(f)` (raise ValueError) -- when the error surfaces (call or first next) is not tested; tests use `list(...)`.
- `entails`/`countermodel`: materialise `premises = list(premises)` FIRST (one-shot generators; a bare Formula then raises TypeError because it is not iterable). Variable set = union over premises and conclusion.
- `countermodel` returns the first assignment satisfying all premises and falsifying the conclusion, with a key for EVERY variable in the union; `entails` is `countermodel(...) is None`.
- `is_valid(f)` must equal `not is_satisfiable(Not(f))`; Const-only formulas have one empty assignment.
- Reuse `evaluate` from T05; do not rewrite evaluation.

**Rules.** Remove `raise NotImplementedError` only in the functions this task owns. Keep docstrings. No new dependencies. 2 attempts total.
