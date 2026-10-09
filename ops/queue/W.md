# Queue W (cards ready for Opus to dispatch under Manager W's name)

Manager W cannot spawn agents (no Agent tool in its toolset), so ready cards go here.
Dispatch with: model haiku, subagent_type general-purpose, run_in_background true, implementer prompt from ops/MANAGERS.md.
Log results: `python ops/ledger.py log <task> haiku <attempt> <outcome> <wall_s> --tests P/T --round <n> --note "W: ..."`

## READY

- [T26] ops/tasks/T26-graph-import-graph.md
  Done command (use .venv, never uv run):
  `cd /home/user/dsdk && .venv/bin/python -m pytest tests/graph tests/test_reuse.py tests/core tests/logic -q`
  Today: 17 failed (all import_graph), 922 passed. Owns only src/dsdk/graph/bridges.py::import_graph.
  NOTE: the T26 tests read tracks.toml. Once dsdk.worlds is registered, `test_import_graph_nodes_are_exactly_the_registered_packages` also needs dsdk.worlds/prob/lang importable packages; dispatch T26 BEFORE any new package is registered, or after F/W stubs exist.
