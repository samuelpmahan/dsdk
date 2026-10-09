# T58-worlds-wumpus-free-gold

**Goal.** Let the logic agent use the fact "exactly one Wumpus", as an explicit option. In `src/dsdk/worlds/wumpus.py`: implement `exactly_one_wumpus_text`, give `provably_safe` the keyword option `exactly_one_wumpus` (default `False`), and make `run_agent` pass that option to `provably_safe`.

**Files to edit.** `src/dsdk/worlds/wumpus.py` only. `provably_safe`, `run_agent` and `sweep_rates` are ALREADY implemented and verified: start from the existing code, keep it, and change only what this card says. Do not touch `risk_limit`, `risk_curve`, `lab_data` or any file under `tests/`, `fixtures/`, `tracks.toml`, `tracks/`, `ops/`, `lab/`, `tools/`. Read the new docstrings of `exactly_one_wumpus_text` and `provably_safe`, then the tests named in the done command.

**Done when.** `cd /home/user/dsdk && .venv/bin/python -m pytest tests/worlds/test_worlds_wumpus_limits.py -q -k "exactly_one_text or default_logic_is_unchanged or two_overlapping or probability_agrees or with_the_option or exactly_one_agent_is_stuck or default_logic_agent_still or exactly_one_logic_agent_finds"` passes (exit 0). Also `cd /home/user/dsdk && .venv/bin/python -m pytest tests/worlds/test_worlds_wumpus.py -q` must stay green (35 tests) and `.venv/bin/python -m pytest tests/core tests/logic tests/graph tests/prob tests/test_reuse.py -q`.

**Depends on.** none (the Wumpus cards already landed)

**Pitfalls.**
- The default MUST not change anything: with the option off, `provably_safe` and `run_agent` give exactly the answers they give today (the page's logic agent reads 0 died / 71 gold / 229 empty over seeds 1 to 300).
- `exactly_one_wumpus_text(front)`: variables are `W{x}{y}` for each frontier square in the order given, then `WR`; the text is `"(" + " | ".join(names) + ")"` followed by `~(a & b)` for every pair (first variable against each later one, then the second, ...), everything joined with `" & "`. Check the exact string in the docstring example, and that an empty frontier gives `"(WR)"`.
- In `provably_safe` with the option on, parse that text with `parse_formula(text, relaxed=True)` and ADD it as one more formula to the WUMPUS formulas only (never to the pit formulas), then use the same `entails(wumpus_formulas, Not(Var("W.."))))` test as before. Skip it when the frontier is empty. A non-`bool` option raises `TypeError`.
- `run_agent` already has `exactly_one_wumpus` and `risk_limit` in its signature; wire ONLY `exactly_one_wumpus` (pass it to `provably_safe`). `sweep_rates` must pass `exactly_one_wumpus` on to `run_agent` too (leave `risk_limit` to the next card).
- Why it works: two overlapping stenches (at (1,2) and (2,1)) with exactly one Wumpus force it onto (2,2), so (1,3) and (3,1) become provably safe; the tests check that logic with the option proves EXACTLY the squares that `stuck_risk` gives death chance 0.

**Rules.** Use ONLY file reading/editing and Bash for pytest. Never create sessions, triggers, agents or remote resources. Do not run git commands that change state. Remove `raise NotImplementedError` only in the functions this task owns. Keep docstrings and the existing imports. Standard library only. Public API of `dsdk.core` / `dsdk.logic` only. 2 attempts total.
