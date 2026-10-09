# T56-worlds-wumpus-caves

**Goal.** Implement the cave basics in `src/dsdk/worlds/wumpus.py`: `imul`, `mulberry32`, `demo_cave`, `seeded_cave`, `neighbours`, `percept`, `name`, `frontier`, `knowledge`, `conjunction`, `state_key`. NOT `stuck_risk`, `provably_safe`, `run_agent`, `sweep_rates`, `frac`, `lab_data` (the next card).

**Files to edit.** `src/dsdk/worlds/wumpus.py` only. Do NOT edit any file under `tests/`, `fixtures/`, `tracks.toml`, `tracks/`, `ops/`, `lab/`, `tools/`, or functions owned by the other card. Read the module docstring (the cave and the knowledge rules are the spec, down to sorting and text) and each stub docstring, then the tests named in the done command.

**Done when.** `cd /home/user/dsdk && .venv/bin/python -m pytest tests/worlds/test_worlds_wumpus.py -q -k "random_stream or demo_cave_is or seeded_caves or neighbours or percepts_in_the_demo or frontier_is or knowledge_sentences or square_without or state_key"` passes (exit 0). Also `cd /home/user/dsdk && .venv/bin/python -m pytest tests/core tests/logic tests/graph tests/prob tests/test_reuse.py -q` must stay green.

**Depends on.** none

**Pitfalls.**
- `mulberry32` must give the SAME numbers as the page's JavaScript. All arithmetic is on 32-bit unsigned integers: `state = (state + 0x6D2B79F5) & 0xFFFFFFFF; t = imul(state ^ (state >> 15), 1 | state); t = ((t + imul(t ^ (t >> 7), 61 | t)) & 0xFFFFFFFF) ^ t; result = ((t ^ (t >> 14)) & 0xFFFFFFFF) / 4294967296`, where `imul(a, b) = (a * b) & 0xFFFFFFFF` (JavaScript's `Math.imul`). The start value is `seed & 0xFFFFFFFF`. Check the three expected values in the first test.
- `seeded_cave`: build the 15 squares with `y` as the OUTER loop and `x` as the inner loop, skipping (1,1). Make THREE groups of draws in this order: first one draw per square for the pits (`rng() < 0.2`), then ONE draw for the Wumpus (`cells[math.floor(rng() * 15)]`), then ONE draw for the gold the same way. `pits` is a `frozenset`. A pit may share a square with the Wumpus or the gold; do not prevent it.
- `neighbours` returns a SORTED tuple of the squares inside 1..4; negative or zero coordinates are outside. `percept`: stench is true when the Wumpus is ON the square or next to it; glitter only while the gold is not yet carried.
- `knowledge` works on a dict `{cell: Percept}` whose keys are the visited squares; visit them in sorted order; the open neighbours of a square are its UNVISITED neighbours in sorted order; the sentence text format is exact (`"P13 | P22"`, `"~P12"`, names are `f"{x}{y}"` after the letter). A square with no open neighbours adds nothing.
- `frontier` returns a sorted tuple. `state_key` joins `f"{x}{y}{B or -}{S or -}"` for the squares in sorted order with `";"`. `conjunction` wraps each sentence in parentheses and joins with `" & "`, and an empty list gives `"true"`.

**Rules.** Use ONLY file reading/editing and Bash for pytest. Never create sessions, triggers, agents or remote resources. Do not run git commands that change state. Remove `raise NotImplementedError` only in the functions this task owns. Keep docstrings and the existing imports. Standard library only. Public API of `dsdk.core` / `dsdk.logic` only. 2 attempts total.
