"""Exact polynomial-identity check (sympy unavailable): polynomials in k as {degree: Fraction}."""
from fractions import Fraction as F
import sys
sys.path.insert(0, "/home/user/dsdk/src")
def mul(a, b):
    r = {}
    for i, x in a.items():
        for j, y in b.items():
            r[i+j] = r.get(i+j, 0) + x*y
    return {d: c for d, c in r.items() if c != 0}
def add(a, b):
    r = dict(a)
    for d, c in b.items(): r[d] = r.get(d, 0) + c
    return {d: c for d, c in r.items() if c != 0}
def sc(a, s): return {d: c*s for d, c in a.items() if c*s != 0}
k = {1: F(1)}; one = {0: F(1)}
kp1 = add(k, one); kp2 = add(k, sc(one, 2))
lhs = add(sc(mul(k, kp1), F(1, 2)), kp1)       # k(k+1)/2 + (k+1)
rhs = sc(mul(kp1, kp2), F(1, 2))                # (k+1)(k+2)/2
mid = sc(add(mul(k, kp1), sc(kp1, 2)), F(1, 2)) # (k(k+1)+2(k+1))/2  (proof line 25)
print("lhs =", dict(sorted(lhs.items())), "\nrhs =", dict(sorted(rhs.items())))
assert lhs == rhs == mid, "polynomial identity FAILED"
print("PASS: k(k+1)/2+(k+1) == (k(k+1)+2(k+1))/2 == (k+1)(k+2)/2 as polynomials in k (coefficients equal)")
# degree<=2 polys over Q agreeing at 3 points are equal; coefficient equality above is the stronger statement.
# Broken proof step: k(k+1)/2+1+(k+1) vs (k+1)(k+2)/2+1
b_l = add(add(sc(mul(k, kp1), F(1,2)), one), kp1); b_r = add(sc(mul(kp1, kp2), F(1,2)), one)
assert b_l == b_r; print("PASS: broken proof's inductive step is a valid polynomial identity (flaw is the base case)")
# Broken claim base: n=0
print("broken claim Q(0): lhs 0 vs rhs", F(0)*1/2+1)
from dsdk.logic.structures import triangular
for n in range(0, 3001):
    assert triangular(n) == n*(n+1)//2 and n*(n+1) % 2 == 0
    if n: assert triangular(n) == triangular(n-1) + n   # loop == recurrence the proof assumes
    assert triangular(n) != n*(n+1)//2 + 1
print("PASS: code triangular(0..3000) == closed form, satisfies recurrence, n(n+1) always even; broken claim false for all of them")
for bad in (-1, True, 2.0, "3"):
    try: triangular(bad); print("NO ERROR", bad)
    except (TypeError, ValueError) as e: print("rejects", repr(bad), type(e).__name__)
