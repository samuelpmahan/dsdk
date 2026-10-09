# T25-graph-lineage-formula

**Goal.** Implement `lineage_graph`, `store_lineage_graph`, `formula_graph`, `formula_labels` in `src/dsdk/graph/bridges.py` (not `import_graph`).

**Files to edit.** `src/dsdk/graph/bridges.py` only (these four functions plus private helpers). Do NOT edit any file under `tests/`, `fixtures/`, `tracks.toml`, `tracks/`, or functions owned by other tasks. Read the whole module docstring and every stub docstring first: they are the spec, including exact strings and tie-breaks. Read the tests named in the done command before coding.

**Done when.** `cd /home/user/dsdk && uv run pytest tests/graph/test_graph_bridges.py -q -k "lineage or formula"` passes (20 tests). (exit 0). Also `cd /home/user/dsdk && uv run pytest tests/core tests/logic tests/test_reuse.py -q` must stay green (it passes today).

**Depends on.** T20, T21, T22 (the tests call `bfs`, `find_cycle`, `topological_order`)

**Pitfalls.**
- Lineage nodes are the `Part` objects themselves. `Part` compares by identity, so a `dict` / `set` keyed by the Part (or by `id(part)`) is correct. Never compare Parts by `.value`.
- Walk backwards from `part` with a `collections.deque` (BFS). Expanding a composed Part `p` (`c = p.composition`, not `None`): discover `c.calculation` FIRST, then `c.inputs.values()` in mapping order; list each Part once at first discovery; `nodes[0] is part`. Edges: `Edge(c.calculation, p, label=CALCULATION_LABEL)` and `Edge(inp, p, label=name)` for each `(name, inp)` in `c.inputs.items()`. Evidence stays the default KNOWN. Build with `Graph.from_edges(edges, nodes, directed=True, closed_world=True)`; the merge rule in `Graph` joins the labels when one Part is passed under two names.
- `store_lineage_graph(store)`: run the same walk from each `part` in `[p for _, p in store.entries()]` sharing one `seen` set, so the node order is the first part's lineage, then new nodes from the next, and so on. An empty store gives `Graph.from_edges([], (), directed=True, closed_world=True)`. Type checks: `isinstance(part, Part)` / `isinstance(store, PxC)` else `TypeError` (a string address is NOT a Part).
- `formula_graph`: iterative preorder with an explicit stack. Pop `(node, parent_id, label)`, assign `my_id = counter`, increment the counter, add the edge from the parent, then push the children in REVERSE order so the left child is numbered first. Child field names come from `FORMULA_CHILD_LABELS[type(node)]` (`Not` -> `"operand"`; binary -> `"left"`, `"right"`); `Const` and `Var` have none. Nodes are `range(counter)`; edges label the child edge; `closed_world=True`. A 2,000-deep `Not` chain is tested.
- `formula_labels`: the same preorder, producing `"Var:a"`, `"Const:True"`, or the class name (`type(node).__name__`) for operators.
- Reject non-`Formula` input with `TypeError` before any work. Do not use recursion anywhere in this file.

**Rules.** Use ONLY file reading/editing and Bash for pytest. Never create sessions, triggers, agents or remote resources. Do not run git commands that change state. Remove `raise NotImplementedError` only in the functions this task owns. Keep docstrings and the existing imports. Standard library only. Public API of `dsdk.core` / `dsdk.logic` only. 2 attempts total.
