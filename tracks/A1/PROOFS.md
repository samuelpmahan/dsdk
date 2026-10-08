# A1 written proofs

The code in `dsdk.logic.structures` is the executable counterpart of the two proofs below. The tests
(`tests/logic/test_structures.py`) only sample behaviour; these proofs are what establish the claims for ALL inputs.

---

## Proof 1 -- `triangular(n) = n(n+1)/2`

**Definition.** `triangular(0) = 0` and, for `n >= 1`, `triangular(n) = 1 + 2 + ... + n`
(equivalently `triangular(n) = triangular(n-1) + n`, which is what the loop computes).

**Claim.** For every integer `n >= 0`: `triangular(n) = n(n+1)/2`.

Proof by induction on `n`. Let `P(n)` be the statement `triangular(n) = n(n+1)/2`.

**Base case (`n = 0`).** `triangular(0) = 0` (empty sum) and `0*(0+1)/2 = 0`. So `P(0)` holds.

**Inductive hypothesis.** Fix some `k >= 0` and assume `P(k)`: `triangular(k) = k(k+1)/2`.

**Inductive step.** We must show `P(k+1)`. Since `k+1 >= 1`,

    triangular(k+1) = triangular(k) + (k+1)          (definition)
                    = k(k+1)/2 + (k+1)               (inductive hypothesis)
                    = (k(k+1) + 2(k+1))/2
                    = (k+1)(k+2)/2
                    = (k+1)((k+1)+1)/2.

That is exactly `P(k+1)`.

By induction, `P(n)` holds for all `n >= 0`. QED.

*Where the test fits:* `test_triangular_matches_closed_form_for_0_to_2000` checks `P(0..2000)`; the proof covers the
rest. The implementation must not use the closed form, otherwise that test would be circular.

---

## Proof 2 -- `mirror(mirror(t)) = t`

**Definitions.** A tree is either `Leaf(v)` or `Node(l, r)` with `l, r` trees.

    mirror(Leaf(v))    = Leaf(v)
    mirror(Node(l, r)) = Node(mirror(r), mirror(l))

**Claim.** For every tree `t`: `mirror(mirror(t)) = t`.

Proof by structural induction on `t`.

**Base case (`t = Leaf(v)`).** `mirror(Leaf(v)) = Leaf(v)`, so `mirror(mirror(Leaf(v))) = mirror(Leaf(v)) = Leaf(v)`.

**Inductive hypothesis.** For the trees `l` and `r`: `mirror(mirror(l)) = l` and `mirror(mirror(r)) = r`.

**Inductive step (`t = Node(l, r)`).**

    mirror(mirror(Node(l, r)))
      = mirror(Node(mirror(r), mirror(l)))                 (definition, inner mirror)
      = Node(mirror(mirror(l)), mirror(mirror(r)))         (definition, outer mirror: swap and mirror the children)
      = Node(l, r)                                         (inductive hypothesis, twice)

Every tree is a `Leaf` or a `Node` of smaller trees, so the claim holds for all trees. QED.

*Where the tests fit:* the Hypothesis property `mirror o mirror = id` samples the claim; the proof covers every tree.

---

## A deliberately broken "proof" -- find the flaw

**False claim.** For every `n >= 0`: `1 + 2 + ... + n = n(n+1)/2 + 1`.

"Proof" by induction. *Inductive hypothesis:* assume `1 + ... + k = k(k+1)/2 + 1`. *Inductive step:*

    1 + ... + k + (k+1) = k(k+1)/2 + 1 + (k+1)
                        = (k+1)(k+2)/2 + 1.

So the statement holds for `k+1` whenever it holds for `k`. "Therefore it holds for all `n`." (Base case omitted.)

**Where it fails.** The inductive step is actually valid: it shows `Q(k) => Q(k+1)`. But induction needs a **base case** to
start the chain, and here the base case is false: for `n = 0`, the left side is `0` and the right side is `0*1/2 + 1 = 1`.
`Q(0)` fails, so the implication chain never starts (in fact `Q(n)` is false for every `n`, since the left side is always
one smaller than the right). A step that preserves a property is worthless if the property is never established anywhere.
The same shape gives the classic "all horses are the same colour" fallacy, where the step additionally silently needs
`k >= 2` to make the two sub-herds overlap, which fails going from 1 to 2 horses.
