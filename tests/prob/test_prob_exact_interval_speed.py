"""Contract tests for the FAST exact (Clopper-Pearson) interval: same numbers as the slow exact-Fraction implementation, 100x quicker.

The slow implementation (60 bisections of exact Fraction binomial tails) was run once over a grid and its outputs frozen in
fixtures/prob/exact_interval_grid.json (regenerate with tools/prob/gen_exact_interval_grid.py; that script refuses to run on a fast
implementation). These tests check, on the fast implementation:

* agreement with the frozen slow outputs to 1e-12 on every k for n in {1, 2, 3, 5, 10, 30, 100, 300} and on spot checks at n = 1000, 2000
  (n = 2000 is where a naive float evaluation of comb * p**i * (1-p)**(n-i) underflows);
* the speed: n = 300, k = 146 (and k = 3) under 0.05 s, and n = 2000 under 1 s;
* the outward-rounding guarantee, with independent exact Fraction tails (a fast method that is merely close but NOT outward would pass the
  agreement tests; this test is what stops it);
* the closed forms at k = 0 and k = n, monotonicity in k, a few other confidence levels, and the argument errors.

On the current slow implementation every test passes or is skipped EXCEPT the timing tests. The agreement/monotonicity/certificate tests for
n >= 100 are skipped there (they would take about 40 minutes); the skip reason names the slow code, so the failure is reported only by the timing tests.
"""
from __future__ import annotations

import json
import math
import time
from fractions import Fraction
from functools import lru_cache
from pathlib import Path

import pytest

from dsdk.prob import exact_interval

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "fixtures" / "prob" / "exact_interval_grid.json"
GRID_N = (1, 2, 3, 5, 10, 30, 100, 300)
SPOTS = {1000: (0, 1, 500, 1000), 2000: (0, 1000, 2000)}
HALF = Fraction(1, 40)  # (1 - 0.95) / 2, exactly


@lru_cache(maxsize=1)
def _load():
    doc = json.loads(FIXTURE.read_text())
    return {(k, n): (low, high) for k, n, low, high in doc["cases"]}


@lru_cache(maxsize=1)
def _is_slow() -> bool:
    """True for the reference-speed implementation (a call at n=100 takes about 0.4 s there and a few ms here)."""
    t = time.perf_counter()
    exact_interval(50, 100)
    return time.perf_counter() - t > 0.1


def _needs_fast(n: int) -> None:
    if n >= 100 and _is_slow():
        pytest.skip("slow reference-speed exact_interval: this check would take tens of minutes; the timing tests report the failure")


def tail_ge(n, k, p):
    return sum((math.comb(n, i) * p**i * (1 - p) ** (n - i) for i in range(k, n + 1)), Fraction(0))


def tail_le(n, k, p):
    return sum((math.comb(n, i) * p**i * (1 - p) ** (n - i) for i in range(0, k + 1)), Fraction(0))


# ==== The frozen fixture itself ====
def test_the_fixture_holds_the_whole_grid_and_the_spot_checks():
    cases = _load()
    for n in GRID_N:
        assert all((k, n) in cases for k in range(n + 1)), n
    for n, ks in SPOTS.items():
        assert all((k, n) in cases for k in ks), n
    assert len(cases) == sum(n + 1 for n in GRID_N) + sum(len(v) for v in SPOTS.values())
    for (k, n), (low, high) in cases.items():
        assert 0.0 <= low <= high <= 1.0 and (k == 0) == (low == 0.0) and (k == n) == (high == 1.0), (k, n)


# ==== The slow implementation stays available as the reference ====
def test_the_slow_exact_fraction_version_is_kept_as_a_private_reference_and_still_reproduces_the_fixture_bit_for_bit():
    """The card keeps the old code as ``_exact_interval_reference`` (so the fixture can be regenerated and checked); on today's code,
    where ``exact_interval`` IS the slow version, it does not exist yet and the test is skipped."""
    from dsdk.prob import sampling

    ref = getattr(sampling, "_exact_interval_reference", None)
    if ref is None:
        if _is_slow():
            pytest.skip("today's exact_interval is itself the slow reference")
        pytest.fail("the fast implementation must keep the old Fraction code as dsdk.prob.sampling._exact_interval_reference")
    cases = _load()
    for n in (1, 2, 3, 5, 10):
        for k in range(n + 1):
            assert ref(k, n) == tuple(cases[(k, n)]), (k, n)
    assert ref(0, 30) == tuple(cases[(0, 30)]) and ref(30, 30) == tuple(cases[(30, 30)])
    assert ref(9, 30) == tuple(cases[(9, 30)])


# ==== Agreement with the slow implementation ====
@pytest.mark.parametrize("n", GRID_N)
def test_every_k_agrees_with_the_frozen_slow_output_to_1e_12(n):
    _needs_fast(n)
    cases = _load()
    worst = 0.0
    for k in range(n + 1):
        low, high = exact_interval(k, n)
        slow_low, slow_high = cases[(k, n)]
        worst = max(worst, abs(low - slow_low), abs(high - slow_high))
        assert abs(low - slow_low) <= 1e-12 and abs(high - slow_high) <= 1e-12, (k, n, (low, high), (slow_low, slow_high))
    assert worst <= 1e-12


@pytest.mark.parametrize("n,k", [(n, k) for n, ks in SPOTS.items() for k in ks])
def test_large_n_spot_checks_agree_with_the_frozen_slow_output(n, k):
    _needs_fast(n)
    low, high = exact_interval(k, n)
    slow_low, slow_high = _load()[(k, n)]
    assert abs(low - slow_low) <= 1e-12 and abs(high - slow_high) <= 1e-12, (k, n, (low, high), (slow_low, slow_high))


# ==== Speed ====
def _best_time(k, n, runs=3, limit=0.05):
    best = math.inf
    for _ in range(runs):
        t = time.perf_counter()
        exact_interval(k, n)
        best = min(best, time.perf_counter() - t)
        if best > 20 * limit:  # hopeless (the slow code): do not repeat a 6 s call
            break
    return best


def test_n_300_k_146_takes_under_50_ms():
    """The slow code takes about 6.3 s; a log-space float implementation takes about 3 ms, so 0.05 s leaves a 15x margin for a busy CI machine (best of 3)."""
    assert _best_time(146, 300) < 0.05


def test_n_300_k_3_takes_under_50_ms():
    """k = 3 was equally slow (about 6.3 s): the cost did not depend on which tail was short."""
    assert _best_time(3, 300) < 0.05


def test_n_2000_takes_under_one_second():
    """The cost must grow gently with n (the card allows O(n) terms per tail evaluation): about 30 ms for a plain implementation."""
    if _is_slow():
        pytest.fail("slow reference-speed implementation: n = 2000 would take over half an hour per call")
    assert _best_time(1000, 2000, limit=1.0) < 1.0


# ==== The coverage guarantee: ends are never inside the exact solution ====
@pytest.mark.parametrize("n,k", [(1, 0), (1, 1), (7, 2), (10, 5), (30, 1), (30, 29), (30, 15), (100, 3), (100, 50), (300, 3), (300, 146), (300, 297)])
def test_the_ends_are_on_the_safe_side_of_the_exact_tail_equations_and_within_1e_9(n, k):
    """Checked with independent exact Fraction tails at the returned floats: the lower end has P(X >= k) <= 0.025 (not narrower than the exact
    interval) and is within 1e-9 of 0.025; the upper end likewise with P(X <= k). A method that is within 1e-12 of the exact ends but on the wrong
    side of them (no outward widening) fails here, not in the agreement tests."""
    _needs_fast(n)
    low, high = exact_interval(k, n)
    if k > 0:
        t = tail_ge(n, k, Fraction(low))
        assert t <= HALF and HALF - t < Fraction(1, 10**9), (k, n, float(t))
    if k < n:
        t = tail_le(n, k, Fraction(high))
        assert t <= HALF and HALF - t < Fraction(1, 10**9), (k, n, float(t))


@pytest.mark.parametrize("confidence", [0.8, 0.9, 0.99, 0.999, Fraction(19, 20)])
def test_other_confidence_levels_solve_the_same_equations(confidence):
    n, k = 30, 7
    half = (1 - Fraction(confidence)) / 2 if not isinstance(confidence, float) else (1 - Fraction(str(confidence))) / 2
    low, high = exact_interval(k, n, confidence)
    t_low, t_high = tail_ge(n, k, Fraction(low)), tail_le(n, k, Fraction(high))
    assert t_low <= half and half - t_low < Fraction(1, 10**9)
    assert t_high <= half and half - t_high < Fraction(1, 10**9)


# ==== Edge cases ====
@pytest.mark.parametrize("n", [1, 2, 10, 300, 2000])
def test_zero_successes_has_low_exactly_zero_and_the_closed_form_upper_end(n):
    low, high = exact_interval(0, n)
    assert low == 0.0 and isinstance(low, float) and isinstance(high, float)
    assert abs(high - (1 - 0.025 ** (1 / n))) <= 1e-12 and high < 1.0


@pytest.mark.parametrize("n", [1, 2, 10, 300, 2000])
def test_all_successes_has_high_exactly_one_and_the_closed_form_lower_end(n):
    low, high = exact_interval(n, n)
    assert high == 1.0 and isinstance(low, float)
    assert abs(low - 0.025 ** (1 / n)) <= 1e-12 and low > 0.0


# ==== Monotonicity and symmetry ====
@pytest.mark.parametrize("n", [10, 30, 100, 300])
def test_both_ends_strictly_increase_with_the_success_count(n):
    _needs_fast(n)
    ivs = [exact_interval(k, n) for k in range(n + 1)]
    for (l0, h0), (l1, h1) in zip(ivs, ivs[1:]):
        assert l1 > l0 and h1 > h0, (n, (l0, h0), (l1, h1))
    for k, (low, high) in enumerate(ivs):
        assert low <= k / n <= high


@pytest.mark.parametrize("n", [10, 30, 100])
def test_swapping_successes_and_failures_mirrors_the_interval(n):
    _needs_fast(n)
    for k in range(n + 1):
        low, high = exact_interval(k, n)
        low2, high2 = exact_interval(n - k, n)
        assert abs(low2 - (1 - high)) <= 1e-12 and abs(high2 - (1 - low)) <= 1e-12, (k, n)


# ==== Arguments and errors are unchanged ====
@pytest.mark.parametrize(
    "args,exc",
    [
        ((1, True), TypeError), ((1, 2.0), TypeError), ((1, "3"), TypeError), ((True, 3), TypeError), ((1.0, 3), TypeError),
        ((1, 0), ValueError), ((1, -4), ValueError), ((-1, 3), ValueError), ((4, 3), ValueError),
        ((3.5, 0), ValueError),  # trials is checked first: 0 is a ValueError before the float successes is looked at
    ],
)
def test_count_argument_errors_have_the_same_types(args, exc):
    with pytest.raises(exc):
        exact_interval(*args)


@pytest.mark.parametrize("c,exc", [(0, ValueError), (1, ValueError), (0.0, ValueError), (1.0, ValueError), (1.5, ValueError), (-0.1, ValueError), (True, TypeError), ("0.9", TypeError), (float("nan"), ValueError)])
def test_confidence_errors_have_the_same_types(c, exc):
    with pytest.raises(exc):
        exact_interval(1, 5, c)


def test_the_result_is_a_pair_of_python_floats_and_deterministic():
    r = exact_interval(5, 10)
    assert isinstance(r, tuple) and len(r) == 2 and all(type(x) is float for x in r)
    assert r == exact_interval(5, 10)
    assert exact_interval(5, 10) == exact_interval(5, 10, 0.95) == exact_interval(5, 10, Fraction(19, 20))
