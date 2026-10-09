# A2 proof audit

Auditor: Manager W (Sonnet), who did not write `tracks/A2/PROOFS.md` or `src/dsdk/lang/calc.py`. Stance: adversarial, the proofs
are not trusted. Line numbers: `P` = `tracks/A2/PROOFS.md`, `C` = `src/dsdk/lang/calc.py`. Written here: this file and
`tracks/A2/audit/` only; PROOFS.md was not edited.

Mechanical evidence: `.venv/bin/python tracks/A2/audit/check_proofs.py 6` enumerates every Calc term of size <= 6 over atoms
`0, 1, true, false, x, y` with all 7 binary operators, `not`, `if`, and `let` with binder `x` or `y`: **278,028 terms**
(open and ill-typed ones included), against every typing environment for `x, y`. About 25 s. Result: **no counterexample to
any claim C1-C10** (listed in the script header). Counts: 79,208 typed steps checked for preservation, 11,498 closed typed
terms for progress, 90,426 steps for size decrease, 834,084 substitutions for Lemma S, 191,681 typed substitutions for the
substitution lemma. `tracks/A2/audit/negative_control.py` swaps in a call-by-name `let`; the checker then reports 17
counterexamples (preservation fails by variable capture, size grows), so the harness can fail.
Not covered: terms larger than 6 nodes (the property tests in `tests/lang/test_calc_properties.py` sample those).

## Verdicts

| Proof | Verdict |
|---|---|
| Lemmas: inversion, canonical forms, substitution (P20-35) | SOUND WITH GAPS (two small omissions, below) |
| 1. Preservation, case `if` (P37-52) | SOUND |
| 2. Preservation, case `+` (P54-70) | SOUND |
| (Preservation as a whole: P39 "Claim") | PARTIAL: 2 of 11 rule families proved; the claim itself is TRUE (mechanically confirmed) |
| 3. Progress (P74-95) | SOUND WITH GAPS (one case proved; claim true; corollary leans on Proof 4 without saying so) |
| 4. Termination by size (P98-128) | SOUND |
| Note on loops and halting (P130-end) | SOUND (a remark, not a proof) |

## Findings

1. **Preservation is claimed in general (P39) but only `if` and `+` are proved (P37-70).** P65 says `-` and `*` "are identical",
   which is right. The remaining families are not: `let` needs the substitution lemma applied to a typing environment that is
   extended (the L rule is the only one where the reduct is built by a function other than "pick a child" or "rebuild the
   node"), and `and`/`or` need the A2/A3 case split (reduct `false`, or the discarded/kept right operand). `==` on Bool pairs,
   `<`, `not` and the congruence of `let` are also unproved. The only mention of `let` is P30-35 (the lemma) and P111 (size).
   Mechanically the claim holds on all 79,208 typed steps, so this is a documentation gap, not a bug. Suggested fix: retitle P37
   and P54 "Preservation: cases `if`, `+`" and add a line "the other cases are the same shape; `let` is the substitution
   lemma", or prove `let` and `and` explicitly.
2. **Canonical forms is stated for the empty environment (P26) but applied under an arbitrary Γ (P61-62).** The statement is
   true for any Γ (values are literals, and the literal rules do not mention Γ), so nothing breaks, but P61's parenthetical
   "needs the values to be CLOSED literals" is misleading: the step needs only that a value is a literal. State the lemma for
   arbitrary Γ.
3. **Substitution lemma proof (P30-35) omits one subterm.** For `let y = b in body` with `y = x` it says "the body is untouched" and
   stops; the bound term `b` is still substituted (C `_subst`, the `Let` branch: `bound` is always searched) and needs the induction hypothesis.
   The conclusion is correct (C7 confirmed on 191,681 typed substitutions, shadowing included), the sentence is incomplete.
4. **Progress corollary (P92-96).** "repeating this reaches a value" needs termination, which is Proof 4, not Progress or
   Preservation. Add "(by Proof 4 the repetition ends)". Otherwise the corollary is right and checked (C6: for every closed typed
   term of size <= 6 the trace ends in a value of the static type).
5. **Proof 4 is correct, including the details I attacked.** The reduct sizes (P109-111): B3 3 -> 1, N 2 -> 1, A2 `2 + |r| -> 1`,
   A3 `2 + |r| -> |r|`, I-true `2 + |t| + |f| -> |t|` (P's `1 + 1 + s_t + s_f` agrees), L `2 + |body| -> |body|`. All consistent with `size` at C231-242
   (`Let` counts `1 + bound + body`). Lemma S holds for every term and every literal tested (C5: 834,084 substitutions).
   The bound `steps <= size - 1` (P116) holds for all 278,028 traces (C4). The call-by-name counterexample (P119-125) is exact:
   `let x = (1+1) in ((x*x)*x)` has size 9, the call-by-name reduct has size 11, and the real `trace` strictly decreases (C8).
   Side effect worth knowing: under call-by-name the same example also shows variable capture (negative control, preservation
   fails), which supports P's claim that closed-value substitution makes renaming unnecessary.
6. **A2/A3 discard the right operand unexamined (C step, `and` branch).** Confirmed (C9): `false and (1 + true)` steps to `false`
   though the term is ill-typed. This is consistent with the proofs because they only claim anything for WELL-typed terms; P89
   states the progress consequence correctly.
7. **Test references resolve.** `test_preservation_every_step_keeps_the_type`, `test_type_safety_*`,
   `test_every_step_strictly_decreases_the_size_measure`, `test_stuck_terms_are_ill_typed`, `test_substitution_lemma_*` all exist
   in `tests/lang/test_calc_properties.py`.
8. **Halting note.** `Omega = (lambda x. x x)(lambda x. x x)` reduces to itself; "timeout is not a proof of non-termination" and
   "total languages are not Turing-complete" are standard and correctly hedged. No claim about Calc depends on it.

## Not checked

The proofs say nothing about parsing or `evaluate` (big-step), and neither did I. Terms with more than 6 nodes were not
enumerated. Hypothesis tests were not re-run.
