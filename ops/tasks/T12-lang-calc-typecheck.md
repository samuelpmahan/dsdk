# T12-lang-calc-typecheck

**Goal.** Implement `typecheck` in `src/dsdk/lang/calc.py`.

**Files to edit.** `src/dsdk/lang/calc.py` only, only the function `typecheck` (you may add private helpers above it). Do NOT edit any file under `tests/`, `fixtures/`, or other tasks' functions.

**Done when.** `cd /home/user/dsdk && uv run pytest tests/lang/test_calc_types.py -q` passes (exit 0). Then run `cd /home/user/dsdk && uv run pytest -q tests/core tests/logic tests/test_reuse.py` and confirm it still passes.

**Depends on.** T10 (`to_source` builds the error text; node constructors).

**Pitfalls.**
- Result is `Judgment(Status.KNOWN, Type.INT or Type.BOOL)` or `Judgment(Status.INVALID, None, reason)`. Never raise for an ill-typed program. Non-Expr input is `TypeError`.
- Reason text is EXACT: `f"{tag}: {to_source(node)}"` with tag one of `"unbound variable"` (node = the Var), `"operand type mismatch"` (node = the BinOp or Not), `"condition not Bool"` (node = the If), `"branch type mismatch"` (node = the If).
- ORDER: use one recursive helper `go(e, env)` that first computes the types of all children left to right (BinOp: left, right; If: cond, then, orelse; Let: bound, then body), and only afterwards applies the rule of the node itself. So the FIRST failure is the innermost-leftmost one: `(1 + true) + 2` reports `(1 + true)`. A common bug is checking the parent rule before visiting the children. Implement failure as a private exception carrying the reason, caught once in `typecheck`.
- Rules: `+ - *` need Int,Int and give Int; `<` needs Int,Int and gives Bool; `==` needs the SAME type on both sides (Int,Int or Bool,Bool) and gives Bool; `and`/`or` need Bool,Bool; `not` needs Bool. If: the cond must be Bool (check it BEFORE comparing the branches), then both branch types must be equal, and the result is that type. Compare types with `is` on the enum members.
- Let: type the BOUND expression in the current environment, then type the body in a NEW dict `{**env, name: bound_type}`. Never mutate the caller's `env` and never mutate a dict shared with a sibling (a let must not leak outside its body: `(let x = true in x) == (x < 3)` outside `x` is the env's x). `env=None` means empty; accept any Mapping (copy it with `dict(env)`).
- A Var not in the env is "unbound variable" with the Var as the node (so for `(x + 1)` the reason is `unbound variable: x`).
- Depth 200: plain recursion with one helper function (about 1 frame per level) is fine.

**Rules.** Use ONLY file reading/editing and Bash for pytest. Never create sessions, triggers, agents or remote resources. Do not run git commands that change state. Remove `raise NotImplementedError` only in the functions this task owns. Keep docstrings. No new dependencies. 2 attempts total.
