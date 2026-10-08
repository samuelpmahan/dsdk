# T07-logic-proof

**Goal.** Implement `Step.__post_init__` and `check` in `src/dsdk/logic/proof.py`.

**Files to edit.** `src/dsdk/logic/proof.py` only. Do NOT edit any file under `tests/`, `fixtures/`, `tracks.toml`, or other tasks' functions. Stub signatures and docstrings are the spec: read them before coding.

**Done when.** `uv run pytest tests/logic/test_proof.py -q` passes (exit 0). Also keep previously finished tasks green: `uv run pytest -q` must not regress anything you did not own.

**Depends on.** T04

**Pitfalls.**
- Validate arity FIRST, then citation range (`0 <= c < i`), then the rule; the failure reason text format is pinned: `f"step {i} ({rule.value}): {detail}"`, detail contains 'cites' for arity problems and 'earlier' for citation-range problems.
- Cite ORDER is part of the contract: modus_ponens/modus_tollens cite (implication, other). and_intro builds `And(f[i], f[j])` in that order; i == j is allowed.
- or_intro_left: conclusion must be `Or` whose LEFT equals the cited formula (right side arbitrary); or_intro_right mirrors it.
- double_negation_elim strips exactly two `Not`s (`Not(Not(Not(p)))` gives `Not(p)`).
- Fallacies (affirming the consequent, denying the antecedent) fall out of strict structural matching: do not add 'helpful' leniency.
- Step: `type(c) is int` for each cite (bool rejected), `type(cites) is tuple`, `isinstance(rule, Rule)`.
- Stop at the FIRST invalid step. `premises` may be a generator: `list()` it once. Empty proof is valid with `CheckResult(True, None, "")`.

**Rules.** Remove `raise NotImplementedError` only in the functions this task owns. Keep docstrings. No new dependencies. 2 attempts total.
