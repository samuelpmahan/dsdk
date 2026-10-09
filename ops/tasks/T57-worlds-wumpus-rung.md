# T57-worlds-wumpus-rung

**Goal.** Implement the probability rung and the agents in `src/dsdk/worlds/wumpus.py`: `stuck_risk`, `provably_safe`, `run_agent`, `sweep_rates`, `frac`, `lab_data`. The numbers must come from calling `dsdk.prob` (`ask` with the knowledge as TEXT, `expectation`, `prior_belief`) and `dsdk.logic.entails`.

**Files to edit.** `src/dsdk/worlds/wumpus.py` only, and only the six functions above (the other card owns the cave basics, which must already be implemented). Do NOT edit any file under `tests/`, `fixtures/`, `tracks.toml`, `tracks/`, `ops/`, `lab/`, `tools/`. Read the module docstring ("What the agent knows" and "Probability model") and each stub docstring, then `tests/worlds/test_worlds_wumpus.py`, then `ask` in `src/dsdk/prob/ask.py` and `expectation` in `src/dsdk/prob/expect.py`.

**Done when.** `cd /home/user/dsdk && .venv/bin/python -m pytest tests/worlds/test_worlds_wumpus.py -q` passes (exit 0; the whole sweep takes about 20 s). Also `cd /home/user/dsdk && .venv/bin/python -m pytest tests/core tests/logic tests/graph tests/prob tests/test_reuse.py -q` must stay green.

**Depends on.** the previous card (cave basics)

**Pitfalls.**
- Do NOT enumerate worlds or do probability arithmetic yourself: no `itertools`, no `product(`, no `Belief(`, no `WeightedWorld`. A test fails if the module source contains them. Build the pit belief with `prior_belief({"P" + name(c): PIT_PRIOR for c in frontier})` and ask `ask(belief, "P13", pit_text)` where `pit_text = conjunction(pit_sentences)`.
- The Wumpus belief is `prior_belief({}, parse_formula(exactly_one_text, relaxed=True))` over the frontier variables `Wxy` plus ONE extra variable `WR`; `exactly_one_text` is "(W.. | W.. | WR)" AND-ed with `~(a & b)` for every pair. All its worlds weigh 1 (no priors). Ask `ask(belief, "W13", wumpus_text)`. `WR` is needed so that the "no stench anywhere" case is still satisfiable.
- `death = 1 - (1 - pit) * (1 - wumpus)` with `Fraction` values. `expected_pits` is `expectation(pit_belief, "(if P13 then 1 else 0) + (if P22 then 1 else 0) + ...", pit_text)`.
- If any `ask` or `expectation` is not KNOWN, return `Judgment(Status.INVALID, None, <that judgment's reason>)` (the reason starts "evidence has probability zero" for impossible percepts). An empty frontier is KNOWN with `StuckRisk((), Fraction(0))`.
- `provably_safe`: parse each sentence with `parse_formula(text, relaxed=True)` and use `entails(pit_formulas, Not(Var("P13")))` AND `entails(wumpus_formulas, Not(Var("W13")))`; a square is safe only when both hold.
- `run_agent`: follow the numbered loop in its docstring exactly. Check glitter FIRST, then "has gold -> escape", then provably safe squares (visit the FIRST of them each time, then re-derive), then stuck. Append `dict(percepts)` (a COPY) to `stuck` each time. For the probabilistic agent drop squares with `death == 1`, pick `min(options, key=lambda r: (r.death, r.cell))`, append it to `gambles` BEFORE entering it, and if the square is a pit or holds the Wumpus return `"died"`. A square entered safely gets its percept (`percept(cave, c, has_gold)`).
- `frac(x)` is `f"{x.numerator}/{x.denominator}"` (so zero is `"0/1"`). `lab_data`: iterate the demo cave then `seeded_cave(s)` for each seed, BOTH agents, collecting each stuck state once by `state_key` (compute `stuck_risk` only for new keys); the frontier rows are `[name, pit, wumpus, death]` as `frac` strings.

**Rules.** Use ONLY file reading/editing and Bash for pytest. Never create sessions, triggers, agents or remote resources. Do not run git commands that change state. Remove `raise NotImplementedError` only in the functions this task owns. Keep docstrings and the existing imports. Standard library only. Public API of `dsdk.core` / `dsdk.logic` only. 2 attempts total.
