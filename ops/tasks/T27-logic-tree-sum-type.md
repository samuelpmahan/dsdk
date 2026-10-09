# T27-logic-tree-sum-type (fix from proof re-audit AUDIT-2 N2)

**Goal.** Make `Tree` in `src/dsdk/logic/structures.py` an abstract sum type:
- `Tree()` itself raises `TypeError`.
- `Node` accepts only `Leaf` or `Node` children. An object that is a bare `Tree`, including one built with `Tree.__new__(Tree)`, raises `TypeError`.

**Files to edit.** `src/dsdk/logic/structures.py` only.

**Done when.** `cd /home/user/dsdk && uv run pytest tests/logic -q` exits 0.

**Depends on.** Nothing.

**Pitfalls.**
- Check the child type with `isinstance(child, (Leaf, Node))`, not `isinstance(child, Tree)`.
- Block direct instantiation in `Tree.__post_init__` with `if type(self) is Tree: raise TypeError(...)`. This is safe because `Leaf` and `Node` are subclasses.
- Leave every other function unchanged.

**Rules.** Use ONLY file reading/editing and Bash for pytest. Never create sessions, triggers, agents, messages or remote resources. Do not run git commands that change state.
