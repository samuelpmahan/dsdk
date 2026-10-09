# T13-lang-calc-step

**Goal.** Implement the small-step semantics in `src/dsdk/lang/calc.py`: `step`, `classify`, `trace`.

**Files to edit.** `src/dsdk/lang/calc.py` only, only the functions `step`, `classify`, `trace` (private helpers allowed). Do NOT edit any file under `tests/`, `fixtures/`, or other tasks' functions (use `substitute`, `is_value` from T10 as given).

**Done when.** `cd /home/user/dsdk && uv run pytest tests/lang/test_calc_step.py -q` passes (exit 0). Then run `cd /home/user/dsdk && uv run pytest -q tests/core tests/logic tests/test_reuse.py` and confirm it still passes.

**Depends on.** T10.

**Pitfalls.**
- Transcribe the rule list of the module docstring exactly; `step` returns the reduct or `None` (value OR stuck). Non-Expr is `TypeError`. Recursion is fine (one frame per nesting level).
- Congruence pattern, used everywhere: if a child in an evaluation position is not a value, call `step(child)`; if that returns `None` the WHOLE term returns `None` (a stuck child blocks the parent, the right operand is never touched); otherwise rebuild the parent with the stepped child.
- BinOp for `+ - * < ==`: (1) left not a value -> step left; (2) else right not a value -> step right; (3) both values: if BOTH are `IntLit`: `+` `-` `*` give `IntLit`, `<` and `==` give `BoolLit`; if op is `==` and BOTH are `BoolLit`: `BoolLit(l.value == r.value)`; every other pair returns `None` (stuck). Decide with `isinstance(x, IntLit)` / `isinstance(x, BoolLit)`, NEVER by comparing `.value` across classes: Python says `True == 1` and the tests require `1 == true` to be stuck.
- BinOp `and` / `or` are DIFFERENT (short-circuit): (1) left not a value -> step left; (2) left is not a `BoolLit` -> `None`; (3) `and`: `BoolLit(False)` left -> result `BoolLit(False)` and the right operand is discarded WITHOUT being looked at (even if it is ill-typed or a free variable); `BoolLit(True)` left -> result is the right operand itself (not yet evaluated). `or`: `BoolLit(True)` left -> `BoolLit(True)`; `BoolLit(False)` left -> the right operand. Never step the right operand of and/or while the left is still being reduced.
- Not: operand not a value -> step it; `BoolLit(b)` -> `BoolLit(not b)`; `IntLit` -> `None`. If: cond not a value -> step cond; `BoolLit(True)` -> the `then` term; `BoolLit(False)` -> the `orelse` term; `IntLit` cond -> `None`. Let: bound not a value -> step bound (call-by-value: a stuck bound expression makes the whole let stuck even if the variable is unused); bound a value -> `substitute(body, name, bound)`. IntLit, BoolLit and Var -> `None`.
- `classify`: VALUE if `is_value(e)`, else STEP if `step(e) is not None`, else STUCK (a free `Var` is STUCK, not VALUE).
- `trace`: `out = [e]`; loop: `nxt = step(out[-1])`; if `None` return `out`; append. The result includes the start term and the final value-or-stuck term. A value gives `[e]`. Do NOT raise for stuck terms.

**Rules.** Use ONLY file reading/editing and Bash for pytest. Never create sessions, triggers, agents or remote resources. Do not run git commands that change state. Remove `raise NotImplementedError` only in the functions this task owns. Keep docstrings. No new dependencies. 2 attempts total.
