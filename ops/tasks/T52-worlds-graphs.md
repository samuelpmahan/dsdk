# T52-worlds-graphs

**Goal.** Implement the four graph builders in `src/dsdk/worlds/networks.py`: `transition_graph`, `coselection_graph`, `dj_graph`, `six_degrees_graph` (plus private helpers such as a co-selection pair counter). NOT `SixDegrees` / `six_degrees` (task T53).

**Files to edit.** `src/dsdk/worlds/networks.py` only. Do NOT edit any file under `tests/`, `fixtures/`, `tracks.toml`, `tracks/`, `ops/`, or functions owned by other tasks. Read the module docstring (evidence vocabulary) and each stub docstring first. Read `dsdk/graph/model.py`'s module docstring (construction and merge rules) and `tests/worlds/test_worlds_graphs.py`.

**Done when.** `cd /home/user/dsdk && .venv/bin/python -m pytest tests/worlds/test_worlds_graphs.py -q` passes (exit 0). Also `cd /home/user/dsdk && .venv/bin/python -m pytest tests/core tests/logic tests/graph tests/test_reuse.py -q` must stay green.

**Depends on.** T50 (the loader: the real-corpus tests use `load_lostlands`)

**Pitfalls.**
- Always build with `Graph.from_edges(edges, nodes, directed=..., closed_world=False)`, passing `nodes=range(n)` explicitly so unplayed tracks stay as isolated nodes. Do not construct `Graph(...)` directly.
- Edge classes: use `Edge(source, target, weight, evidence, label)` with `Status.KNOWN` / `Status.UNKNOWN` from `dsdk.core`. Weights are plain ints (not bool). `Graph` raises `GraphError` if duplicate edges disagree on weight, so `six_degrees_graph` uses `weight=None` everywhere and lets the merge rule pick KNOWN and join labels.
- Co-selection works per SET: a set is the pair `(group, date)` over `world.selections`; use `world.sets()`. Count a pair once per set even if a track repeats inside the set; never create a self-loop for co-selection.
- `six_degrees_graph`: each co-selected pair gives BOTH directions as UNKNOWN; each distinct observed transition gives a KNOWN edge; a KNOWN self-loop (a track followed by itself) gets only the label `"transition"`.
- `dj_graph`: `by` must be one of `DJ_MODES`, else `ValueError`; weight = size of the intersection of DISTINCT track ids (or member artist ids); no edge when the intersection is empty.
- The real co-selection graph has 48,298 edges: build it with a dict counter and one `from_edges` call. Do not call `g.get_edge` or `g.neighbors` in loops (they scan every edge).

(`dsdk.graph` public API is allowed too.)

**Rules.** Use ONLY file reading/editing and Bash for pytest. Never create sessions, triggers, agents or remote resources. Do not run git commands that change state. Remove `raise NotImplementedError` only in the functions this task owns. Keep docstrings and the existing imports. Standard library only. Public API of `dsdk.core` / `dsdk.logic` only. 2 attempts total.
