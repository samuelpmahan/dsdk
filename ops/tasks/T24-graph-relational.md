# T24-graph-relational

**Goal.** Implement `two_hop_join`, `two_hop_pairs`, `two_hop_pairs_graph`, `two_hop_counts_graph`, `two_hop_matrix` in `src/dsdk/graph/relational.py`.

**Files to edit.** `src/dsdk/graph/relational.py` only. Do NOT edit any file under `tests/`, `fixtures/`, `tracks.toml`, `tracks/`, or functions owned by other tasks. Read the whole module docstring and every stub docstring first: they are the spec, including exact strings and tie-breaks. Read the tests named in the done command before coding.

**Done when.** `cd /home/user/dsdk && uv run pytest tests/graph/test_graph_relational.py -q` passes (13 tests). (exit 0). Also `cd /home/user/dsdk && uv run pytest tests/core tests/logic tests/test_reuse.py -q` must stay green (it passes today).

**Depends on.** T20 (uses `Graph.neighbors`, `adjacency_matrix`)

**Pitfalls.**
- `two_hop_join` is a literal nested loop over `records` (outer `r1`, inner `r2`, both in input order) appending `(r1[source], r2[target])` when `r1[target] == r2[source]`. Do NOT deduplicate: the duplicate-row test expects four `(a, c)` rows from two copies of `a->b` and two copies of `b->c`. A record without the key columns raises `GraphError` (catch `KeyError`).
- `two_hop_pairs` is `frozenset(two_hop_join(...))`.
- `two_hop_pairs_graph(g)`: `frozenset((a, c) for a in g.nodes for b in g.neighbors(a) for c in g.neighbors(b))`. Walks need not be simple, so `(a, a)` appears for `a->b->a` and for self-loops.
- `two_hop_matrix`: triple loop over `g.adjacency_matrix()` returning a tuple of tuples of ints (do not import numpy). `two_hop_counts_graph`: the nonzero entries of that matrix as `{(nodes[i], nodes[j]): count}`; an empty graph gives `{}`.
- The graph version counts DISTINCT middle nodes because `Graph.from_records` merges duplicate rows; the join counts row pairs. That difference is intended and is the point of the module docstring.

**Rules.** Use ONLY file reading/editing and Bash for pytest. Never create sessions, triggers, agents or remote resources. Do not run git commands that change state. Remove `raise NotImplementedError` only in the functions this task owns. Keep docstrings and the existing imports. Standard library only. Public API of `dsdk.core` / `dsdk.logic` only. 2 attempts total.
