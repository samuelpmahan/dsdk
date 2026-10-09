# T22-graph-cycles-topo-components

**Goal.** Implement `find_cycle`, `topological_order`, `components`, `strongly_connected_components` in `src/dsdk/graph/traverse.py`.

**Files to edit.** `src/dsdk/graph/traverse.py` only (only these four functions plus private helpers; do not change `bfs`, `shortest_path`, `dfs_*`, `CycleError`, `BFSResult`). Do NOT edit any file under `tests/`, `fixtures/`, `tracks.toml`, `tracks/`, or functions owned by other tasks. Read the whole module docstring and every stub docstring first: they are the spec, including exact strings and tie-breaks. Read the tests named in the done command before coding.

**Done when.** `cd /home/user/dsdk && uv run pytest tests/graph/test_graph_traverse.py -q` passes (59 tests). (exit 0). Also `cd /home/user/dsdk && uv run pytest tests/core tests/logic tests/test_reuse.py -q` must stay green (it passes today).

**Depends on.** T20, T21

**Pitfalls.**
- ITERATIVE only (2,000-node cycle and path tests). Keep the recursion-free `(node, iterator)` stack pattern from T21.
- `find_cycle` keeps THREE things while running the DFS: a `state` dict (absent = unvisited, on the current stack, or finished), the current `path` list (same order as the stack), and `parent` of each node. For each neighbour `w` of the top node `u`: if `w` is on the stack and NOT (undirected and `w == parent[u]` and `w != u`), return `tuple(path[path.index(w):]) + (w,)`; elif `w` is unvisited, push it; a FINISHED node is ignored (a diamond `a->b, a->c, b->d, c->d` has NO cycle: using one `visited` set for both meanings is the classic bug). Roots are tried in `g.nodes` order. Undirected graphs: the parent check is only about skipping the edge you just came along.
- `topological_order`: raise `GraphError` for an undirected graph FIRST (before looking at anything else, even for an empty-edged graph). indegree of `v` = `len(g.predecessors(v))` (a self-loop counts, so that node never becomes ready). Use `heapq` over node INDICES (`g.index_of`), not over node values: nodes may be of mixed or unorderable types. When fewer nodes than `len(g.nodes)` were emitted raise `CycleError(find_cycle(g))`.
- `components`: treat every edge as undirected (for directed graphs use `neighbors` AND `predecessors`). Output is CANONICAL: each component a tuple in node order, components sorted by the index of their first node; return a tuple of tuples. Sort by `g.index_of`, never by the node values themselves.
- `strongly_connected_components`: undirected graphs return `components(g)`. Directed: Kosaraju. `order = dfs_postorder(g)`; walk `reversed(order)`; for each unassigned node collect everything unassigned reachable in `g.reverse()` (iterative stack); canonicalise exactly like `components`. Empty graph returns `()`.
- The hypothesis tests compare against Floyd-Warshall and union-find oracles on random small graphs including self-loops and duplicate edges; trust the docstrings, not intuition (a self-loop never merges SCCs; an undirected 2-cycle `a-b` is NOT a cycle).

**Rules.** Use ONLY file reading/editing and Bash for pytest. Never create sessions, triggers, agents or remote resources. Do not run git commands that change state. Remove `raise NotImplementedError` only in the functions this task owns. Keep docstrings and the existing imports. Standard library only. Public API of `dsdk.core` / `dsdk.logic` only. 2 attempts total.
