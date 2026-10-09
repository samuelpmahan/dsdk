# T33-prob-bayesnet-graph

**Goal.** Implement `ancestors` and `ancestral_net` in `src/dsdk/prob/bayesnet.py`.

**Files to edit.** `src/dsdk/prob/bayesnet.py`, only those two functions. Do NOT edit any file under `tests/`, `fixtures/`, `tracks.toml`, `tracks/`, `ops/`, or functions owned by other tasks. The docstrings in the stub files are the spec: read them first (module docstring, then each function), then the tests named in the done command.

**Done when.** `cd /home/user/dsdk && uv run pytest tests/prob/test_bayesnet_graph.py -q` passes (exit 0). Then run `cd /home/user/dsdk && uv run pytest -q tests/core tests/logic tests/test_reuse.py` and confirm it still passes.

**Depends on.** T31, T32 (the tests build nets with `bayes_net`, and compare marginals of `joint_belief`).

**Pitfalls.**
- `ancestors`: `reached = bfs(net.structure.reverse(), node).distance`; the answer is a `frozenset` of the keys other than `node`. `bfs` raises `MissingNodeError` for an absent node by itself; do not catch it. `TypeError` first for a non-`BayesNet`.
- `ancestral_net`: argument checks first (non-BayesNet TypeError; `nodes` must be a `set` or `frozenset` of `str`, a list or str is a TypeError). `keep` = `nodes` plus the ancestors of every node in it (this raises `MissingNodeError` for unknown nodes).
- Keep the ORIGINAL node order: `order = [n for n in net.structure.nodes if n in keep]`. Keep only the edges whose endpoints are both in `keep` (copy `weight`, `evidence`, `label`), build with `Graph.from_edges(edges, order, directed=True, closed_world=net.structure.closed_world)`, and copy the CPTs of the kept nodes with fresh dicts (`dict(net.cpts[n])`) so the result does not share state with the original. Construct `BayesNet(sub, cpts)` directly; the pieces are already valid.
- Kept nodes keep all their parents (the set is closed under ancestors), so the CPT keys do not change.

**Rules.** Use ONLY file reading/editing and Bash for pytest. Never create sessions, triggers, agents or remote resources. Do not run git commands that change state. Remove `raise NotImplementedError` only in the functions this task owns. Keep docstrings. No new dependencies. 2 attempts total.
