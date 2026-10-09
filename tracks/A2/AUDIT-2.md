# A2 proof audit, round 2

Auditor: Manager W (Sonnet), again; I did not write `tracks/A2/PROOFS.md` or `src/dsdk/lang/calc.py`. This round covers only what
changed in PROOFS.md after `tracks/A2/AUDIT.md`: Proof 2A (preservation for the remaining rules), the rewritten Substitution /
Exchange / Canonical-forms lemmas, the full Progress proof, and the type-safety corollary. Line numbers refer to the current
`tracks/A2/PROOFS.md` (P). PROOFS.md and the calc code were not edited.

Mechanical evidence: `.venv/bin/python tracks/A2/audit/check_proofs.py 6` (about 30 s) was extended with claims C11 to C15 and runs
on the same 278,028 terms (size 6 or less, open and ill-typed ones included, all four environments for `x, y`). Result: **no
counterexample to any of C1 to C15**. What the new checks do:
- **C11** classifies each step by an independent shape-based function that follows congruence down to the computation rule that fires
  (it does not call `step`), and checks preservation per rule. Every one of the 13 rules was exercised: B3 for `+ - * < ==`
  (928, 928, 928, 1,648, 3,296 typed steps), A2 and A3 (3,204 each), O2 and O3 (3,204 each), N (11,204), I-true and I-false (6,506
  each), and L (34,448). The check fails as vacuous if any rule is missing, and fails if `step` fires where the classifier sees no rule.
- **C12** canonical forms in all four environments: a typed value of type Int is an `IntLit`, Bool a `BoolLit`.
- **C13** both `let` sub-cases of the substitution lemma: 24,297 typed `let`s that shadow the substituted name and 24,297 that do not;
  the bound term is always substituted into and the body only when the binder differs (checked against `substitute`); the typing
  conclusion is preserved; the Exchange identities hold on environments.
- **C14** progress for every typing-rule family (`+ - * < ==`, `and`, `or`, `not`, `if`, `let`), each exercised on closed typed terms
  (196, 196, 196, 196, 972, 776, 776, 1,946, 1,000 and 5,240 terms).
- **C15** the three programs of the broken-proof exhibit: `if true then 1 else (1 + true)` and `false and (1 + true)` are ill-typed and
  not stuck, `let x = (1 + true) in 5` is ill-typed and stuck, and all three are in `fixtures/lang/calc_programs.json`.
`tracks/A2/audit/negative_control.py` (a call-by-name `let`) still makes the checker fail, now with 5,890 counterexamples, including the
new check that the classifier and `step` agree on which rule fires.

## Verdicts

| Part | Round 1 | Round 2 |
|---|---|---|
| Lemmas: inversion, canonical forms, substitution, exchange (P22-48) | SOUND WITH GAPS | SOUND |
| Proof 1 (if) and Proof 2 (+) | SOUND | SOUND (unchanged apart from the canonical-forms wording) |
| Proof 2A (remaining preservation rules, P84-111) | did not exist | SOUND |
| Preservation as a whole (P52) | PARTIAL | SOUND: every rule has a case |
| Proof 3 progress (P113-125) | SOUND WITH GAPS | SOUND |
| Type-safety corollary (P127-132) | SOUND WITH GAPS | SOUND (names termination) |
| Proof 4 termination, halting note | SOUND | SOUND (unchanged) |
| Broken-proof exhibit, new (P179-197) | did not exist | SOUND AS A FLAWED-PROOF EXHIBIT |

## My earlier findings

1. **Preservation proved for only `if` and `+`: CLOSED.** Proof 2A covers `<`, `==`, `and`, `or`, `not`, `let` and every congruence rule,
   and the Claim at P52 says which proof covers which rule. I checked each case against the real code, not only the text: `==` at
   mixed types cannot occur in a well-typed term; `and` A2 discards the right operand but the reduct is a Bool literal; `let` L uses the
   substitution lemma with the bound term a literal. C11 confirms preservation for all 13 computation rules on the enumeration.
2. **Canonical forms stated for the empty environment but used under an arbitrary Γ: CLOSED.** The lemma is now stated for any Γ and the
   proof says why (literal rules ignore Γ). C12 confirms it in all four environments. The Proof 2 parenthetical is corrected.
3. **Substitution lemma omitted the bound term: CLOSED.** Substitution is defined explicitly (bound term always substituted, body only
   when `y` differs), Exchange is stated, and both `let` sub-cases use the induction hypothesis on `b`. I re-derived the `y = x` case
   (`Γ[x:=T1][x:=U] = Γ[x:=U]`) and the `y ≠ x` case (exchange, then the hypothesis at `Γ[y:=U]`); both are correct. C13 exercises both
   sub-cases 24,297 times each.
4. **Progress corollary leaned on termination without saying so: CLOSED.** The corollary now says it ends "because of Proof 4" and why
   closedness is preserved (a typing derivation under the empty environment has no free variable). Progress covers every typing rule.
5. **Proof 4 correct: still CLOSED (no change needed).** The size accounting is unchanged and C3/C4/C5 still hold on all 278,028 terms.
6. **A2/A3 discard the right operand: still consistent.** The new `and` case in Proof 2A and the new broken-proof exhibit both rely on
   it correctly; C15 pins the behaviour.
7. **Test references resolve: still true.** The test names quoted in the rewritten text (`test_preservation_every_step_keeps_the_type`,
   `test_substitution_lemma_*`, `test_type_safety_*`, `test_stuck_terms_are_ill_typed`) exist in `tests/lang/test_calc_properties.py`.
8. **Halting note: unchanged and sound.**

## New findings (all minor)

- **Open, wording only: Lemma S (P138-142) says the let case with `y = x` "leaves `body` unchanged" and does not mention the bound term**,
  the same omission the typing lemma had. The size claim is still true (the induction hypothesis covers `b`), so nothing breaks, but the
  sentence should say that `b` is substituted into and keeps its size.
- **Open, wording only: the broken-proof exhibit's Rice-theorem remark (P194-197) is correct but stated as if it decided this exhibit.**
  The three counterexample programs already settle the false direction; the Rice remark explains why no checker can fix it. Fine as
  written; it could say "explains" rather than leaving the reader to guess the role.
- **Not a finding, a check worth recording:** the "After audit" table (P200-end) lists my findings 1 to 4 and nothing for 5 to 8, which is
  right, since those needed no change.

## Not checked

- Terms larger than 6 nodes were not enumerated (the property tests sample those).
- The rule classifier shares the term generator with the checker, but not code with `step`; it was written from the semantics in the
  `calc.py` docstring, not from the implementation.
- Parsing and the big-step `evaluate` are outside these proofs.
