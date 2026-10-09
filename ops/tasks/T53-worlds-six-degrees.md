# T53-worlds-six-degrees

**Goal.** Implement `SixDegrees.__init__`, `SixDegrees.hop`, `SixDegrees.query` and `six_degrees` in `src/dsdk/worlds/networks.py` (plus private helpers): shortest transition paths with a Judgment and per-hop evidence.

**Files to edit.** `src/dsdk/worlds/networks.py` only; touch ONLY these (T52 owns the graph builders). Do NOT edit any file under `tests/`, `fixtures/`, `tracks.toml`, `tracks/`, `ops/`. Read the `SixDegrees.query` docstring twice: it is a decision table with exact reason strings. Read `src/dsdk/graph/evidence.py` (`reachable`, `candidate_path`) and `src/dsdk/graph/traverse.py` (`shortest_path`): your answer must equal theirs; `tests/worlds/test_worlds_degrees.py` checks that on 40 random worlds.

**Done when.** `cd /home/user/dsdk && .venv/bin/python -m pytest tests/worlds -q` passes (exit 0). Also `cd /home/user/dsdk && .venv/bin/python -m pytest tests/core tests/logic tests/graph tests/test_reuse.py -q` must stay green.

**Depends on.** T50, T51, T52, T54

**Pitfalls.**
- Do NOT call `dsdk.graph.reachable` on the real graph: it scans all edges for every neighbour lookup and would take hours on 96,599 edges. Build adjacency lists ONCE in `__init__` from `self.graph.edges` (nodes are `range(n)`, edges are sorted, so each list is already in ascending target order).
- KNOWN case: breadth-first search over the known-only adjacency; a node's parent is its FIRST discoverer; stop when the target is discovered; `source == target` is the one-node path. It wins even if a shorter path exists through inferred edges.
- Candidate case: copy `candidate_path`'s algorithm onto adjacency lists: heap of `(inferred_count, hops, path_tuple)`, skip nodes already settled when popped AND when pushing, return the first popped path ending at the target.
- Reason strings are exact: `"known path: 0 -> 1"`, `"uncertain edges on best candidate path: 3->2 (unknown), 2->0 (unknown)"` (only the non-KNOWN hops), and the open-world sentence. `INVALID` for a non-int or out-of-range node: `bool` is NOT an int here (`isinstance(True, int)` is true in Python, so exclude it); name the source if both are bad; never raise.
- `hop(a, b)`: KNOWN iff the transition `a -> b` was observed: count = number of transition rows, sets = distinct `(group, date)` sorted with `None` dates first (use `-1` for None in the sort key). Otherwise UNKNOWN: sets = sets containing both tracks, count = their number. Else `ValueError(f"no edge {a} -> {b}")`.
- `__init__` must set `self.graph = six_degrees_graph(world)` and `self.known = known_subgraph(self.graph)` (the self-reuse test checks `known_subgraph` is used).

(`dsdk.graph` public API is allowed too.)

**Rules.** Use ONLY file reading/editing and Bash for pytest. Never create sessions, triggers, agents or remote resources. Do not run git commands that change state. Remove `raise NotImplementedError` only in the functions this task owns. Keep docstrings and the existing imports. Standard library only. Public API of `dsdk.core` / `dsdk.logic` only. 2 attempts total.
