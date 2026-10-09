# T10-lang-calc-ast

**Goal.** Implement the Calc AST validation and structure helpers in `src/dsdk/lang/calc.py`: `Expr.__post_init__`, `size`, `free_vars`, `substitute`, `is_value`, `to_python`, `from_python`, `to_source`.

**Files to edit.** `src/dsdk/lang/calc.py` only, and only those eight functions. Do NOT edit the dataclass definitions, `OPS`, `Type`, `Outcome`, `StuckError`, any file under `tests/`, `fixtures/`, or `parse_calc`, `typecheck`, `step`, `classify`, `trace`, `evaluate` (other tasks own them).

**Done when.** `cd /home/user/dsdk && uv run pytest tests/lang/test_calc_ast.py -q` passes (exit 0). Then run `cd /home/user/dsdk && uv run pytest -q tests/core tests/logic tests/test_reuse.py` and confirm it still passes.

**Depends on.** none (start here, in parallel with T09).

**Pitfalls.**
- `Expr.__post_init__` is ONE method shared by all node classes: branch on `type(self)`. Required checks (see the module docstring): IntLit.value `type(v) is int` (`True` is rejected, TypeError); BoolLit.value `type(v) is bool` (TypeError); Var.name and Let.name: non-str is `TypeError`, then a name that does not `re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name, re.ASCII)` or is in `CALC_KEYWORDS` is `ValueError` (import `CALC_KEYWORDS` is already at the top of the file). Use `fullmatch`, not `match` or `$`: `"a\n"` must be rejected. BinOp.op not in `OPS` is `ValueError` (also for `None`); every child field (left, right, operand, cond, then, orelse, bound, body) must be an `Expr` else `TypeError` (a `dsdk.logic` Formula is not an Expr). Get the field list from `dataclasses.fields(self)`.
- Every public function starts by rejecting a non-Expr with `TypeError` (write one helper `_require_expr(x)`).
- `size`: counts nodes, the Let binder name is NOT a node. Use an explicit stack (depth-200 trees are tested).
- `free_vars` for Let is `free(bound) | (free(body) - {name})`: the name stays free in the BOUND expression (`let x = x in x` has free variable x).
- `substitute(e, name, value)`: argument checks first (`e` Expr, `name` str, `value` must be an `IntLit` or `BoolLit`, else `TypeError`). For `Let(y, b, body)`: ALWAYS substitute into `b`; substitute into `body` only when `y != name`. Rebuild nodes with the same class and fields. Plain recursion is fine for depth 200 (one Python frame per level).
- `to_python` returns `.value`; non-value Expr is `ValueError`, non-Expr is `TypeError`. `from_python` checks `isinstance(x, bool)` BEFORE `isinstance(x, int)`; anything else is `TypeError`.
- `to_source` strings are exact: `3`, `-3`, `true`, `false`, `x`, `(l op r)`, `(not e)`, `(if c then t else e)`, `(let x = b in body)`. Single spaces. A negative literal is printed with its minus sign and no parentheses (`(1 - -2)`).

**Rules.** Use ONLY file reading/editing and Bash for pytest. Never create sessions, triggers, agents or remote resources. Do not run git commands that change state. Remove `raise NotImplementedError` only in the functions this task owns. Keep docstrings. No new dependencies. 2 attempts total.
