# T40-js-logic-parity (B3: Python/JS parity, first slice)

**Goal.** Implement every function in `viewer/parity/logic.mjs` so that the JS logic reproduces the Python-verified fixtures exactly. This is an independent implementation: do not read or port `src/dsdk/logic/*.py`. Work only from the JSDoc in `logic.mjs`, the tests, and the fixture JSON.

**Files to edit.** `viewer/parity/logic.mjs` only.

**Done when.** `cd /home/user/dsdk && node --test viewer/parity/*.test.mjs` exits 0.

**Depends on.** Nothing.

**Pitfalls.**
- The canonical string is fully parenthesised: `(~a)`, `(a & b)`, `(a | b)`, `(a -> b)`, `(a <-> b)`, with bare atoms and `true`/`false`. Compare your output against the fixture `string` fields.
- Enumeration order: names sorted, false before true, first name varies slowest (like nested loops with the first name outermost).
- `evaluate` must check that every variable is assigned before evaluating. Do not short-circuit past an unassigned variable.
- Use plain recursion or a stack. Fixture formulas are small.

**Rules.** Use ONLY file reading/editing and Bash for `node --test`. Never create sessions, triggers, agents or remote resources. Do not run git commands that change state. No npm installs. 2 attempts total.
