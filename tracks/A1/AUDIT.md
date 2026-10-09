# A1 proof audit

Auditor stance: adversarial, PROOFS.md not trusted. Line numbers refer to `tracks/A1/PROOFS.md` (P) and
`src/dsdk/logic/structures.py` (S). Nothing outside `tracks/A1/AUDIT.md` and `tracks/A1/audit/` was written.

## Verdicts

| Proof | Verdict |
|---|---|
| 1. triangular(n) = n(n+1)/2 | SOUND WITH GAPS (mathematics correct; code link is asserted, not proved) |
| 2. mirror(mirror(t)) = t | SOUND WITH GAPS (mathematics correct; code link is asserted, not proved) |
| 3. Deliberately broken proof | SOUND as a flawed-proof exhibit (flaw correctly named), with one INCORRECT side remark (horses analogy) |

## Proof 1

1. Claim (P13): for every integer n >= 0, triangular(n) = n(n+1)/2. Domain and quantifier are stated. The proof
   establishes exactly this about the mathematical definition (P10). Not more, not less.
2. Base case (P17): n = 0, correct start value. 0 = 0*1/2 verified.
3. IH (P19): P(k) for a fixed k >= 0, used only for k in the step. Correct (ordinary induction, not strong).
4. Step (P23-27): every line checked. Line 24 uses the IH; line 25 is common-denominator algebra; line 26 factors
   (k+1) out of k(k+1)+2(k+1). All correct. No hidden lemma in the algebra (symbolic check below).
   Unstated but true: the division by 2 is in Q; the code's `//` form is the same because n(n+1) is always even
   (checked mechanically n <= 3000; also trivially true as consecutive integers). P never mentions this.
5. Definitions vs code:
   - n = 0: S101 `total = 0`, `range(1, 1)` is empty, returns 0. Matches P10.
   - Negative n: S99 raises ValueError; P's domain is n >= 0, so consistent; the claim says nothing about n < 0.
   - Non-int: S97 `type(n) is not int` rejects bool/float/str with TypeError. Consistent with "integer n".
   - GAP (P10-11): "equivalently triangular(n) = triangular(n-1) + n, which is what the loop computes" is asserted.
     The proof is about the recurrence/sum; that the loop at S101-103 computes it needs a loop invariant
     (after iteration i, total = 1+...+i), which is not given. Low risk, easy fix, but the title claim "proof
     establishes it for the code" is not literally earned. Mechanically confirmed for n <= 3000 only.
6. Minor: P33-34 says the test checks P(0..2000); the test exists (test_structures.py:152) and its loop bound
   should be confirmed by whoever edits it; I did not re-verify the bound 2000 beyond the name.

## Proof 2

1. Claim (P45): for every tree t, mirror(mirror(t)) = t. Quantifier over all finite trees. Proof matches it.
2. Base case (P49): Leaf(v); both mirror applications are the identity on leaves. Correct. (Only one base-case
   constructor exists; there is no empty tree, matching S63-65 "there is no empty tree".)
3. IH (P51): assumed for l and r, the immediate subtrees of t. Structurally smaller only. Correct.
4. Step (P55-58): line 56 applies the definition to inner mirror(Node(l,r)) = Node(mirror(r), mirror(l)). Line 57
   applies it to the outer: mirror(Node(a,b)) = Node(mirror(b), mirror(a)) with a = mirror(r), b = mirror(l),
   giving Node(mirror(mirror(l)), mirror(mirror(r))). Checked: correct, order right. Line 58 uses the IH twice.
   Correct. Uses implicitly: congruence of Node over = (equal children give equal nodes). True for dataclass eq.
   Well-foundedness (P60) "every tree is a Leaf or a Node of smaller trees": true for finite trees built via the
   constructors; frozen dataclass prevents mutation-based cycles except via `object.__setattr__` abuse (out of scope,
   but P does not state "finite/acyclic").
5. Definitions vs code:
   - Leaf/Node (S54-68) match P40. Leaf accepts any value (S58), Node validates children (S46-51).
   - GAP: P's mirror is the recursive definition (P42-43). The code (S76) is an iterative post-order `_fold`
     with an explicit stack (S17-40). Equivalence of `_fold` with the recursive definition is not proved.
     I confirmed it by enumeration (below) but it is a real hole between "proof" and "code".
   - Equality: "=" in P is mathematical; the code/test uses dataclass `==`. For leaf values with non-reflexive
     `==` (NaN, or a class whose `__eq__` returns False) the double mirror still compares equal, but only because
     `_fold` returns the same Leaf object and tuple comparison short-circuits on identity (check_edge.py). So the
     claim in code form depends on leaf identity preservation (S76 `lambda leaf: leaf`), which P never states.
   - Input validation (TypeError for non-trees) is outside the claim; fine.
6. Statement about tests (P62) "the Hypothesis property samples the claim" is accurate (test_structures.py:90).

## Proof 3 (broken proof)

- False claim: sum_{i<=n} i = n(n+1)/2 + 1 for all n >= 0. Truly false for every n (LHS is always exactly 1 less).
- The inductive step (P72-73) is VALID: k(k+1)/2 + 1 + (k+1) = (k+1)(k+2)/2 + 1 (polynomial identity verified).
- The real flaw named at P77-80 is correct: no base case, and the base case is false (Q(0): 0 vs 1). The
  explanation names the cause (missing/false base), not a symptom (e.g. it does not blame the algebra). The remark
  that Q is false for every n, so no n could serve as a base, is also correct.
- FINDING (incorrect remark, P81-82): "The same shape gives the classic horses fallacy." It does not. In the horses
  fallacy the base case (1 horse) is TRUE and the STEP is invalid (fails 1 -> 2). In the broken proof the step is
  valid and the base case is false. They are opposite failure modes; the sentence's own detail ("step silently needs
  k >= 2 ... fails going from 1 to 2") contradicts "same shape". Does not affect the verdict on the exhibit but
  should be reworded ("a different induction fallacy: valid base, invalid step").
- Minor: P75 says "(Base case omitted.)" while P77 says the base case "is false"; consistent (omitted because it
  fails), but the exhibit never demonstrates that the omitted base would have to hold.

## Mechanical evidence

sympy is NOT installed (`uv run python -c "import sympy"` gives ModuleNotFoundError). Fallback: exact `Fraction`
polynomial arithmetic in `audit/check_sum.py`. This compares coefficient dictionaries, hence proves the identity
as polynomials in k, not by sampling.

Output of `check_sum.py`:
```
lhs = {0: 1, 1: 3/2, 2: 1/2}     rhs = {0: 1, 1: 3/2, 2: 1/2}
PASS: k(k+1)/2+(k+1) == (k(k+1)+2(k+1))/2 == (k+1)(k+2)/2 as polynomials in k (coefficients equal)
PASS: broken proof's inductive step is a valid polynomial identity (flaw is the base case)
broken claim Q(0): lhs 0 vs rhs 1
PASS: code triangular(0..3000) == closed form, satisfies recurrence, n(n+1) always even; broken claim false for all of them
rejects -1 ValueError / True TypeError / 2.0 TypeError / '3' TypeError
```
Output of `check_mirror.py` (all shapes with 0..6 internal nodes, leaves over {0,1}, using the real `mirror` and
an independent literal-recursive reference mirror):
```
PASS: 20134 trees (<=6 internal nodes, leaves in {0,1}); 20110 with mirror(t)!=t
```
Output of `check_edge.py`: NaN leaf, and leaf with `__eq__` always False, both still satisfy mirror(mirror(t)) == t
(by identity preservation).

IMPORTANT: the enumeration is a bounded check. It supports the structural-induction proof and shows `_fold` agrees
with the recursive definition on small trees, but it does NOT replace the proof, and the proof does not cover the
iterative implementation. Likewise the n <= 3000 check does not replace the induction.

## Reproduce

```
cd /home/user/dsdk
uv run python -c "import sympy"          # fails: not installed
uv run python tracks/A1/audit/check_sum.py
uv run python tracks/A1/audit/check_mirror.py
uv run python tracks/A1/audit/check_edge.py
```

## Recommended fixes (not applied; PROOFS.md untouched)
1. Add a loop-invariant lemma linking `triangular` (S101-103) to the recurrence (P10-11).
2. Add a lemma that `_fold` computes the recursive mirror (induction on tree structure), and note leaf identity/
   equality assumptions.
3. Correct or delete the horses analogy (P81-82).
4. State "finite trees" in the Proof 2 claim.
