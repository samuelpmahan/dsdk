# T04-logic-formula

**Goal.** Implement `Formula.__post_init__`, `variables`, `size`, `to_str` in `src/dsdk/logic/formula.py`.

**Files to edit.** `src/dsdk/logic/formula.py` only. Do NOT edit any file under `tests/`, `fixtures/`, `tracks.toml`, or other tasks' functions. Stub signatures and docstrings are the spec: read them before coding.

**Done when.** `uv run pytest tests/logic/test_formula.py -q` passes (exit 0). Also keep previously finished tasks green: `uv run pytest -q` must not regress anything you did not own.

**Depends on.** none (needs dsdk.core only through the package import)

**Pitfalls.**
- ONE `Formula.__post_init__` validates every subclass (dispatch on `type(self)` or use `dataclasses.fields`): Const needs `type(v) is bool` (not `isinstance`: 1 is not a bool here, but True is), Var needs a str matching `[A-Za-z_][A-Za-z0-9_]*` via `re.fullmatch` with `re.ASCII` (NOT `$`: "a\n" must fail; "é" must fail) and not "true"/"false", operands must be `Formula`.
- Depth 200 must work with the default recursion limit: write `variables`, `size`, `to_str` with an explicit stack. Dataclass `__eq__`/`__hash__` are fine at depth 200; do not override them.
- `to_str` grammar is exact: `(~x)`, `(l & r)`, `(l | r)`, `(l -> r)`, `(l <-> r)`, atoms bare, `true`/`false` lowercase. Non-Formula input to `variables/size/to_str` -> TypeError.
- Do not touch the dataclass decorators (frozen=True is part of the contract).

**Rules.** Remove `raise NotImplementedError` only in the functions this task owns. Keep docstrings. No new dependencies. 2 attempts total.
