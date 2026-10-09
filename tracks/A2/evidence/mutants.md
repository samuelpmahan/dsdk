# Mutation evidence: dsdk.lang (A2)

Commit `34fd121e2e10`. 592 mutation sites in the shipped source; 3 sampled with seed 20261009.
**3 killed, 0 survived** (100% kill rate).

Reproduce: `.venv/bin/python tools/mutants/run.py dsdk.lang tests/lang --max 3 --seed 20261009`

A survivor is either equivalent (no observable change) or a test gap. Each one is listed for triage.

## Survivors

| # | Where | Kind | Original | Mutant |
|---|---|---|---|---|

## Killed (first failing test)

| # | Where | Kind | Killed by |
|---|---|---|---|
| 0 | `src/dsdk/lang/calc.py:392` | negate-if | `tests/lang/test_bridge.py::test_source_round_trip_through_the_parser` |
| 1 | `src/dsdk/lang/calc.py:443` | int+1 | `tests/lang/test_calc_parse.py::test_comparison_is_non_associative` |
| 2 | `src/dsdk/lang/formula_syntax.py:204` | compare | `tests/lang/test_formula_syntax.py::test_relaxed_precedence_and_associativity[a` |
