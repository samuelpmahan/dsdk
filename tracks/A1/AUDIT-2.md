# A1 proof audit, round 2 (re-audit of the revised PROOFS.md)

Auditor stance: adversarial; the "Changes after audit" table was not trusted. `P` = tracks/A1/PROOFS.md,
`S` = src/dsdk/logic/structures.py. Only this file and `audit/check_fold_invariant.py` were written.
Interpreters: `uv run` uses Python 3.13.16; 3.12 and 3.11 also present; pyproject says `requires-python >=3.12`.

## Verdicts

| Proof | Verdict |
|---|---|
| 1. triangular(n) = n(n+1)/2 (Lemma A, Lemma B, Theorem 1.4) | SOUND (two cosmetic nits, N5, N6) |
| 2. mirror(mirror(t)) = t (Lemma M, Lemma F, Theorem 2.4, 2.5) | SOUND WITH GAPS: the `~` result and Lemma F are sound; the `==` justification in 2.0/2.5 is factually wrong on Python 3.13 (N1), "tree" is not the class the code accepts (N2), and `==` is not total (N3) |
| 3. Deliberately broken proof | SOUND (horses remark corrected) |

## Earlier findings (AUDIT.md)

| # | Earlier finding | Status | Reason |
|---|---|---|---|
| 1 | P1: loop-to-recurrence link asserted | CLOSED | Lemma B (P 1.3) is a real invariant proof; checked below against S97-104 line by line. |
| 2 | P1: domain / errors vs code, `//` evenness | CLOSED | 1.0 matches S97-100 and order of checks; executed: `True`, `IntEnum` member, `2.0` all give TypeError. Fact E is correct (consecutive integers). |
| 3 | P1 minor: test bound 2000 | CLOSED | tests/logic/test_structures.py:152-155 is `for n in range(2001)`, i.e. 0..2000 inclusive, as P states. |
| 4 | P2: proof about recursion, code iterative `_fold` | CLOSED | Lemma F + the executed instrumented check (below) confirm J and the measure on the real code. Gaps in wording only (N4). |
| 5 | P2: finite / acyclic not stated | CLOSED | 2.0 and the claim in 2.4 say "finite binary tree". (But see N2 on what "tree" means and N3 on `==` for deep trees.) |
| 6 | P2: `=` meaning and leaf identity (NaN / always-False `__eq__`) | PARTIALLY CLOSED -> reopened as N1 | The introduction of `~` and the identity-preservation point are right and the conclusion survives. The stated mechanism ("dataclass `==` is `(self.value,)==(other.value,)`, tuple compare tests identity first") is false on Python 3.13, which the project supports. |
| 7 | P2: informal well-foundedness | CLOSED | Replaced by structural induction (Lemma M) and the weight measure (Lemma F), both verified. |
| 8 | P3: horses analogy wrong | CLOSED | P now says horses = true base, invalid step; exhibit = valid step, false base. Correct. |
| 9 | P3 minor: omitted base never shown to fail | CLOSED | "Where it fails" shows Q(0): 0 vs 1 and that Q(n) is false for every n. |

## Lemma B (loop invariant for `triangular`), against S101-104

Code: `total = 0` (S101); `for i in range(1, n + 1):` (S102); `total += i` (S103); `return total` (S104).

* Bounds: `range(1, n+1)` yields exactly 1..n (n items; empty at n=0). No off-by-one: a `range(1, n)` or `range(n)` would be wrong, the code is neither. P says the same.
* Initialisation `I(0)`: `total = 0 = S(0)` at S101. Correct.
* Maintenance: iteration j+1 (0 <= j < n) has `i = j+1`, `total := S(j) + (j+1) = S(j+1)`. Correct; the case j+1 = n is covered (j < n). Body has no other assignment to `total` or `i`, no break/continue (S102-103).
* Termination: the for-loop over a finite range, iteration count n; measure n-j. Exit: j = n, `I(n)`, return at S104. Correct.
* Not-assumed-what-is-proved: the invariant uses `S` (the recurrence), not the closed form. Correct.
* Unstated but true: Python ints are unbounded, so `+=` does not overflow (N6).
Verdict: sound.

## Lemma F (`_fold` invariant J and weight), against S17-40

Transitions in the real code:
1. `cur` Leaf (S27-28): `work` loses its top, `results.append(leaf(cur))`. P: `R' = R+[a(cur)]`, W' = W0. Matches. Weight 2 -> 0 (|Leaf|=1), delta 2.
2. `cur` Node, expanded (S29-33): `right_res = pop()`, `left_res = pop()`, append `combine(left_res, right_res)`. P: remove last two (p below q), append c(p,q). Matches the pop order (right is last). Weight 1 -> 0, delta 1.
3. `cur` Node, not expanded (S34-37): appends `(cur,True)`, `(cur.right,False)`, `(cur.left,False)`; left is on top. P: `W0 + [(cur,True),(r,False),(l,False)]`. Matches. Weight 2|cur| -> 1+2|l|+2|r| = 2|cur|-1, delta 1.
Also: the `else` branch (S38-39) is the only exit that is not via empty `work`; P says it is unreachable for "a well-formed tree" (see N2: not true for the class of objects the constructors accept).
The denotation argument (D(W',R') = D(W,R) in each case; case 3 by evaluating the three new top frames) is correct, and the base case/exit (`D([],R)=R`, `results[0]=F(t)` at S40) is correct. The weight argument is correct (|x| >= 1 so all weights are naturals).

Executed check (`audit/check_fold_invariant.py`): the REAL `_fold` is run unmodified under `sys.settrace`; at every `while work:` test (S25) the locals `work` and `results` are snapshotted. For all 65 trees with 0..5 internal nodes (1+1+2+5+14+42; distinct leaf labels, symbolic leaf/combine) it asserts: (i) every `True` frame is a Node, (ii) every frame holds a Tree, (iii) `D(W,R)` is defined and equals `[F(t)]` (F by independent recursion, D by the PROOFS definition), the next state equals exactly the transition predicted for the case taken, the weight delta is exactly 2 / 1 / 1 for leaf / expanded / unexpanded, weight strictly decreases and stays >= 0, initial weight = 2|t|, exit state is `W=[]`, `R=[F(t)]`, and the number of loop tests = iterations+1 = leaves + 2*internal + 1. Result: PASS, 988 loop-test states, identical on Python 3.12 and 3.13. Sanity: a mutant `_fold` that pushes left before right is detected by the same checker (so the checker is not vacuous).
Verdict: Lemma F sound, with wording nits (N4).

## Python-semantics claims, each executed

| Claim in P | Executed result | Status |
|---|---|---|
| `type(n) is not int` rejects `True`, `2.0`, `"3"`, int subclasses | `True`, `IntEnum` member, `2.0` -> TypeError on 3.11/3.12/3.13 | CONFIRMED |
| "tuple comparison checks identity before `==`" | `(nan,)==(nan,)` is True while `nan==nan` is False; same for a class with `__eq__` always False (3.11-3.13) | CONFIRMED (for tuples) |
| "dataclass `==` compares `(self.value,)==(other.value,)`" (P 2.0, 2.5) | 3.11/3.12: `Leaf(nan)==Leaf(nan)` (same nan object) is True. **3.13: False.** `dis` on 3.13 `__eq__`: no BUILD_TUPLE (field-wise compare); on 3.12: BUILD_TUPLE | **FALSE on 3.13** (N1) |
| two identical Leaf objects compare equal even if the value's `==` is irreflexive | `x=Leaf(nan); x==x` True on 3.11-3.13; `Node(x,x)==Node(x,x)` True on all | CONFIRMED (on 3.13 via the instance-level shortcut, not tuple identity) |
| `mirror(mirror(t)) == t` with NaN / always-False leaves | `audit/check_edge.py` on 3.13: True, True, True | CONFIRMED (conclusion holds; mechanism differs on 3.13) |
| every finite tree: `mirror(mirror(t)) == t` | depth 3000: `mirror(mirror(t))` works (iterative) but `==` raises `RecursionError` (3.11-3.13) | **FALSE as stated for the `==` form** (N3) |
| `Node.__post_init__` guarantees children are trees | `Node(Tree(), Leaf(1))` constructs; `mirror` raises `TypeError: expected a Tree, got Tree` | validation is isinstance-Tree, not Leaf-or-Node (N2) |

## New findings (introduced or left by the revision)

* N1 (P 2.0 lines "a tuple comparison (self.value,) == (other.value,)", and all of 2.5 paragraph 2 "Python's dataclass `==` on Leaf compares (self.value,)==(other.value,)... Node equality compares (left, right) tuples"). False on Python 3.13, within `requires-python >=3.12`: `Leaf(nan)==Leaf(nan)` with the same nan object is False there. The claim "~ implies ==" is still TRUE on every version, but for a different reason: (a) identical Leaf objects: dataclass `__eq__` returns True on `self is other` (3.13 shortcut) / tuple identity (<=3.12); (b) Node: field-wise `==` on `~` children, by induction. The proof should say "implies == for any dataclass `__eq__` that is reflexive on identical objects and compares fields", and not describe the tuple mechanism as the fact. Also the sentence "two identical leaves compare equal even when value.__eq__ is irreflexive" is true only for identical *Leaf* objects, not for `Leaf(v)` vs a fresh `Leaf(v)` with the same `v` (False on 3.13). Severity: medium (a stated fact about the language is wrong; the theorem survives).
* N2 (P 2.0 "A tree is a Leaf(v) or Node(l, r)" vs S46-51, S38-39). The constructor check is `isinstance(child, Tree)`, which a bare `Tree()` instance satisfies (it is neither Leaf nor Node). Such a "tree" is constructible, and `_fold` raises TypeError on it, so P's statements "that branch is unreachable here" (P 2.3) and "children are trees by `__post_init__`" (P Lemma F inductive step, (ii)) are only true after restricting to trees whose every node is a Leaf or Node (i.e. excluding direct `Tree()`/foreign subclass instances). Add that restriction (or note the TypeError). Severity: low.
* N3 (P 2.4 claim "mirror(mirror(t)) == t for every finite binary tree", 2.5, conclusion). `==` is recursive in Python; for deep trees it raises RecursionError (executed, depth 3000), whereas `mirror` is iterative and works. The `~` form is a mathematical statement and is fine; the `==` form should be scoped ("when the comparison itself completes", depth below the recursion limit). Severity: low.
* N4 (P 2.1/2.3 notation). `F(Leaf x) = a(x)` reads as if x were the value, while the code and `a(x)=x` need x to be the Leaf object (otherwise M(Leaf v) would be v, not Leaf(v)). Also J's "=" between `D(W,R)` and `[F(t)]` is an equality of symbolic terms; since `c` allocates a fresh Node each call, the equality is up to `~`-shape, not object identity. Both are repairable by a sentence. Severity: cosmetic.
* N5 (P 1.4 "Inductive hypothesis: no further induction is needed"). Fills the mandated format with a placeholder; the base case there duplicates Lemma B at n=0. Harmless.
* N6 (P 1.3). Does not mention that Python integers do not overflow, which the exactness of `total` relies on. Harmless.
* No error was found in Lemma B, Lemma A, Lemma M, Lemma F's transitions, the weight measure, or the broken-proof exhibit.

## Reproduce

```
cd /home/user/dsdk
uv run python tracks/A1/audit/check_fold_invariant.py            # PASS: 65 trees, 988 states (3.13)
PYTHONPATH=src python3.12 tracks/A1/audit/check_fold_invariant.py # same on 3.12
uv run python tracks/A1/audit/check_edge.py
sed -n 150,156p tests/logic/test_structures.py                    # range(2001)
# dataclass == on 3.13 vs 3.12 (N1):
cat > /tmp/s.py <<'X'
import sys; from dataclasses import dataclass
@dataclass(frozen=True)
class L: v: object
n=float('nan'); print(sys.version_info[:2], (n,)==(n,), L(n)==L(n), (lambda x: x==x)(L(n)))
X
python3.12 /tmp/s.py   # (3, 12) True True True
python3.13 /tmp/s.py   # (3, 13) True False True
# N2 and N3:
PYTHONPATH=src python3.13 -c "from dsdk.logic.structures import *; mirror(Node(Tree(),Leaf(1)))"
PYTHONPATH=src python3.13 -c "
from dsdk.logic.structures import *
t=Leaf(1)
for _ in range(3000): t=Node(t,Leaf(0))
m=mirror(mirror(t)); print('mirror ok'); print(m==t)"
```
