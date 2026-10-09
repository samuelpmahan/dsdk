# T16-lang-bridge

**Goal.** Implement `from_formula`, `bind_assignment` and `trace_into_pxc` in `src/dsdk/lang/bridge.py`, the links from dsdk.lang to dsdk.logic and dsdk.core.

**Files to edit.** `src/dsdk/lang/bridge.py` only. Do NOT edit any file under `tests/`, `fixtures/`, `src/dsdk/core`, `src/dsdk/logic` or other lang modules. Read the docstring of `trace_into_pxc` word by word: it is the spec.

**Done when.** `cd /home/user/dsdk && uv run pytest tests/lang -q` passes (exit 0: ALL tests in tests/lang, including the fixture tests). Then run `cd /home/user/dsdk && uv run pytest -q tests/core tests/logic tests/test_reuse.py` and confirm it still passes.

**Depends on.** T09, T10, T11, T12, T13, T14, T15 (the bridge tests call the parsers, `typecheck`, `trace`, `evaluate`).

**Pitfalls.**
- `from_formula`: dispatch with `isinstance` on the `dsdk.logic` classes; shapes are exact: Const -> `calc.BoolLit`; Var -> `calc.Var` (a keyword name makes `calc.Var` raise ValueError: let it propagate); Not -> `calc.Not`; And/Or -> `calc.BinOp("and"/"or", ...)`; Implies(x, y) -> `BinOp("or", Not(T(x)), T(y))`; Iff -> `BinOp("==", ...)`. Non-Formula input is `TypeError` (check `isinstance(f, logic.Formula)`; a Calc node is NOT a Formula). Depth 200: plain recursion with one frame per level is fine.
- `bind_assignment`: first reject any value with `type(v) is not bool` (TypeError), then wrap from the inside out: iterate names in DESCENDING sorted order, `out = calc.Let(name, calc.BoolLit(v), out)`, so the smallest name ends up OUTERMOST. Empty assignment returns `e` itself (same object).
- `trace_into_pxc`: validate arguments FIRST, before touching the store (`prefix` not str -> TypeError, empty -> ValueError; `store` not a `PxC` -> TypeError; `expr` not a `calc.Expr` -> TypeError). Compute `steps = calc.trace(expr)` BEFORE opening the tick.
- Record dict (store ONLY plain dicts and strings, never AST objects: the store deep-copies values and a 100-deep AST would hit the recursion limit): `{"index": i, "source": calc.to_source(term), "outcome": calc.classify(term).value}`.
- Two calculation functions, each taking ONE argument `inputs` (a dict of input values): `load(inputs)` parses `inputs["program"]` with `calc.parse_calc` and returns the record for index 0; `advance(inputs)` takes `prev = inputs["prev"]`, parses `prev["source"]`, applies `calc.step`, and returns the record with index `prev["index"] + 1` of the result. They must compute from their inputs (a test feeds them other inputs and checks the outputs); never read the precomputed `steps` list inside them.
- Single atomic tick: `with store.tick(prefix) as tx:`; `head = tx.compose(f"px.{prefix}.0", Part(load), {"program": Part(calc.to_source(expr))})`; then for i in 1..n: `head = tx.compose(f"px.{prefix}.{i}", step_part, {"prev": head})` where `step_part = Part(advance)` is created ONCE before the loop and shared. Pass the Part object returned by the previous compose (not a copy and not an address string): the tests check identity along the chain. Do not call `store.set` or `store.compose` (they raise inside a tick), write nothing to `fn.*`/`sc.*`, and do not catch exceptions: an occupied address must propagate and the tick rolls back by itself. Return `head` after the `with` block.

**Rules.** Use ONLY file reading/editing and Bash for pytest. Never create sessions, triggers, agents or remote resources. Do not run git commands that change state. Remove `raise NotImplementedError` only in the functions this task owns. Keep docstrings. No new dependencies. 2 attempts total.
