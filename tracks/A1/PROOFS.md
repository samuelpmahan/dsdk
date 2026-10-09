# A1 written proofs

The code in `dsdk.logic.structures` is the executable counterpart of the proofs below. The tests
(`tests/logic/test_structures.py`) only sample behaviour; these proofs establish the claims for ALL inputs, and
(after the audit) they are proved about the code as written: the loop in `triangular` and the iterative `_fold`
behind `mirror`, not only about the mathematical definitions.

Every proof uses the same format: **claim, base case, inductive hypothesis, inductive step, conclusion.**
For the loop and stack-machine proofs, "base case" is initialisation of the invariant and "inductive step" is
maintenance across one iteration. Theorem 1.4 is the one exception: it is not itself an induction but a direct
combination of two lemmas that are, so it states its premises instead of an inductive hypothesis.

---

## Proof 1 -- `triangular(n) = n(n+1)/2`

### 1.0 Domain and code behaviour

`triangular(n)` is specified on **`n` an `int` (exactly; `bool`, `float`, `str`, and `int` subclasses are excluded) with `n >= 0`**.
The code behaves as follows, in this order:

1. `type(n) is not int` -> `TypeError` (so `True`, `2.0`, `"3"` are rejected; `bool` is rejected even though it subclasses `int`).
2. `n < 0` -> `ValueError`.
3. Otherwise it runs the loop `total = 0; for i in range(1, n+1): total += i; return total`.

The claims below say nothing about the error cases other than that they are exactly the complement of the domain.
All remaining statements assume the domain: `n` is an `int`, `n >= 0`.

### 1.1 Definitions and a fact used for division by 2

`S(0) = 0` and for `j >= 1`, `S(j) = S(j-1) + j` (so `S(j) = 1 + 2 + ... + j`).

**Fact E (`m(m+1)` is even for every integer `m`).** Of two consecutive integers `m, m+1` one is even, so their product is even.
Hence `m(m+1)/2` is an integer and equals `m(m+1)//2`. This is why the division by 2 below is exact, in particular
`k(k+1) + 2(k+1)` is even (it is `(k+1)(k+2)`, a product of consecutive integers) and the code-style `//` equals `/`.

### 1.2 Lemma A (arithmetic): for every integer `n >= 0`, `S(n) = n(n+1)/2`

Let `P(n)` be the statement `S(n) = n(n+1)/2`. Proof by induction on `n`.

**Base case (`n = 0`).** `S(0) = 0` and `0*(0+1)/2 = 0`. So `P(0)` holds.

**Inductive hypothesis.** Fix some `k >= 0` and assume `P(k)`: `S(k) = k(k+1)/2`.

**Inductive step.** We must show `P(k+1)`. Since `k+1 >= 1`,

    S(k+1) = S(k) + (k+1)                  (definition)
           = k(k+1)/2 + (k+1)              (inductive hypothesis)
           = (k(k+1) + 2(k+1))/2           (common denominator; numerator is even by Fact E, being (k+1)(k+2))
           = (k+1)(k+2)/2
           = (k+1)((k+1)+1)/2.

That is exactly `P(k+1)`.

**Conclusion.** By induction, `P(n)` holds for all `n >= 0`. QED.

### 1.3 Lemma B (the loop): the loop invariant and termination

Let `n >= 0` be an `int`. The loop is `for i in range(1, n+1): total += i` with `total = 0` before it.
`range(1, n+1)` yields `1, 2, ..., n` in order (empty if `n = 0`). Say "after `j` iterations" for `0 <= j <= n`.

**Claim (invariant `I(j)`).** After `j` iterations, `total = S(j)`. Equivalently, by Lemma A, `total = j(j+1)/2`.
(The invariant is stated with `S`, not the closed form, so the argument does not assume what it will be used to establish.)

**Base case (initialisation, `j = 0`).** Before the first iteration `total = 0 = S(0)`. So `I(0)` holds.

**Inductive hypothesis.** Fix `j` with `0 <= j < n` and assume `I(j)`: after `j` iterations `total = S(j)`.

**Inductive step (maintenance).** Since `j < n`, iteration number `j+1` executes, with loop variable `i = j+1` (the `(j+1)`-th
element of `1, ..., n`). It performs `total := total + i = S(j) + (j+1) = S(j+1)` by the hypothesis and the definition of `S`
(`j+1 >= 1`). So `I(j+1)` holds.

**Conclusion (termination and exit).**
*Termination.* The iteration count is finite and equals `n`, because the loop ranges over the finite sequence `1..n`. Explicitly,
the measure `m(j) = n - j` is a natural number (`>= 0`) for `0 <= j <= n`, is `n` on entry, strictly decreases by exactly 1 per
iteration, and the loop exits when `m = 0`, i.e. `j = n`. No `break`/`continue`, and `i` is not reassigned in the body, so there
is no other path.
*Exit.* At exit `j = n`, so `I(n)` gives `total = S(n)`; the function returns `total`. QED.

*Reliance on Python integers.* The invariant says `total` equals the mathematical integer `S(j)`. That is valid only because Python's `int` is
arbitrary precision: `total += i` never overflows or wraps, so each `+=` is exact integer addition. (In a fixed-width language this
lemma would need the extra hypothesis `S(n)` fits in the word size.) The same holds for `n + 1` in `range(1, n + 1)` and for the `//` in 1.4.

### 1.4 Theorem (the code): for every `int n >= 0`, `triangular(n) = n(n+1)/2`

**Claim.** For every `int n >= 0`, the value returned by `triangular(n)` is `n(n+1)/2`, which is an integer equal to `n(n+1)//2`.

**Premises.** This theorem is not proved by a fresh induction; the inductions are inside Lemma A (arithmetic) and Lemma B (loop), each already
proved for an arbitrary `int n >= 0`. The premises are exactly those two lemmas (and Fact E); no hypothesis about `n - 1` is used.

**Combination.** Fix an `int n >= 0`. By Lemma B the code returns `S(n)`; by Lemma A, `S(n) = n(n+1)/2`; by Fact E that quotient is an
integer, and so equals `n(n+1)//2`.

**Sanity check of the smallest case (`n = 0`, not needed for the proof).** The checks pass, `range(1, 1)` is empty, the loop body never runs and the
function returns `0 = 0*1/2`, as the combination predicts.

**Conclusion.** For all `int n >= 0` the code returns `n(n+1)/2`. For `n < 0` or non-`int` `n` it raises (`ValueError` /
`TypeError`) and the formula makes no claim. QED.

*Where the test fits:* `test_triangular_matches_closed_form_for_0_to_2000` checks `P(0..2000)` (the loop bound there is
`range(2001)`); the proofs cover the rest. The implementation must not use the closed form, otherwise that test would be circular.

---

## Proof 2 -- `mirror(mirror(t)) = t`

### 2.0 Scope: finite binary trees, and which equality is meant

* **Trees.** A tree is a `Leaf(v)` (any value `v`) or a `Node(l, r)` with `l`, `r` trees. A **finite binary tree** is one obtained by finitely
  many applications of these constructors. Every tree built by the code is finite: constructors take already-built children, and the
  dataclasses are frozen, so no cycle can be created short of `object.__setattr__` abuse, which is out of scope. Every statement below is for finite
  trees only. There is no empty tree.
* **Code invariant relied on (sum type).** `Tree` is an abstract sum type with exactly two concrete variants, `Leaf` and `Node`: a bare `Tree()` raises
  `TypeError`, and `Node.__post_init__` requires each child to be a `Leaf` or a `Node`. Hence every object reachable from a constructed tree by
  `.left` / `.right` is a `Leaf` or a `Node`, never a bare `Tree` or a foreign subclass instance. (This invariant is established in
  `src/dsdk/logic/structures.py`, not by this document; it is exactly what the "every tree is a `Leaf` or a `Node`" in the inductions below uses. Under
  the earlier code, which accepted a bare `Tree()` child, `_fold` could reach its `TypeError` branch; AUDIT-2 N2.)
* **Equality.** "Equal" means **structural equality of trees** as computed by the dataclass-generated `__eq__` of `Leaf` and `Node` (field-wise comparison
  of the stored values / children). Its exact mechanism differs between Python versions (see 2.5) and the proof does not depend on the mechanism, only
  on two properties verified there on both 3.12 and 3.13.
* **Stronger relation used in the proof.** Write `t ~ u` ("same shape, same leaf objects") when either `t is u` (both `Leaf`, the identical object),
  or both are `Node` with `t.left ~ u.left` and `t.right ~ u.right`. Then `t ~ u` implies `t == u` (shown in 2.5). `~` is a mathematical relation: it is
  decided by object identity and shape, runs no user `__eq__` and cannot raise. The proof establishes `~`, which is what makes the result survive
  leaf values whose `==` is odd.

### 2.1 Definitions

Recursive mirror `M` (the mathematical definition; `M(Leaf)` returns the very same leaf object):

    M(Leaf(v))    = Leaf(v)            (the same object)
    M(Node(l, r)) = Node(M(r), M(l))

Generic recursive fold `F_{a,c}` for functions `a` (leaf case) and `c` (node case), both pure and total on the values they receive:

    F(x)         = a(x)                 for x a Leaf object (the callback receives the Leaf object itself, not its stored value)
    F(Node(l,r)) = c(F(l), F(r))

`M = F_{a,c}` with `a(x) = x` (x the Leaf object, so `M(Leaf(v))` is the Leaf, not `v`) and `c(p, q) = Node(q, p)`. Since `c` allocates a fresh `Node` on
every call, "values" computed by `F` are objects; two evaluations of the same expression give `~`-related, not identical, results. The code is `mirror(t) = _fold(t, lambda leaf: leaf, lambda left, right: Node(right, left))`.

### 2.2 Lemma M (the recursive definition): for every finite tree `t`, `M(t)` is a tree and `M(M(t)) ~ t`

**Claim.** For every finite tree `t`: `M(t)` is a tree and `M(M(t)) ~ t`.

**Base case (`t = Leaf(v)`).** `M(Leaf(v))` is that same leaf, a tree, so `M(M(t)) = M(t) = t`; the object is identical, so `M(M(t)) ~ t`.

**Inductive hypothesis.** For the immediate subtrees `l` and `r` of `t`: `M(l)`, `M(r)` are trees, `M(M(l)) ~ l`, `M(M(r)) ~ r`.

**Inductive step (`t = Node(l, r)`).** `M(t) = Node(M(r), M(l))` is a tree (children are trees by the hypothesis). Then

    M(M(Node(l, r)))
      = M(Node(M(r), M(l)))                    (definition, inner mirror)
      = Node(M(M(l)), M(M(r)))                 (definition, outer mirror: swap and mirror the children)
      ~ Node(l, r)                             (inductive hypothesis twice; `~` is a congruence for `Node` by its definition)

**Conclusion.** Every finite tree is a `Leaf` or a `Node` of strictly smaller finite trees, so by structural induction the claim holds
for all finite trees. QED.

### 2.3 Lemma F (the code): `_fold(t, a, c) = F_{a,c}(t)` for every finite tree `t`

`_fold` keeps a work stack `W` (list of pairs `(x, flag)`, top = last) and a result stack `R`. Loop:
pop `(cur, expanded)`; if `cur` is a `Leaf`, push `a(cur)` on `R`; if `cur` is a `Node` and `expanded`, pop `right_res` then `left_res` from `R`
and push `c(left_res, right_res)`; if `cur` is a `Node` and not `expanded`, push `(cur, True)`, then `(cur.right, False)`, then `(cur.left, False)`
on `W` (so the left child is on top and is processed first). A non-`Tree` at the root or as a child raises `TypeError`; for a finite tree in the sense of 2.0 this
never happens: by the sum-type invariant cited in 2.0 every child is a `Leaf` or a `Node`, so the `else` branch is unreachable here.

**Denotation of the machine state.** For a work stack `W = [w_1, ..., w_m]` (top `w_m`) and results `R`, let `D(W, R)` be the list obtained
from `R` by processing `w_m, w_{m-1}, ..., w_1` in that order, where
* processing `(x, False)` appends `F(x)`;
* processing `(x, True)` removes the last two items `p, q` (`p` below `q`) and appends `c(p, q)`.

**Reading of `=` in `J`.** `D(W, R)` is evaluated symbolically: its items are expression terms built from `F`, `a`, `c` (e.g. `c(F(l), F(r))`), and `=` in (iii)
is equality of those terms. The code's actual list `R` holds objects, each the evaluation of its term; since `c` creates fresh `Node` objects, an actual
object equals the evaluation of its term only up to `~` (not identity), and `a` returns the Leaf object itself. The final result is therefore `~`-related to `F(t)`, which
is all that 2.4 uses (and `F(t)` is itself defined by the same evaluation, so for `mirror` they are the same computation).

**Claim (invariant `J`).** At the top of every loop test, (i) every frame `(x, True)` in `W` has `x` a `Node`, (ii) every frame `(x, False)` has `x` a `Leaf` or a `Node`, and
(iii) `D(W, R)` is defined (no step of the denotation removes from a list with fewer than two items) and `D(W, R) = [F(t)]` (as terms).

**Base case (initialisation).** Initially `W = [(t, False)]`, `R = []`. (i), (ii) hold trivially since `t` is a `Leaf` or `Node` (a tree, checked first by the `isinstance` test). `D(W, R)` = process `(t, False)` = `[F(t)]`. So `J` holds.

**Inductive hypothesis.** `J` holds at the top of some iteration with `W` non-empty. Let `(cur, expanded)` be the popped top frame, `W0` the rest.

**Inductive step (maintenance).** By `J`, `D(W, R)` = `D(W0, R0)` where `R0` is the result of processing the top frame on `R`. We show the code's new state `(W', R')` has `D(W', R') = D(W, R)`:
* *`cur` a `Leaf`.* (A `True` frame never holds a leaf, by (i).) The code sets `W' = W0`, `R' = R + [a(cur)] = R + [F(cur)]`, which equals "process `(cur, False)` on `R`". So `D(W', R') = D(W, R)`.
* *`cur` a `Node`, `expanded` true.* The code pops two items (`right_res` last, `left_res` before) and appends `c(left_res, right_res)`, which is exactly processing `(cur, True)`. (Defined because `D` is defined, by (iii).) Same `D`.
* *`cur = Node(l, r)`, `expanded` false.* The code sets `W' = W0 + [(cur, True), (r, False), (l, False)]` and `R' = R`. Processing the new top three frames in order (`(l,False)`, then `(r,False)`, then `(cur,True)`) turns `R` into `R + [F(l), F(r)]` and then into `R + [c(F(l), F(r))] = R + [F(cur)]`, the same as processing `(cur, False)`. So `D(W', R') = D(W, R)`.
New frames: `(cur, True)` has a `Node` (i); `l`, `r` are each a `Leaf` or a `Node` (ii) by the sum-type invariant of 2.0 (`Node.__post_init__` rejects anything else, and bare `Tree()` cannot be built). So (i)-(iii) hold again.

**Conclusion (termination and exit).**
*Termination.* Weight each frame: `w(x, False) = 2|x|`, `w(x, True) = 1`, where `|x|` is the number of vertices (leaves plus nodes) of the finite tree `x`, a positive integer. The measure `mu(W) = sum of frame weights` is a natural number. Each iteration strictly decreases it:
leaf frame: `2 -> 0`; expanded node frame: `1 -> 0`; unexpanded node `cur = Node(l, r)` with `|cur| = 1 + |l| + |r|`: `2|cur| = 2 + 2|l| + 2|r|` is replaced by `1 + 2|l| + 2|r|`, a decrease of 1. A natural-number measure cannot decrease forever, so the loop terminates.
*Exit.* The loop ends only with `W` empty; then `D([], R) = R`, so by (iii) `R = [F(t)]` (as terms; as objects, `~`-related), and `results[0] = F(t)`. QED.

### 2.4 Theorem (the code): for every finite tree `t`, `mirror(t)` is a tree and `mirror(mirror(t)) ~ t`; Corollary: `==` when the comparison completes

**Theorem (`~` form, total).** For every finite binary tree `t`: `mirror(t)` is a tree and `mirror(mirror(t)) ~ t`. This is the primary statement. It has no
depth restriction: `mirror` is iterative (Lemma F) and `~` is a mathematical relation, so both sides are defined for every finite tree. (Compare AUDIT-2 N3.)

**Base case (`t = Leaf(v)`).** `mirror(t) = _fold(t, ...) = F_{a,c}(t) = a(t) = t` by Lemma F, the very same object. Then `mirror(mirror(t)) = t`, so `~` (identical).

**Inductive hypothesis.** For the immediate subtrees `l`, `r`: `mirror(mirror(l)) ~ l` and `mirror(mirror(r)) ~ r`.

**Inductive step (`t = Node(l, r)`).** By Lemma F with `a(x) = x`, `c(p, q) = Node(q, p)`, `mirror(s) = F_{a,c}(s) = M(s)` for every finite tree `s` (the recursive definition in 2.1 *is* `F_{a,c}`);
so `mirror(t) = Node(mirror(r), mirror(l))` is a tree and
`mirror(mirror(t)) = Node(mirror(mirror(l)), mirror(mirror(r))) ~ Node(l, r)` by the hypothesis, the same computation as Lemma M's step, now for the code. (Lemma M gives the same conclusion directly: `mirror(mirror(t)) = M(M(t)) ~ t`.)

**Conclusion.** `mirror(mirror(t)) ~ t` for all finite binary trees. QED.

**Corollary (`==` form, with a depth caveat).** For every finite binary tree `t`, *if the evaluation of `mirror(mirror(t)) == t` completes*, it returns `True`.
Proof: `~` implies `==` (2.5). Caveat: dataclass `==` is recursive in the depth of the tree, so for deep trees the comparison itself raises `RecursionError`
even though `mirror(mirror(t))` was computed correctly. Executed on both Python 3.12.3 and 3.13.16: two separately built left-leaning trees of depth 3000
(`Node(Node(...), Leaf(0))`) compared with `==` raise `RecursionError` (limit 1000). So the unconditional statement "`mirror(mirror(t)) == t` for every finite tree" is
false as a statement about evaluating `==` in Python; the true unconditional statement is the `~` theorem, and the `==` form holds whenever the tree depth is
within the interpreter's recursion budget (roughly `sys.getrecursionlimit()` minus the current stack depth; the exact bound is interpreter-dependent and not proved here).

### 2.5 `~` implies `==`, and what the theorem says about `==` on leaf values

Lemma M/F show that `mirror` returns the **same leaf objects**: `_fold` hands the original `Leaf` object to `leaf(cur)`, and `lambda leaf: leaf` returns it unchanged. So every leaf of
`mirror(mirror(t))` *is* a leaf of `t` at the same position, and `t ~ mirror(mirror(t))` holds with `is`, not merely `==`.

**Claim: `t ~ u` implies `t == u`, on every supported Python version.** The mechanism of the generated `__eq__` differs, so the proof uses only two properties:

* **(R) Reflexive on identical objects.** For `x` a `Leaf`, `x == x` is `True` even if `x.value` has an irreflexive `==`.
* **(C) Compositional on `Node`.** `Node(l, r) == Node(l', r')` is `True` whenever `l == l'` and `r == r'` (it asks nothing else of the children).

*Actual mechanism, verified by running snippets* (`@dataclass(frozen=True)`, `n = float('nan')`, `x = Leaf(n)`):

| | Python 3.12.3 | Python 3.13.16 |
|---|---|---|
| `(n,) == (n,)` | `True` | `True` |
| `Leaf(n) == Leaf(n)` (two distinct Leaf objects, same `n`) | `True` | **`False`** |
| `x == x` | `True` | `True` |
| `Node(x, x) == Node(x, x)` (distinct Nodes, shared leaf `x`) | `True` | `True` |
| `BUILD_TUPLE` in `Leaf.__eq__` (`dis`) | present | absent |

On 3.12 (and earlier) the generated `__eq__` compares the tuples `(self.value,) == (other.value,)`, and tuple comparison tests identity before `==`; the same for
`Node` with `(left, right)`. On 3.13 the generated `__eq__` compares fields one by one with `==` (no tuple), preceded by a `self is other` shortcut.
So the earlier description "dataclass `==` is a tuple comparison" is true for 3.12 only. (R) holds on both, via tuple element identity on 3.12 and
the `self is other` shortcut on 3.13, as the `x == x` row shows. (C) holds on both: tuple comparison / field-wise comparison of the children.

*Proof of the claim* by induction on the `~` derivation. If `t is u` and both are `Leaf`: (R). If both are `Node` with `t.left ~ u.left`, `t.right ~ u.right`: by induction
the children are `==`, so (C) gives `t == u`. (Proof relies on (R) and (C) only; since `~` for `Leaf` demands the *identical* object, the weaker, version-dependent
fact that two *distinct* Leaf objects with the same irreflexive value compare equal is never used. It is `True` on 3.12 and `False` on 3.13.)

Hence the theorem holds for "always-unequal" leaves (a `float('nan')` leaf, or a user class whose `__eq__` always returns `False`), on both versions; this is what the audit's `check_edge.py` observed.

What the theorem therefore **does** say: `mirror(mirror(t)) ~ t` for every finite tree and every kind of leaf value, and consequently `mirror(mirror(t)) == t` whenever that
comparison completes (2.4, Corollary).
What it does **not** say: it asserts nothing about `==` on leaf *values* being reflexive, symmetric or transitive; it does not say `Leaf(nan) == Leaf(nan)` for two distinct Leaf objects
(that is `False` on 3.13, and for distinct NaN objects on every version); and it does not claim `mirror(t1) == mirror(t2)` whenever `t1 == t2` when leaf equality is irregular. The result relies on the leaf-identity preservation of
`lambda leaf: leaf` in `mirror`; a variant that copied leaf values would need reflexive leaf `==` to keep the `==` form of the claim.

*Where the tests fit:* the Hypothesis property `mirror o mirror = id` samples the claim; the proofs cover every finite tree and, via Lemma F, the iterative implementation.

---

## A deliberately broken "proof" -- find the flaw

**False claim.** For every `n >= 0`: `1 + 2 + ... + n = n(n+1)/2 + 1`.

"Proof" by induction. *Inductive hypothesis:* assume `1 + ... + k = k(k+1)/2 + 1`. *Inductive step:*

    1 + ... + k + (k+1) = k(k+1)/2 + 1 + (k+1)
                        = (k+1)(k+2)/2 + 1.

So the statement holds for `k+1` whenever it holds for `k`. "Therefore it holds for all `n`." (Base case omitted.)
(The divisions by 2 are exact for the same reason as in Proof 1: `k(k+1)` and `(k+1)(k+2)` are products of consecutive integers, hence even.)

**Where it fails.** Let `Q(n)` be the false claim. The inductive step is actually valid: it shows `Q(k) => Q(k+1)`. But induction needs a **base case**
to start the chain, and here the base case is false: for `n = 0`, the left side is `0` and the right side is `0*1/2 + 1 = 1`. `Q(0)` fails, so the implication chain
never starts (in fact `Q(n)` is false for every `n`, since the left side is always one smaller than the right, so no other `n` could serve as a base case either).
A step that preserves a property is worthless if the property is never established anywhere.

**Contrast with the horses fallacy (a different failure mode).** In the classic "all horses are the same colour" fallacy the roles are reversed: the **base case is true**
(one horse is trivially all one colour) and the **inductive step is invalid** (the two overlapping sub-herds argument silently needs `k >= 2` and fails going from 1 horse to 2).
In the exhibit above the **step is valid** and the **base case is false**. Both are broken inductions, but they break in opposite places, so they do not have "the same shape":
an induction proof needs both a true base and a valid step, and each of the two fallacies lacks a different one.

---

## Changes after audit

| Audit finding | Fix in this file |
|---|---|
| P1 gap: "the loop computes the recurrence" was asserted (P10-11) | Added 1.3 Lemma B: loop invariant `total = S(j)` after `j` iterations, with initialisation, maintenance, termination (measure `n - j`) and exit; 1.4 combines it with Lemma A to conclude the code returns `n(n+1)/2`. |
| P1: domain and error behaviour not matched to code | 1.0 states `int`, `n >= 0`, `bool` and other types excluded (`TypeError`), `n < 0` is `ValueError`, order of checks. |
| P1: division by 2 relied on unstated evenness of `n(n+1)` | Fact E (1.1) proves `m(m+1)` is even in one line; cited at the division in Lemma A, in 1.4, and in the broken proof. |
| P1 minor: test bound 2000 not verified | Confirmed against the test (`range(2001)`) and stated in the closing note of Proof 1. |
| P2 gap: proof was about the recursive definition, code is iterative `_fold` | Split into Lemma M (recursive `M(M(t)) ~ t`, structural induction) and Lemma F (`_fold = F` via stack invariant `J`, with termination measure); 2.4 transfers the theorem to the code. Both versions proved. |
| P2: "finite", acyclic not stated | 2.0 states finite binary trees explicitly and says why constructors/frozen dataclasses yield finite trees; every claim is "for finite trees". |
| P2: meaning of "=" and leaf identity preservation (`check_edge.py`: NaN / always-unequal leaves) | 2.0 fixes structural equality (dataclass `==`), introduces the stronger `~` (same shape, same leaf objects); 2.5 explains identity-then-`==` tuple comparison, what the theorem does and does not say about leaf `==`. |
| P2: well-foundedness remark was informal | Replaced by explicit structural induction (Lemma M) and the numeric weight `mu` (Lemma F). |
| P3: horses analogy was wrong ("same shape") | Reworded: horses has a true base and an invalid step (1 -> 2); the exhibit has a valid step and a false base. Broken exhibit kept unchanged otherwise. |
| P3 minor: omitted base case never shown to fail | The false base is `Q(0)`: 0 vs 1, shown in "Where it fails" and stated to rule out any other base. |
| **AUDIT-2 N1:** dataclass `==` described as `(self.value,)==(other.value,)`, false on Python 3.13 | 2.0 no longer names a mechanism. 2.5 rewritten: `~ => ==` is derived from two properties, (R) reflexive on identical objects and (C) compositional on `Node`, and a table of executed outputs on 3.12.3 and 3.13.16 shows the real mechanism (tuple compare on 3.12, field-wise plus `self is other` on 3.13; `Leaf(nan)==Leaf(nan)` is `True` / `False`). Conclusion `~ => ==` kept: it holds on both versions. |
| **AUDIT-2 N2:** bare `Tree()` accepted as child (cross-reference) | Code fix is separate (`Tree` becomes abstract, children must be `Leaf` or `Node`). 2.0 now lists this as a "code invariant relied on"; Lemma F's unreachable-`else` claim and (ii) cite it and say `Leaf` or `Node`, not "tree". No `src` or tests edited here. |
| **AUDIT-2 N3:** `==` form not total (RecursionError on deep trees) | 2.4 restated: primary Theorem in the `~` form (total, no depth limit); `==` is a Corollary "if the comparison completes", with the executed depth-3000 `RecursionError` on 3.12 and 3.13 and a statement that the exact bound is interpreter-dependent. |
| **AUDIT-2 N4:** `F(Leaf x) = a(x)` notation; `=` in `J` is between terms | 2.1: `F(x) = a(x)` with `x` the Leaf object, and the note that `c` allocates fresh Nodes. Lemma F gets a "Reading of `=` in `J`" paragraph: equality of symbolic terms, actual objects `~`-related, not identical. Exit step says the same. |
| **AUDIT-2 N5:** placeholder inductive hypothesis in 1.4 | 1.4 now lists its premises (Lemma A, Lemma B, Fact E) and a combination step; no fake hypothesis. The `n = 0` case is kept only as a labelled sanity check. Format note at the top updated. |
| **AUDIT-2 N6:** reliance on unbounded Python ints unstated | 1.3 adds "Reliance on Python integers": `total += i`, `n + 1` and `//` are exact because `int` is arbitrary precision; a fixed-width language would need a no-overflow hypothesis. |
