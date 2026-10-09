# T32-prob-bayesnet-build

**Goal.** Implement `bayes_net` and `joint_belief` in `src/dsdk/prob/bayesnet.py`.

**Files to edit.** `src/dsdk/prob/bayesnet.py`, only those two functions. Do NOT edit any file under `tests/`, `fixtures/`, `tracks.toml`, `tracks/`, `ops/`, or functions owned by other tasks. The docstrings in the stub files are the spec: read them first (module docstring, then each function), then the tests named in the done command.

**Done when.** `cd /home/user/dsdk && uv run pytest tests/prob/test_bayesnet_build.py -q` passes (exit 0). Then run `cd /home/user/dsdk && uv run pytest -q tests/core tests/logic tests/test_reuse.py` and confirm it still passes.

**Depends on.** T30, T31 (the tests call `probability` and `marginals`; `joint_belief` builds `Belief`/`WeightedWorld`).

**Pitfalls.**
- `bayes_net` checks run in the order listed in its docstring and the FIRST violated one raises. Types first (TypeError for non-Graph / non-Mapping), then `structure.directed` (ValueError), then every node is `str` (TypeError), then every edge has `evidence is Status.KNOWN` (ValueError naming the edge), then `dsdk.graph.find_cycle(structure)`: if it is not `None` raise `CycleError(cycle)` (already imported; a self-loop counts), then the CPT node set equals the node set (ValueError naming the missing/extra node), then each CPT row.
- `CycleError` is a subclass of `ValueError`: that is why the edge-evidence check must come BEFORE the cycle check (a test has an uncertain edge inside a cycle and expects a plain ValueError that is not a CycleError).
- CPT keys: for node `n`, `k = len(structure.predecessors(n))`. Every key must be a `tuple` of exactly `k` values with `type(v) is bool` (so `1`/`0` are rejected: ValueError), and there must be exactly `2**k` distinct keys (ValueError if rows are missing). A root has the single key `()`. Values go through `to_prob` (TypeError/ValueError propagate). A CPT that is not a Mapping is a `TypeError`.
- Store COPIES: build fresh dicts `{node: {key: Fraction}}` so later mutation of the caller's dicts does not change the net.
- `joint_belief`: `names = tuple(sorted(net.structure.nodes))`; raise `ValueError` if `len(names) > MAX_VARIABLES` before enumerating; use `dsdk.logic.models(Const(True), over=names)` for the worlds (all assignments, in the module order); the weight is the product over ALL nodes of `p` if the node is true else `1 - p`, where `p = net.cpts[n][tuple(model[q] for q in parents)]` and `parents = net.structure.predecessors(n)` (graph node order; NOT edge-listing order). The weights must sum to exactly `Fraction(1)`.
- `TypeError` for a non-`BayesNet` argument to `joint_belief`.

**Rules.** Use ONLY file reading/editing and Bash for pytest. Never create sessions, triggers, agents or remote resources. Do not run git commands that change state. Remove `raise NotImplementedError` only in the functions this task owns. Keep docstrings. No new dependencies. 2 attempts total.
