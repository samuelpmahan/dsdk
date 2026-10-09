# T11-lang-calc-parse

**Goal.** Implement `parse_calc` in `src/dsdk/lang/calc.py`: a precedence-climbing parser over `tokenize(text, CALC_KEYWORDS)`.

**Files to edit.** `src/dsdk/lang/calc.py` only, only the function `parse_calc` (you may add private helpers above it). Do NOT edit any file under `tests/`, `fixtures/`, `lexer.py`, or other tasks' functions.

**Done when.** `cd /home/user/dsdk && uv run pytest tests/lang/test_calc_parse.py -q` passes (exit 0). Then run `cd /home/user/dsdk && uv run pytest -q tests/core tests/logic tests/test_reuse.py` and confirm it still passes.

**Depends on.** T09 (tokenize), T10 (node constructors and `to_source`, used by the round-trip tests).

**Pitfalls.**
- DEPTH: nesting depth 200 must not raise RecursionError, and a classic one-function-per-precedence-level recursive descent uses about 8 Python frames per parenthesis level and FAILS. Write ONE recursive function `expr(min_prec)` plus ONE `prefix(min_prec)` (so at most 2-3 frames per nesting level), with a loop for binary operators.
- Binary operator table (token kind -> (precedence, op string)): OR (1, "or"), AND (2, "and"), LT (4, "<"), EQEQ (4, "=="), PLUS (5, "+"), MINUS (5, "-"), STAR (6, "*"). All are left-associative: after consuming an operator with precedence `p`, parse the right operand with `expr(p + 1)`. Loop: `left = prefix(min_prec)`; while the next token is a binary operator with `prec >= min_prec`: consume, `right = expr(prec + 1)`, `left = BinOp(op, left, right)`.
- Comparison is NON-associative: remember (a local flag in the loop) that the last node built in this loop was a comparison (prec 4); if the next operator is another LT/EQEQ, stop the loop (return `left`). The leftover token then becomes the error "expected END" at the top level (or "expected RPAREN" inside parentheses). So `1 < 2 < 3` fails at offset 6.
- `prefix(min_prec)` handles the start of an operand: `LET` and `IF` ONLY when `min_prec == 0` (otherwise `1 + let x = 2 in x` must fail at the `let` with the operand-expected set); `NOT` only when `min_prec <= 3`, building `Not(expr(3))` (that makes `not 1 < 2` a `not` of the comparison, and `not a and b` a `(not a) and b`); `INT`; `MINUS` followed by `INT` is a negative literal `IntLit(-n)` (if the next token is not INT: ParseError at that token, expected exactly `{"INT"}`); `TRUE`/`FALSE`; `NAME` -> `Var`; `LPAREN` -> `expr(0)` then `RPAREN`. `let x = e1 in e2`: `LET NAME EQ expr(0) IN expr(0)`. `if`: `IF expr(0) THEN expr(0) ELSE expr(0)`.
- Errors: tokenize the WHOLE text first (so LexError wins). `ParseError(message, offset, expected)` where offset is the START of the offending token, or `len(text)` when tokens ran out. A required token (`eat(kind)`) that is missing gives `expected={kind}` (THEN, ELSE, EQ, IN, NAME, RPAREN). Wanting an operand gives `{"INT","MINUS","TRUE","FALSE","NAME","LPAREN"}` (you may add NOT/LET/IF where legal). After `expr(0)` at top level, any leftover token is a ParseError with `expected={"END"}` (the tests only require that END is in the set).
- `INT` text -> `int(text)` (exact, `007` is 7). Non-str input is `TypeError`. Empty or blank input is a ParseError at offset `len(text)`.
- Keywords are separate token kinds (LET, IN, IF, THEN, ELSE, AND, OR, NOT, TRUE, FALSE) so `letx` is a NAME and becomes `Var("letx")`.

**Rules.** Use ONLY file reading/editing and Bash for pytest. Never create sessions, triggers, agents or remote resources. Do not run git commands that change state. Remove `raise NotImplementedError` only in the functions this task owns. Keep docstrings. No new dependencies. 2 attempts total.
