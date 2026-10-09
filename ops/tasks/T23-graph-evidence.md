# T23-graph-evidence

**Goal.** Implement `known_subgraph`, `candidate_path`, `reachable` in `src/dsdk/graph/evidence.py`.

**Files to edit.** `src/dsdk/graph/evidence.py` only. Do NOT edit any file under `tests/`, `fixtures/`, `tracks.toml`, `tracks/`, or functions owned by other tasks. Read the whole module docstring and every stub docstring first: they are the spec, including exact strings and tie-breaks. Read the tests named in the done command before coding.

**Done when.** `cd /home/user/dsdk && uv run pytest tests/graph/test_graph_evidence.py -q` passes (21 tests). (exit 0). Also `cd /home/user/dsdk && uv run pytest tests/core tests/logic tests/test_reuse.py -q` must stay green (it passes today).

**Depends on.** T20, T21 (uses `Graph` and `shortest_path`)

**Pitfalls.**
- The decision table in the module docstring is the whole spec, including the EXACT reason strings. Copy them character for character, e.g. `"known path: a -> b -> c"`, `"uncertain edges on best candidate path: b->c (unknown)"` (edges joined by `", "`, each `f"{u}->{v} ({edge.evidence.value})"`), `"open world: no path found, but absence of an edge is not proof of impossibility"`, `"closed world: no path from a to c even counting uncertain edges"`, `"node 'ghost' is not in the graph"` (`repr` of the node). Build `Judgment` with `Status` members: `Judgment(Status.KNOWN, True, reason)`, `Judgment(Status.KNOWN, False, reason)`, `Judgment(Status.UNKNOWN, None, reason)`, `Judgment(Status.INVALID, None, reason)`.
- `reachable` checks in this order and returns at the first match: (1) either node absent -> INVALID (source named first; DO NOT raise); (2) a path in `known_subgraph(g)` via `shortest_path` -> KNOWN True; (3) a `candidate_path` -> UNKNOWN naming the uncertain edges; (4) closed world -> KNOWN False; (5) UNKNOWN open world.
- `known_subgraph`: `Graph.from_edges([e for e in g.edges if e.evidence is Status.KNOWN], g.nodes, directed=g.directed, closed_world=g.closed_world)`. Passing `g.nodes` keeps isolated nodes and the node order.
- `candidate_path`: Dijkstra with `heapq` over tuples `(uncertain_count, hops, index_path)` where `index_path` is a tuple of node INDICES (`g.index_of`); push `(0, 0, (index_of(source),))`; pop the smallest; skip it when its last node is already settled; return the nodes when the last index is the target's; otherwise push each neighbour's extension (`uncertain + (edge.evidence is not Status.KNOWN)`, `hops + 1`, `path + (j,)`). Get the edge with `g.get_edge(u, v)` (it works for undirected graphs in both directions). Validate both nodes with `g.index_of` first (`MissingNodeError`). `source == target` returns `(source,)`.
- In an undirected graph the reason names an uncertain edge in the direction the path WALKS it (`b->a`), so build the text from consecutive path nodes, not from `edge.source` / `edge.target`.
- KNOWN False needs `g.closed_world` AND no path at all counting every edge; a closed world with an uncertain path is still UNKNOWN.

**Rules.** Use ONLY file reading/editing and Bash for pytest. Never create sessions, triggers, agents or remote resources. Do not run git commands that change state. Remove `raise NotImplementedError` only in the functions this task owns. Keep docstrings and the existing imports. Standard library only. Public API of `dsdk.core` / `dsdk.logic` only. 2 attempts total.
