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

## ON HOLD until Sam confirms the data sources (Opus, 2026-10-09). Contract, tests and cards are ready.

## READY (dsdk.worlds wave, 2026-10-09)

Package registered in tracks.toml (order 5). Stubs + tests are in place; every test in tests/worlds currently fails on the stubs
(a reference implementation passes all 229; the 'next-track model' card T52 now also wires dsdk.prob and T53 calls dsdk.graph instead of searching itself). Cards, in dispatch order. Slots: 2 at a time.

Wave 1 (dispatch together, different files):
- [T50] ops/tasks/T50-worlds-lostlands-loader.md   done: `.venv/bin/python -m pytest tests/worlds/test_worlds_lostlands.py -q -k "not provenance"`
- [T54] ops/tasks/T54-worlds-buildlog.md           done: `.venv/bin/python -m pytest tests/worlds/test_worlds_buildlog.py -q`
Wave 2 (after T50; T52 and T51 touch different files):
- [T52] ops/tasks/T52-worlds-graphs.md             done: `.venv/bin/python -m pytest tests/worlds/test_worlds_graphs.py -q`      (networks.py)
- [T51] ops/tasks/T51-worlds-provenance.md         done: `.venv/bin/python -m pytest tests/worlds/test_worlds_lostlands.py tests/worlds/test_worlds_self_reuse.py -q -k "not networks"` (lostlands.py)
Wave 3 (after T50, T51, T52, T54 are green; same file as T52, so strictly after it):
- [T53] ops/tasks/T53-worlds-six-degrees.md        done: `.venv/bin/python -m pytest tests/worlds -q`

Each card also requires `.venv/bin/python -m pytest tests/core tests/logic tests/graph tests/test_reuse.py -q` to stay green.
Test file sizes: all of tests/worlds takes ~30 s. Haiku must NOT edit tests/worlds/*, fixtures/worlds/*, or tracks.toml.

## READY, not on hold (Opus, 2026-10-09): dsdk.prob made load-bearing through the build ledger
- [T55] ops/tasks/T55-worlds-buildlog-summary.md   done: `.venv/bin/python -m pytest tests/worlds/test_worlds_buildlog_summary.py tests/worlds/test_worlds_buildlog.py -q`
  Adds only two functions to the verified buildlog.py. Needs no Lost Lands data decision. When it passes, tests/test_stack.py's strict
  waiver "prob owed to worlds" flips (xpass-strict), and Opus removes it. tools/lab/build_lab.py already calls these functions: until the
  card lands the Lab shows "waiting for dsdk" for the first-try tiles; after, it shows dsdk's numbers plus "page recomputes: agree".

## READY (Opus, 2026-10-09): the probability rung for the Logic Cave (two cards, no data decision needed)
- [T56] ops/tasks/T56-worlds-wumpus-caves.md   done: `.venv/bin/python -m pytest tests/worlds/test_worlds_wumpus.py -q -k "random_stream or demo_cave_is or seeded_caves or neighbours or percepts_in_the_demo or frontier_is or knowledge_sentences or square_without or state_key"`
- [T57] ops/tasks/T57-worlds-wumpus-rung.md    done: `.venv/bin/python -m pytest tests/worlds/test_worlds_wumpus.py -q`   (after T56; same file)
  tools/lab/build_lab.py calls dsdk.worlds.wumpus.lab_data(); until T57 lands the Lab shows the pending state.
