# T53-worlds-six-degrees

**Goal.** Implement `SixDegrees.__init__`, `SixDegrees.hop`, `SixDegrees.query` and `six_degrees` in `src/dsdk/worlds/networks.py` (plus private helpers): shortest transition paths with a Judgment and per-hop evidence.

**Files to edit.** `src/dsdk/worlds/networks.py` only; touch ONLY these (T52 owns the graph builders). Do NOT edit any file under `tests/`, `fixtures/`, `tracks.toml`, `tracks/`, `ops/`. Read the `SixDegrees.query` docstring twice: it is a decision table with exact reason strings. Read `src/dsdk/graph/evidence.py` (`reachable`, `candidate_path`) and `src/dsdk/graph/traverse.py` (`shortest_path`); `tests/worlds/test_worlds_degrees.py` compares the result with an independent brute-force oracle on 40 random worlds.

**Done when.** `cd /home/user/dsdk && .venv/bin/python -m pytest tests/worlds -q` passes (exit 0). Also `cd /home/user/dsdk && .venv/bin/python -m pytest tests/core tests/logic tests/graph tests/test_reuse.py -q` must stay green.

**Depends on.** T50, T51, T52, T54

**Pitfalls.**
- Write NO search code: no heap, no queue, no loops over edges. The Judgment is `dsdk.graph.reachable(self.graph, source, target)`; the witness path is `shortest_path(self.known, ...)` when the judgment is KNOWN and `candidate_path(self.graph, ...)` when it is UNKNOWN (that returns `None` for the open-world case). A test fails if the module mentions `heapq` or `deque`.
- Nodes are track KEYS (strings). `query` first rejects anything that is not a track key (a non-`str`, or a `str` for which `self.graph.has_node(...)` is false) with `Judgment(Status.INVALID, None, f"node {x!r} is not in the graph")`, naming the source if both are bad. Unhashable arguments (a list) must not raise.
- `__init__` sets `self.graph = six_degrees_graph(world)` and `self.known = known_subgraph(self.graph)` and builds two evidence tables: for each observed `(source_key, target_key)` the transition count and the set of `(group, date)` pairs; for each track key the set of `(group, date)` pairs it was played in.
- `hop(a, b)`: ask `self.graph.get_edge(a, b)`; `None` -> `ValueError(f"no edge {a} -> {b}")`. The `evidence` is the edge's own. KNOWN: count = number of transition ROWS (not sets), sets = the distinct `(group, date)` pairs. UNKNOWN: sets = the intersection of the two tracks' set tables, count = its size. `sets` is sorted by `(group, date)` with `None` dates first (use `-1` for `None` in the sort key).
- `hops` is `tuple(self.hop(u, v) for u, v in zip(path, path[1:]))`, or `()` when there is no path or a one-node path.

(`dsdk.graph` and `dsdk.prob` public API is allowed too.)

**Rules.** Use ONLY file reading/editing and Bash for pytest. Never create sessions, triggers, agents or remote resources. Do not run git commands that change state. Remove `raise NotImplementedError` only in the functions this task owns. Keep docstrings and the existing imports. Standard library only. Public API of `dsdk.core` / `dsdk.logic` only. 2 attempts total.
