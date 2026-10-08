# T05-logic-evaluate

**Goal.** Implement `evaluate` and `evaluate_partial` (strong Kleene) in `src/dsdk/logic/semantics.py`. Leave models/truth_table/entailment for T06.

**Files to edit.** `src/dsdk/logic/semantics.py` only. Do NOT edit any file under `tests/`, `fixtures/`, `tracks.toml`, or other tasks' functions. Stub signatures and docstrings are the spec: read them before coding.

**Done when.** `uv run pytest tests/logic/test_semantics.py -q -k "evaluate or kleene or partial or deep_not"` passes (exit 0). Also keep previously finished tasks green: `uv run pytest -q` must not regress anything you did not own.

**Depends on.** T04

**Pitfalls.**
- `evaluate` raises `UnassignedVariableError(name)` if ANY variable of the formula is missing, even when short-circuiting would avoid it; name = alphabetically first missing. Collect `variables(f)` first, then evaluate.
- Values must be real bools (`type(v) is bool`) else TypeError (for variables occurring in f).
- Kleene is TRUTH-FUNCTIONAL: compute each node's result from its children's three-valued results (T/F/None). Do NOT case-split on variables: `x | ~x` must be UNKNOWN. Tables are in the `evaluate_partial` docstring; Implies = Or(Not a, b); Iff is UNKNOWN when either side is.
- UNKNOWN judgment: `Judgment(Status.UNKNOWN, None, "unassigned: " + ", ".join(sorted(missing)))` with ALL missing variables of f; KNOWN: `Judgment(Status.KNOWN, bool_value, "")`.
- Depth 200: iterative post-order traversal (explicit stack), keyed by `id(node)` or a result stack. Identical sub-objects may appear twice in a tree, so cache by position/stack, not by equality.

**Rules.** Remove `raise NotImplementedError` only in the functions this task owns. Keep docstrings. No new dependencies. 2 attempts total.
