# A2 written proofs (Calc: types, small-step semantics, termination)

The code in `dsdk.lang.calc` is the executable counterpart of the proofs below. The Hypothesis properties in
`tests/lang/test_calc_properties.py` only SAMPLE these statements; the proofs establish them for ALL terms.
Rule names (B1, B2, B3, A1-A3, O1-O3, N1, I1, L1) are the ones in the `calc.py` module docstring. `v` ranges over values
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

**Canonical forms.** If `⊢ v : Int` and `v` is a value then `v = IntLit(n)` for some integer `n`; if `⊢ v : Bool` then
`v = BoolLit(b)`. *Proof:* values are `IntLit` or `BoolLit`; by inversion `⊢ IntLit(n) : T` forces `T = Int` and
`⊢ BoolLit(b) : T` forces `T = Bool`, so a value of type Int cannot be a `BoolLit` and vice versa. ∎

**Substitution lemma.** If `Γ[x:=T1] ⊢ e : T` and `⊢ v : T1` for a literal `v`, then `Γ ⊢ e[x:=v] : T`. *Proof:* structural
induction on `e`; the `Var x` case is `⊢ v : T1`; for `let y = b in body` with `y = x` the body is untouched and its
judgment never used `x`; with `y ≠ x` apply the induction hypothesis to `b` and to `body` under `Γ[y:=…]`. (Tested by
`test_substitution_lemma_*`.) ∎

---

## Proof 1 -- Preservation, case `if`

**Claim (Preservation).** If `Γ ⊢ e : T` and `e → e'` then `Γ ⊢ e' : T`. (Here with `Γ` arbitrary: the proof never uses
closedness except where stated.)

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
* **B3:** `l` and `r` are both values and the rule applied is the integer one. By canonical forms (this is the step that
  needs the values to be CLOSED literals) `l = IntLit(a)` and `r = IntLit(b)`, and `e' = IntLit(a+b)`. By T-Int,
  `⊢ IntLit(a+b) : Int`, which is `T`. ✓

The rules for `-` and `*` are identical with `a-b`, `a*b`. The case that does NOT occur is "B3 on a non-Int pair"
(`1 + true`): there is NO rule for it, which is exactly why that term is stuck, and why inversion rules it out for
well-typed terms (it would need `Γ ⊢ true : Int`). ∎

*Where the tests fit:* `test_preservation_every_step_keeps_the_type` samples the claim on random well-typed programs; the
`let` case needs the substitution lemma above and is sampled by `test_substitution_lemma_*`.

---

## Proof 3 -- Progress (statement, one case proved)

**Claim (Progress).** If `⊢ e : T` (empty environment) then `e` is a value or there is an `e'` with `e → e'`.

Proof by induction on the typing derivation. The variable case is vacuous (`Γ` is empty, so `⊢ x : T` is not derivable).
Literals are values. We prove the case `e = l + r`; the others (`-`, `*`, `<`, `==`, `and`, `or`, `not`, `if`, `let`) have
the same shape: "if a subterm in an evaluation position can step, use the congruence rule; otherwise it is a value, and
canonical forms say which literal it is, so the computation rule applies".

**Case `l + r`.** Inversion: `⊢ l : Int` and `⊢ r : Int`. The induction hypothesis applies to both.
1. If `l` is not a value, IH gives `l → l'`, so B1 gives `l + r → l' + r`.
2. Otherwise `l` is a value; if `r` is not a value, IH gives `r → r'`, and B2 gives `l + r → l + r'`.
3. Otherwise both are values of type Int; canonical forms give `l = IntLit(a)`, `r = IntLit(b)`, and B3 gives
   `l + r → IntLit(a+b)`. ∎

(The `and` case differs only in step 3: `l` is a `BoolLit`, and A2/A3 apply WITHOUT looking at `r`, so progress for `and` does
not even need `r` to be a value.)

**Corollary (type safety).** A closed well-typed term never gets stuck: by Progress it can step unless it is a value, by
Preservation the reduct is again well-typed and closed (substitution only removes free variables), so repeating this reaches
a value. This is `test_type_safety_*` and `test_stuck_terms_are_ill_typed`.

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
