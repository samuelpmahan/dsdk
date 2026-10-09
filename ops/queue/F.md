# Queue F (cards ready for Opus to dispatch under Manager F's name)

Manager F cannot spawn agents (the Agent tool is not in its toolset; checked 2026-10-09 with ToolSearch `select:Agent`:
no match). So ready cards go here.
Dispatch with: model haiku, subagent_type general-purpose, run_in_background true, implementer prompt from ops/MANAGERS.md.
Verify each result with the done command below (`.venv/bin/python -m pytest`, never `uv run`).
Log results: `python ops/ledger.py log <task> haiku <attempt> <outcome> <wall_s> --tests P/T --round <n> --note "F: ..."`

The card files still say `uv run pytest`; the implementer prompt in ops/MANAGERS.md tells Haiku to substitute
`.venv/bin/python -m pytest` with the same arguments.

## A2 lang (all five stubs and the tests exist; cards are final)

Wave order: [T09 + T10] -> [T11, T12, T13, T15] -> T14 -> T16 (integration gate).
All of calc.py is shared by T10-T14, so T10 and T11-T14 must NOT run on calc.py at the same time as each other
unless they own different functions (they do: each card names its own functions), but they DO edit the same FILE.
Safe pairs: T09 (lexer.py) with T10 (calc.py); in wave 2, T15 (formula_syntax.py) can run beside ONE calc.py card.
If two calc.py cards run concurrently, the second Haiku must re-read the file before every edit (str-replace edits are
atomic enough, but a whole-file rewrite would clobber the other card).

| Wave | Card | Done command (use .venv python) | Depends | Notes |
|---|---|---|---|---|
| 1 | T09 ops/tasks/T09-lang-lexer.md | `.venv/bin/python -m pytest tests/lang/test_lexer.py -q` | - | lexer.py only |
| 1 | T10 ops/tasks/T10-lang-calc-ast.md | `.venv/bin/python -m pytest tests/lang/test_calc_ast.py -q` | - | calc.py, 8 functions |
| 2 | T11 ops/tasks/T11-lang-calc-parse.md | `.venv/bin/python -m pytest tests/lang/test_calc_parse.py -q` | T09, T10 | calc.py parse_calc |
| 2 | T12 ops/tasks/T12-lang-calc-typecheck.md | `.venv/bin/python -m pytest tests/lang/test_calc_types.py -q` | T10 | calc.py typecheck |
| 2 | T13 ops/tasks/T13-lang-calc-step.md | `.venv/bin/python -m pytest tests/lang/test_calc_step.py -q` | T10 | calc.py step/classify/trace |
| 2 | T15 ops/tasks/T15-lang-formula-parse.md | `.venv/bin/python -m pytest tests/lang/test_formula_syntax.py -q` | T09 | formula_syntax.py |
| 3 | T14 ops/tasks/T14-lang-calc-evaluate.md | `.venv/bin/python -m pytest tests/lang/test_calc_eval.py tests/lang/test_calc_properties.py -q` | T10, T12, T13 | test_calc_properties is Hypothesis (10-50 s); run it ONCE at the end |
| 4 | T16 ops/tasks/T16-lang-bridge.md | `.venv/bin/python -m pytest tests/lang -q` | all above | integration gate: whole tests/lang |

Wave-2 note: while T11/T12/T13 are in flight, use `-k` filters on test_calc_properties.py (it needs evaluate/step/typecheck
together and is slow). Regression command for every card:
`.venv/bin/python -m pytest -q tests/core tests/logic tests/test_reuse.py`.

## A3 prob (contract written; see the bottom of this file once the T30-T38 cards exist)
