# T08-logic-structures

**Goal.** Implement `Tree.__post_init__`, `mirror`, `tree_size`, `tree_height`, `triangular` in `src/dsdk/logic/structures.py`.

**Files to edit.** `src/dsdk/logic/structures.py` only. Do NOT edit any file under `tests/`, `fixtures/`, `tracks.toml`, or other tasks' functions. Stub signatures and docstrings are the spec: read them before coding.

**Done when.** `uv run pytest tests/logic/test_structures.py -q` passes (exit 0). Also keep previously finished tasks green: `uv run pytest -q` must not regress anything you did not own.

**Depends on.** none

**Pitfalls.**
- `Tree.__post_init__` runs for Leaf too: only check Node's children are `Tree` (TypeError). Leaf accepts anything.
- mirror/size/height must reject non-trees with TypeError and work at depth 200 (plain recursion is OK at 200 for these, but an explicit stack is safer).
- `triangular` MUST loop (for/while/sum over range) and must NOT use `*`, `/`, `//` (a test inspects the source with `ast`); reject `bool` and `float` with TypeError via `type(n) is int`, negatives with ValueError. `triangular(200_000)` must be fast (a simple loop is fine).
- Height of a Leaf is 0, size of a Leaf is 1; Node: 1 + max / 1 + sum.

**Rules.** Remove `raise NotImplementedError` only in the functions this task owns. Keep docstrings. No new dependencies. 2 attempts total.
