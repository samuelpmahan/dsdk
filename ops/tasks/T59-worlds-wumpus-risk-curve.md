# T59-worlds-wumpus-risk-curve

**Goal.** Give the probabilistic agent a risk limit and draw the trade-off curve. In `src/dsdk/worlds/wumpus.py`: make `run_agent` honour `risk_limit`, make `sweep_rates` pass `risk_limit` on, implement `risk_curve` (the `CurvePoint` class and `RISK_LIMITS` already exist), and add `"curve"` to `lab_data`'s result.

**Files to edit.** `src/dsdk/worlds/wumpus.py` only. `run_agent`, `sweep_rates` and `lab_data` are ALREADY implemented and verified: start from the existing code and change only what this card says. Do NOT edit `tests/`, `fixtures/`, `tracks.toml`, `tracks/`, `ops/`, `lab/`, `tools/`. Read the docstrings of `run_agent` (the "Options" paragraph), `risk_curve`, `CurvePoint` and `lab_data`, then `tests/worlds/test_worlds_wumpus_limits.py`.

**Done when.** `cd /home/user/dsdk && .venv/bin/python -m pytest tests/worlds/test_worlds_wumpus_limits.py tests/worlds/test_worlds_wumpus.py -q` passes (exit 0; about two minutes, because every `exact_interval` call at 300 caves takes several seconds). Also `cd /home/user/dsdk && .venv/bin/python -m pytest tests/core tests/logic tests/graph tests/prob tests/test_reuse.py -q` must stay green.

**Depends on.** the free-gold card (it added the `exactly_one_wumpus` wiring this card builds on)

**Pitfalls.**
- `risk_limit=None` (default) must reproduce 146 died / 133 gold / 21 empty exactly. Convert a given limit with `to_prob(risk_limit, "risk_limit")` (so `0.2` is exactly `Fraction(1, 5)`; its `TypeError`/`ValueError` for a bool, a string, a negative number or a number above 1 must propagate). Then, if a limit was given and `probabilistic` is false, raise `ValueError("risk_limit needs probabilistic=True")`.
- The gamble options become: `r.death != 1` AND (no limit OR `r.death <= limit`), comparing exact `Fraction`s. A limit of 1 therefore still never picks certain death. Keep "pick the smallest death, ties to the smallest square" and record gambles as before.
- `risk_curve`: validate nothing yourself except "no seeds" (`ValueError("risk_curve needs at least one seed")`; turn `seeds` into a list first so a generator works). For each limit: `sweep_rates(seeds, probabilistic=True, exactly_one_wumpus=..., risk_limit=limit)`, then `exact_interval(died, caves)` and `exact_interval(gold, caves)`; the result's `limit` is `to_prob(limit, "risk_limit")`. No interval arithmetic of your own (a test fails on "sqrt", "comb(", "1.96", "wilson" in the module).
- SPEED: `exact_interval` at 300 caves takes several seconds, and the same counts come up again and again. Keep a module-level dict `{(count, caves): interval}` and reuse it. Also remember each stuck state's `stuck_risk` in a module-level dict keyed by `state_key(percepts)` so the sweeps do not recompute it. Without both, the tests may time out.
- `lab_data`: add `"curve"`: for each `CurvePoint` of `risk_curve(seeds)` a dict `{"limit": frac(limit), "caves", "died", "gold", "empty", "death": [low, high], "gold_ci": [low, high]}` (limits are text like `"0/1"`, `"1/5"`, `"1/1"`; intervals are floats). Leave the other keys alone.

**Rules.** Use ONLY file reading/editing and Bash for pytest. Never create sessions, triggers, agents or remote resources. Do not run git commands that change state. Remove `raise NotImplementedError` only in the functions this task owns. Keep docstrings and the existing imports. Standard library only. Public API of `dsdk.core` / `dsdk.logic` only. 2 attempts total.
