# A2 written proofs (Calc: types, small-step semantics, termination)

The code in `dsdk.lang.calc` is the executable counterpart of the proofs below. The Hypothesis properties in
`tests/lang/test_calc_properties.py` only SAMPLE these statements; the proofs establish them for ALL terms.
Rule names B1, B2, B3, A1-A3, O1-O3, N1, I1 and L1 are the ones in the `calc.py` module docstring; I-true, I-false, N and L are this note's shorthand for the I1 (true/false branch), N1 and L1 cases. `v` ranges over values
(`IntLit` / `BoolLit`). A closed term has no free variables.

## Setting

Typing judgment `Γ ⊢ e : T` with `T ∈ {Int, Bool}`:

    (T-Int)  Γ ⊢ n : Int                (T-Bool) Γ ⊢ b : Bool            (T-Var) Γ(x) = T  =>  Γ ⊢ x : T
    (T-Arith) Γ ⊢ l : Int, Γ ⊢ r : Int  =>  Γ ⊢ l ⊕ r : Int          for ⊕ in {+, -, *}
    (T-Lt)    Γ ⊢ l : Int, Γ ⊢ r : Int  =>  Γ ⊢ l < r : Bool
    (T-Eq)    Γ ⊢ l : T,   Γ ⊢ r : T    =>  Γ ⊢ l == r : Bool
    (T-Logic) Γ ⊢ l : Bool, Γ ⊢ r : Bool =>  Γ ⊢ l and r, l or r : Bool          (T-Not) Γ ⊢ e : Bool => Γ ⊢ not e : Bool
    (T-If)    Γ ⊢ c : Bool, Γ ⊢ t : T, Γ ⊢ e : T  =>  Γ ⊢ if c then t else e : T
    (T-Let)   Γ ⊢ b : T1, Γ[x:=T1] ⊢ body : T2  =>  Γ ⊢ let x = b in body : T2

Two lemmas are used everywhere.

**Inversion.** If `Γ ⊢ e : T` and `e` has a given shape, the premises of the (unique) typing rule for that shape hold. E.g.
`Γ ⊢ l + r : T` implies `T = Int`, `Γ ⊢ l : Int`, `Γ ⊢ r : Int`. *Proof:* exactly one typing rule has a conclusion of that
shape, so the derivation of the judgment ends with it. ∎

**Canonical forms.** For ANY environment `Γ`: if `Γ ⊢ v : Int` and `v` is a value then `v = IntLit(n)` for some integer `n`; if `Γ ⊢ v : Bool` then
`v = BoolLit(b)`. *Proof:* values are `IntLit` or `BoolLit`; by inversion `Γ ⊢ IntLit(n) : T` forces `T = Int` and `Γ ⊢ BoolLit(b) : T` forces `T = Bool`
(the literal rules do not mention `Γ`), so a value of type Int cannot be a `BoolLit` and vice versa. ∎ (Nothing here needs the value to be
closed: a value is a literal, and a literal has no variables. The statement is used below under arbitrary `Γ`.)

**Substitution.** `e[x:=v]` (for a literal `v`) replaces the free occurrences of `x`: `x[x:=v] = v`; `y[x:=v] = y` for `y ≠ x`; literals are unchanged; it commutes with
the other constructors; and for `let y = b in body`: `(let y = b in body)[x:=v] = let y = b[x:=v] in body'` where `body' = body` if `y = x` (the binder
shadows) and `body' = body[x:=v]` if `y ≠ x`. (This is `substitute` in `calc.py`; the bound term `b` is ALWAYS substituted into, because the binder `y` is not in scope in `b`.)

**Exchange.** If `y ≠ x` then `Γ[x:=A][y:=B] = Γ[y:=B][x:=A]`; and `Γ[x:=A][x:=B] = Γ[x:=B]`. (Environments are finite maps; a later binding of the same name overrides.)

**Substitution lemma.** If `Γ[x:=T1] ⊢ e : T` and `v` is a literal with `⊢ v : T1`, then `Γ ⊢ e[x:=v] : T`. *Proof:* structural induction on `e`, for ALL `Γ` at once
(the induction hypothesis is used at different environments). A literal `v` has the type `T1` under every environment, since the literal rules do not look at `Γ`.
* `e` a literal: unchanged, and its type does not depend on the environment. ✓
* `e = Var x`: `Γ[x:=T1] ⊢ x : T` gives `T = T1`; `e[x:=v] = v`, and `Γ ⊢ v : T1`. ✓  `e = Var y`, `y ≠ x`: `Γ[x:=T1](y) = Γ(y)`, so `Γ ⊢ y : T` and `y[x:=v] = y`. ✓
* `e` a `BinOp`, `Not` or `If`: invert the typing, apply the induction hypothesis to each child at the SAME `Γ`, rebuild with the same rule. ✓
* `e = let y = b in body`, inversion: `Γ[x:=T1] ⊢ b : U` and `Γ[x:=T1][y:=U] ⊢ body : T`. The induction hypothesis on `b` (same `Γ`) gives `Γ ⊢ b[x:=v] : U`; this is needed in BOTH sub-cases.
  *Case `y = x`:* the second premise reads `Γ[x:=U] ⊢ body : T` (the later binding overrides), and `e[x:=v] = let x = b[x:=v] in body`; T-Let applied to `Γ ⊢ b[x:=v] : U` and
  `Γ[x:=U] ⊢ body : T` gives `Γ ⊢ e[x:=v] : T`. ✓  *Case `y ≠ x`:* by exchange the second premise is `Γ[y:=U][x:=T1] ⊢ body : T`; the induction hypothesis on `body` at the
  environment `Γ[y:=U]` gives `Γ[y:=U] ⊢ body[x:=v] : T`; with `Γ ⊢ b[x:=v] : U`, T-Let gives `Γ ⊢ (let y = b[x:=v] in body[x:=v]) : T`. ✓ ∎
(Tested by `test_substitution_lemma_*`.)

---

## Proof 1 -- Preservation, case `if`

**Claim (Preservation).** If `Γ ⊢ e : T` and `e → e'` then `Γ ⊢ e' : T`. The proof is by cases on the last rule used for `e → e'`: Proof 1 treats `if`, Proof 2 treats `+` (and `-`, `*`), and Proof 2A below treats every other rule (`<`, `==`, `and`, `or`, `not`, `let`), so together they cover all rules. (Here `Γ` is arbitrary: no case below uses
closedness; a value is a literal and that is all the computation rules look at.)

Proof by induction on the derivation of `e → e'`, by cases on the last rule. We do the cases whose left-hand side is
`e = if c then t else f`. By inversion on `Γ ⊢ e : T`: **`Γ ⊢ c : Bool`, `Γ ⊢ t : T`, `Γ ⊢ f : T`.**

* **I1 (congruence):** `c → c'` and `e' = if c' then t else f`. Induction hypothesis on `c → c'` and `Γ ⊢ c : Bool` gives
  `Γ ⊢ c' : Bool`. With `Γ ⊢ t : T` and `Γ ⊢ f : T`, rule T-If gives `Γ ⊢ if c' then t else f : T`. ✓
* **I-true:** `c = BoolLit(True)` and `e' = t`. We already have `Γ ⊢ t : T` from inversion. ✓
* **I-false:** `c = BoolLit(False)` and `e' = f`. We already have `Γ ⊢ f : T`. ✓

No other rule has an `if` on the left. (Note what made this work: both branches have the SAME type `T` in T-If, so
whichever branch is chosen has type `T`. If T-If only required `t : T1` and `f : T2` with any types, I-true would change the
type of the program.) ∎

## Proof 2 -- Preservation, case `+`

Here `e = l + r`. By inversion on `Γ ⊢ e : T`: **`T = Int`, `Γ ⊢ l : Int`, `Γ ⊢ r : Int`.**

* **B1:** `l → l'`, `e' = l' + r`. IH on `l → l'` gives `Γ ⊢ l' : Int`; T-Arith gives `Γ ⊢ l' + r : Int`. ✓
* **B2:** `l = v` is a value, `r → r'`, `e' = v + r'`. IH gives `Γ ⊢ r' : Int`; with `Γ ⊢ v : Int`, T-Arith gives
  `Γ ⊢ v + r' : Int`. ✓
* **B3:** `l` and `r` are both values and the rule applied is the integer one. By canonical forms (valid under any `Γ`: it only uses that a value is a literal) `l = IntLit(a)` and `r = IntLit(b)`, and `e' = IntLit(a+b)`. By T-Int,
  `⊢ IntLit(a+b) : Int`, which is `T`. ✓

The rules for `-` and `*` are identical with `a-b`, `a*b`. The case that does NOT occur is "B3 on a non-Int pair"
(`1 + true`): there is NO rule for it, which is exactly why that term is stuck, and why inversion rules it out for
well-typed terms (it would need `Γ ⊢ true : Int`). ∎

*Where the tests fit:* `test_preservation_every_step_keeps_the_type` samples the claim on random well-typed programs; the
`let` case (Proof 2A) needs the substitution lemma and is sampled by `test_substitution_lemma_*`.

## Proof 2A -- Preservation, the remaining rules (`<`, `==`, `and`, `or`, `not`, `let`)

Same induction on the derivation of `e → e'`, same hypothesis `Γ ⊢ e : T`, `Γ` arbitrary. In every case congruence rules are one line: the stepped child keeps its type by the
induction hypothesis, the other children are unchanged, and the same typing rule rebuilds the node.

**`l < r`** (T-Lt: `T = Bool`, `Γ ⊢ l : Int`, `Γ ⊢ r : Int`). B1, B2 as in Proof 2 (the children stay Int). B3: by canonical forms `l = IntLit(a)`, `r = IntLit(b)` and `e' = BoolLit(a < b)`,
and `Γ ⊢ BoolLit(a < b) : Bool = T`. ✓

**`l == r`** (T-Eq: `T = Bool`, `Γ ⊢ l : S`, `Γ ⊢ r : S` with the SAME `S`). B1, B2: the stepped child keeps type `S`, so T-Eq rebuilds `Bool`. B3: both are values of the same type `S`, so by canonical
forms both are `IntLit` (if `S = Int`) or both `BoolLit` (if `S = Bool`); those are the only pairs that have a rule, and `e' = BoolLit(a == b)` has type `Bool = T`. The pair `IntLit`/`BoolLit` would need
`S = Int` and `S = Bool` at once, so it cannot occur in a well-typed term (this is why `1 == true` is stuck AND ill-typed). ✓

**`l and r`** (T-Logic: `T = Bool`, `Γ ⊢ l : Bool`, `Γ ⊢ r : Bool`). *A1:* `l → l'`, `e' = l' and r`: the induction hypothesis gives `Γ ⊢ l' : Bool`, T-Logic rebuilds `Bool`. (There is no rule that steps `r`.)
*A2:* `l = BoolLit(False)`, `e' = BoolLit(False)`: the reduct is a literal of type `Bool = T`; it does not matter that `r` is discarded unexamined, because the claim is only about the reduct's type. *A3:* `l = BoolLit(True)`,
`e' = r`: by inversion `Γ ⊢ r : Bool = T`. ✓ **`l or r`** mirrors it: O1 as A1; `BoolLit(True) or r → BoolLit(True)` is a `Bool` literal; `BoolLit(False) or r → r` and `Γ ⊢ r : Bool = T`. ✓

**`not e0`** (T-Not: `T = Bool`, `Γ ⊢ e0 : Bool`). N1: the induction hypothesis gives `Γ ⊢ e0' : Bool` and T-Not rebuilds. Computation: `e0 = BoolLit(b)` by canonical forms and `e' = BoolLit(not b)` has type `Bool`. ✓

**`let x = b in body`** (T-Let: `Γ ⊢ b : T1` and `Γ[x:=T1] ⊢ body : T`).
* *L1 (congruence):* `b → b'`, `e' = let x = b' in body`. The induction hypothesis gives `Γ ⊢ b' : T1` with the SAME `T1`; so the premise about `body` (under `Γ[x:=T1]`) is unchanged, and T-Let gives `Γ ⊢ e' : T`. ✓
* *L (computation):* `b = v` is a value and `e' = body[x:=v]`. By canonical forms `v` is a literal and `Γ ⊢ v : T1` is `⊢ v : T1` (literals do not use `Γ`). The substitution lemma, with `Γ[x:=T1] ⊢ body : T`,
  gives `Γ ⊢ body[x:=v] : T`. ✓ This is the one rule whose reduct is built by a function other than "pick a child" or "rebuild the node", and it is exactly why the substitution lemma was proved above for ALL environments and with the
  bound term always substituted into. The proof uses call-by-value twice: the rule only fires when `b` is a value (a literal), so the lemma's hypothesis "`v` is a literal" holds; and congruence L1 is what gets `b` there.

Every rule of the semantics now has a case (B1-B3 for `+ - * < ==`, A1-A3, O1-O3, N1 with its computation rule, I1 with both computation rules, L1 and L), so **Preservation holds for every well-typed term**, and the rule
that no step is possible for a literal or a variable needs no case. ∎

---

## Proof 3 -- Progress

**Claim (Progress).** If `⊢ e : T` (empty environment) then `e` is a value or there is an `e'` with `e → e'`.

Proof by induction on the typing derivation. The variable case is vacuous (`Γ` is empty, so `⊢ x : T` is not derivable). Literals are values. Inversion gives the premises of each case.
* **`l ⊕ r`, `l < r`, `l == r`** (premises `⊢ l : S`, `⊢ r : S'` with `S = S' = Int` for arithmetic and `<`, and `S = S'` for `==`). (1) If `l` is not a value, the induction hypothesis gives `l → l'`, so B1 applies.
  (2) Otherwise `l` is a value; if `r` is not a value the hypothesis gives `r → r'` and B2 applies. (3) Otherwise both are values of the same type; canonical forms give two `IntLit` or (for `==` at `Bool`) two `BoolLit`, and B3 applies.
* **`l and r`, `l or r`** (`⊢ l : Bool`). If `l` is not a value, A1 (O1) applies. Otherwise `l` is a value of type `Bool`, hence a `BoolLit` (canonical forms), and A2/A3 (O2/O3) apply WITHOUT looking at `r`, so progress for `and`/`or` does
  not even need `r` to be a value.
* **`not e0`** (`⊢ e0 : Bool`). If `e0` is not a value, N1 applies; otherwise `e0 = BoolLit(b)` and the computation rule applies.
* **`if c then t else f`** (`⊢ c : Bool`). If `c` is not a value, I1 applies; otherwise `c = BoolLit(b)` and I-true or I-false applies.
* **`let x = b in body`**. If `b` is not a value, the hypothesis on `⊢ b : T1` gives `b → b'` and L1 applies; otherwise `b` is a value and L applies (`substitute` is defined for every body and every literal).
Every typing rule is covered. ∎

**Corollary (type safety).** A closed well-typed term never gets stuck, and its evaluation ends in a value of the same type. *Proof:* by Progress, a closed well-typed term is a value or can step; by Preservation (with `Γ` empty) the reduct is
again well-typed under the empty environment, which also means it is closed (a typing derivation under the empty environment has no free variable). So the repetition "step, stay well-typed, stay closed" never reaches a stuck term. **It
ends because of Proof 4** (the size strictly decreases at each step, so there is no infinite sequence); without Proof 4 these two facts would only say that stuck is impossible, not that a value is reached. The final term is
not stuck and cannot step, so by Progress it is a value, and by Preservation its type is the original `T`. This is `test_type_safety_*` and `test_stuck_terms_are_ill_typed`.

---

## Proof 4 -- Termination by a decreasing measure

**Measure.** `size(e)` = number of AST nodes (the let binder name is not a node).

**Lemma S (substituting a literal keeps the size).** If `v` is a literal (size 1) then `size(e[x:=v]) = size(e)`.
*Proof:* structural induction. `Var x` (size 1) becomes `v` (size 1); every other `Var`/literal is unchanged; for compound
nodes the size is `1 + ` the sizes of the children, which are unchanged by IH; `let y = b in body` with `y = x` leaves `body`
unchanged. ∎

**Claim.** If `e → e'` then `size(e') < size(e)`.
Proof by induction on `e → e'`.
* **Computation rules.** B3: `1 + 1 + 1 = 3` becomes `1`. N: `2 → 1`. A2: `size(false and r) = 2 + size r → 1`. A3:
  `2 + size r → size r`. O2/O3 likewise. I-true: `1 + 1 + s_t + s_f → s_t`. **L (`let x = v in body`):**
  `size = 1 + 1 + size(body)`, and the reduct has `size(body[x:=v]) = size(body)` by Lemma S, which is smaller by 2. ✓
* **Congruence rules.** B1: `l → l'` and by IH `size l' < size l`, so `size(l' + r) = 1 + size l' + size r < size(l + r)`.
  The other congruence rules (B2, A1, O1, N1, I1, L1) are the same argument with the changed child in a different slot
  (the size of a node is strictly monotone in each child). ✓ ∎

**Consequences.** Every sequence of steps is strictly decreasing in `ℕ`, so it is finite; since the final term has size ≥ 1,
`steps ≤ size(e) - 1`. That is `len(trace(e)) - 1 <= size(e) - 1`, asserted by `test_every_step_strictly_decreases_the_size_measure`.

**Why `let` needs care.** Lemma S is true ONLY because the rule substitutes a VALUE, and values are evaluated first
(call-by-value, rule L1) and have size 1. If `let x = e1 in body` instead substituted the unevaluated `e1` (call-by-name),
then `size(body[x:=e1]) = size(body) + k·(size(e1) - 1)` where `k` is the number of free occurrences of `x`: it can GROW.
Example: `let x = (1+1) in ((x*x)*x)` has size `1 + 3 + 5 = 9` and its reduct `(((1+1)*(1+1))*(1+1))` has size
`1 + 7 + 3 = 11`. A measure that goes up under a step proves nothing; one would need a finer measure (e.g. counting
remaining reductions weighted by duplication), which is a much harder proof. Call-by-value buys the easy measure. The same
reasoning is why only closed values are ever substituted: it also makes variable capture impossible, so `substitute` needs no
renaming.

---

## A note on loops and the halting problem

Calc has no recursion and no loops, so the size measure above proves that EVERY program terminates. Add an unbounded loop
(`while`, a recursive function, or a fixed-point operator) and `size` no longer decreases: `while true do skip` steps to
itself; the term `Ω = (λx. x x)(λx. x x)` steps to itself forever. Termination is then undecidable in general (the halting
problem: no program can decide, for every program and input, whether it halts). A TIMEOUT is therefore not a proof of
non-termination: "did not finish in N steps" is consistent with "finishes at step N+1" (think of a Collatz-style loop
whose halting is an open problem). What can be proved is the other direction: a program HAS halted (we saw the value), or a
specific loop provably repeats a state (a certificate such as `e → e`). Languages that insist on termination (Calc, total
functional languages) pay for it in expressiveness: they are not Turing-complete.

---

## A deliberately broken "proof" -- find the flaw

**False claim.** "A closed term is stuck if and only if it is ill-typed."

"Proof" of the direction (⇐) *ill-typed implies stuck*. Suppose `e` is ill-typed. Then some typing rule fails at some node;
for instance in `if true then 1 else (1 + true)` the node `1 + true` has an Int on the left and a Bool on the right, so there is
no reduction rule for it (B3 needs two literals of the same kind). A node without a reduction rule is stuck, so the evaluation
of `e` gets stuck. (⇒) is Type Safety above. Hence stuck ⇔ ill-typed. ∎

**Where it fails.** The step "a node without a reduction rule is stuck, so the evaluation of `e` gets stuck" assumes that
EVERY subterm is eventually evaluated. Evaluation only visits subterms in evaluation positions: here the condition `true`
selects the `then` branch, rule I-true DISCARDS the `else` branch unexamined, and the program reduces to `1`. It is
ill-typed (the checker looks at all branches) and not stuck. The same happens with `false and (1 + true)` (rule A2) and,
in the other direction of strictness, `let x = (1 + true) in 5` IS stuck even though `x` is never used (call-by-value
evaluates the bound expression first). These three programs are in `fixtures/lang/calc_programs.json` and pinned by tests.
The true statement is only (⇒): *stuck implies ill-typed* (the contrapositive of type safety). The converse is false because
a static type system must be sound for every possible execution, so it rejects some programs that happen to run fine; by
Rice's theorem no computable checker can be both sound and exactly complete for a non-trivial semantic property.

---

## After audit (changes made in response to tracks/A2/AUDIT.md)

| Audit finding | What was wrong | Fix |
|---|---|---|
| Preservation claimed in general but only `if` and `+` proved | `let`, `and`, `or`, `==`, `<`, `not` and the `let` congruence were asserted | New Proof 2A proves every remaining rule, including `let` with the substitution lemma applied at the extended environment, and the A1/A2/A3 case split for `and` (and the mirror for `or`); the Claim now names which proof covers which rule |
| Canonical forms stated for the empty environment but used under an arbitrary `Γ` | The statement was weaker than its use, and the parenthetical "needs the values to be CLOSED literals" was misleading | Canonical forms is stated and proved for arbitrary `Γ` (a value is a literal; literal rules ignore `Γ`); the parenthetical in Proof 2 is replaced |
| Substitution lemma omitted the bound term | For `let y = b in body` with `y = x` the proof said "the body is untouched" and stopped, though `b` is still substituted | Substitution defined explicitly (bound term always substituted, body only when `y ≠ x`), exchange stated, both sub-cases of `let` proved, with the induction hypothesis on `b` used in both |
| Progress proved for one case, corollary leaned on termination without saying so | "repeating this reaches a value" needs Proof 4 | Progress now proves every case (`<`, `==`, `and`, `or`, `not`, `if`, `let`, and the arithmetic family); the corollary says explicitly that termination comes from Proof 4 and why closedness is preserved |
