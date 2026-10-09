# T21-graph-bfs-dfs-paths

**Goal.** Implement `bfs`, `shortest_path`, `dfs_preorder`, `dfs_postorder` in `src/dsdk/graph/traverse.py`.

**Files to edit.** `src/dsdk/graph/traverse.py` only (only these four functions; add a private helper above them if you want one). Do NOT edit any file under `tests/`, `fixtures/`, `tracks.toml`, `tracks/`, or functions owned by other tasks. Read the whole module docstring and every stub docstring first: they are the spec, including exact strings and tie-breaks. Read the tests named in the done command before coding.

**Done when.** `cd /home/user/dsdk && uv run pytest tests/graph/test_graph_traverse.py -q -k "bfs or shortest_path or test_dfs"` passes (26 tests). (exit 0). Also `cd /home/user/dsdk && uv run pytest tests/core tests/logic tests/test_reuse.py -q` must stay green (it passes today).

**Depends on.** T20

**Pitfalls.**
- ITERATIVE only. A 2,000-node path is tested and Python's default recursion limit is 1000. Do not call `sys.setrecursionlimit`.
- `bfs`: use `collections.deque`; call `g.index_of(source)` first so an absent source raises `MissingNodeError`. `distance` / `parent` / `order` exactly as the `BFSResult` docstring says (`parent[source] is None`; unreachable nodes absent; `order` is dequeue order). Neighbours come from `g.neighbors(u)` (already in node order): do not sort again.
- `shortest_path`: check BOTH nodes with `g.index_of` first (`MissingNodeError`), run `bfs`, return `None` when `target not in parent`, otherwise walk `parent` from `target` back to `source` and reverse into a tuple. `source == target` must return `(source,)`.
- DFS must follow the RECURSIVE definition. Use an explicit stack of `(node, iterator over g.neighbors(node))`; on each step advance the top iterator to its next UNMARKED neighbour, mark it, append it to the preorder list and push it; when the iterator is exhausted pop the node and append it to the postorder list. Pushing ALL neighbours at once gives a different order and fails `test_dfs_preorder_follows_the_recursive_definition` (expected `a, b, d, c`).
- Mark a node when it is first reached (preorder append and mark happen together). `source=None` loops over `g.nodes` in order and starts a new traversal from each unmarked node; `source` given validates it with `g.index_of` and traverses only from it. Return tuples.
- Share one private helper for `dfs_preorder` / `dfs_postorder` (they differ only in which list is returned).

**Rules.** Use ONLY file reading/editing and Bash for pytest. Never create sessions, triggers, agents or remote resources. Do not run git commands that change state. Remove `raise NotImplementedError` only in the functions this task owns. Keep docstrings and the existing imports. Standard library only. Public API of `dsdk.core` / `dsdk.logic` only. 2 attempts total.
