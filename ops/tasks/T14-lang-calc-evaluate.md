# T14-lang-calc-evaluate

**Goal.** Implement the big-step reference evaluator `evaluate` in `src/dsdk/lang/calc.py`.

**Files to edit.** `src/dsdk/lang/calc.py` only, only the function `evaluate` (private helpers allowed). Do NOT edit any file under `tests/`, `fixtures/`, or other tasks' functions.

**Done when.** `cd /home/user/dsdk && uv run pytest tests/lang/test_calc_eval.py tests/lang/test_calc_properties.py -q` passes (exit 0). Then run `cd /home/user/dsdk && uv run pytest -q tests/core tests/logic tests/test_reuse.py` and confirm it still passes.

**Depends on.** T10, T12 (typecheck, used by the property tests), T13 (step/trace, the other half of the property tests).

**Pitfalls.**
- `evaluate` must be INDEPENDENT of the small-step code: do not call `step`, `trace` or `classify` (a test patches them to raise). Use an environment instead of substitution: a recursive helper `go(e, env)` returning a Python `int` or `bool`, with `env` a dict of name -> Python value.
- Semantics identical to the small-step rules: IntLit/BoolLit return `.value`. Var: unbound in env -> stuck. Not: operand value must satisfy `type(v) is bool` else stuck. If: cond must satisfy `type(c) is bool`; evaluate ONLY the chosen branch. Let: evaluate the bound expression FIRST in the current env (stuck there makes the whole thing stuck), then evaluate the body in a NEW dict `{**env, name: value}` (never mutate `env`: the binding must not leak out of the let). BinOp: evaluate LEFT first. For `and`/`or`: left must satisfy `type(l) is bool` else stuck; `and` with left False returns `False` WITHOUT evaluating the right; with left True returns the value of the right operand (whatever it is, even an int); `or` mirrors it. For `+ - * < ==`: evaluate right, then if `type(l) is int and type(r) is int` compute (`+ - *` give int, `< ==` give bool); elif the op is `==` and both are `bool`: `l == r`; else stuck.
- Use `type(x) is int` / `type(x) is bool`, never `isinstance(x, int)` (it is true for bools) and never rely on `True == 1`: `1 == true` is stuck.
- Stuck handling: raise a private exception inside the helper and catch it once in `evaluate`, then `raise StuckError(e)` where `e` is the argument of `evaluate` (a free variable, a wrong-type operand, ...). Non-Expr input is `TypeError`.
- Results are exact Python ints (no float, no overflow handling). Recursion is fine for depth 200 (about 1 frame per level).

**Rules.** Use ONLY file reading/editing and Bash for pytest. Never create sessions, triggers, agents or remote resources. Do not run git commands that change state. Remove `raise NotImplementedError` only in the functions this task owns. Keep docstrings. No new dependencies. 2 attempts total.
