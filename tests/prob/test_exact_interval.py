"""Contract tests for dsdk.prob.sampling.exact_interval: the exact (Clopper-Pearson) interval with guaranteed coverage.

Why it exists: the Wilson interval labelled 95% covers the true proportion only about 84% of the time for rare events (exact binomial sums,
see the coverage group below). The exact interval must cover at least 95% for EVERY n and p. The tests check the known textbook values, the
defining tail equations with independent exact arithmetic, the exact coverage over a fine grid of true proportions, the rounding direction
(never narrower than the exact interval), and agreement with the independent JavaScript implementation in the Lab page.
"""
import json
import math
import re
import shutil
import subprocess
from fractions import Fraction
from functools import lru_cache
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from dsdk.prob import exact_interval, wilson_interval

ROOT = Path(__file__).resolve().parents[2]
LAB = ROOT / "lab" / "src" / "lab.html"


def tail_ge(n, k, p):
    """Independent exact P(X >= k) for X ~ Binomial(n, p), p a Fraction."""
    return sum((math.comb(n, i) * p**i * (1 - p) ** (n - i) for i in range(k, n + 1)), Fraction(0))


def tail_le(n, k, p):
    return sum((math.comb(n, i) * p**i * (1 - p) ** (n - i) for i in range(0, k + 1)), Fraction(0))


@lru_cache(maxsize=None)
def interval(k, n):
    return exact_interval(k, n)


def coverage(n, p, intervals):
    """Probability, computed in floats from binomial terms, that the interval built from X ~ Binomial(n, p) contains p."""
    return sum(math.comb(n, k) * p**k * (1 - p) ** (n - k) for k in range(n + 1) if intervals[k][0] <= p <= intervals[k][1])


# ==== Known values from the literature and the Lab ====
@pytest.mark.parametrize(
    "k,n,low,high",
    [(5, 10, 0.1871, 0.8129), (0, 10, 0.0, 0.3085), (33, 35, 0.8084, 0.9930), (10, 10, 0.6915, 1.0), (1, 10, 0.0025, 0.4450), (0, 1, 0.0, 0.975), (1, 1, 0.025, 1.0)],
)
def test_the_exact_interval_matches_known_values_to_four_decimals(k, n, low, high):
    """The 95% exact interval is (0.1871, 0.8129) for 5 of 10, (0, 0.3085) for 0 of 10, (0.8084, 0.9930) for 33 of 35, and the other textbook cases listed, to four decimals."""
    lo, hi = exact_interval(k, n)
    assert round(lo, 4) == pytest.approx(low, abs=1e-4) and round(hi, 4) == pytest.approx(high, abs=1e-4)


def test_zero_successes_has_lower_end_exactly_zero_and_all_successes_upper_end_exactly_one():
    """With no successes the lower end is exactly 0.0 and with all successes the upper end is exactly 1.0, as floats, for several sizes."""
    for n in (1, 2, 7, 30):
        assert exact_interval(0, n)[0] == 0.0 and exact_interval(n, n)[1] == 1.0


def test_the_result_is_a_pair_of_python_floats():
    """The return value is a tuple of two floats with low below high."""
    r = exact_interval(3, 10)
    assert isinstance(r, tuple) and len(r) == 2 and all(type(x) is float for x in r) and r[0] < r[1]


def test_the_default_confidence_is_95_percent_and_float_confidence_is_read_as_its_decimal():
    """The default equals confidence 0.95, which equals the exact fraction 19/20."""
    assert exact_interval(4, 12) == exact_interval(4, 12, 0.95) == exact_interval(4, 12, Fraction(19, 20))


# ==== The defining tail equations hold with independent exact arithmetic ====
@pytest.mark.parametrize("k,n", [(1, 10), (5, 10), (9, 10), (3, 30), (15, 30), (29, 30), (2, 7)])
def test_the_ends_solve_the_tail_equations_and_are_never_narrower_than_the_exact_solution(k, n):
    """At the returned lower end the upper tail P(X >= k) is at most 0.025 but within 1e-9 of it, and at the returned upper end P(X <= k) is at most 0.025 but within 1e-9: each end is the exact solution, rounded outward."""
    lo, hi = interval(k, n)
    t_lo, t_hi = tail_ge(n, k, Fraction(lo)), tail_le(n, k, Fraction(hi))
    half = Fraction(1, 40)
    assert t_lo <= half and half - t_lo < Fraction(1, 10**9)
    assert t_hi <= half and half - t_hi < Fraction(1, 10**9)


def test_edge_ends_have_no_equation_to_solve():
    """For 0 successes the lower end is 0 and for all successes the upper end is 1, whatever the confidence."""
    for c in (0.5, 0.9, 0.99):
        assert exact_interval(0, 9, c)[0] == 0.0 and exact_interval(9, 9, c)[1] == 1.0


def test_the_one_sided_tail_at_the_other_end_of_a_zero_count_interval():
    """For 0 successes in n trials the upper end is 1 - (a/2)^(1/n): for 10 trials 0.30850, matching the closed form to 1e-12."""
    for n in (1, 5, 10, 40):
        assert exact_interval(0, n)[1] == pytest.approx(1 - 0.025 ** (1 / n), abs=1e-12)
        assert exact_interval(n, n)[0] == pytest.approx(0.025 ** (1 / n), abs=1e-12)


def test_rounding_never_moves_an_end_inward():
    """The float ends are on the outer side of the exact solution: at the returned low end the upper tail is at most 0.025 and at the returned high end the lower tail is at most 0.025, for every case here (an end rounded inward would make a tail exceed 0.025)."""
    for k, n in [(5, 10), (1, 10), (9, 10), (33, 35), (2, 7), (1, 1)]:
        lo, hi = interval(k, n)
        assert tail_ge(n, k, Fraction(lo)) <= Fraction(1, 40)
        assert tail_le(n, k, Fraction(hi)) <= Fraction(1, 40) or hi == 1.0


# ==== Guaranteed coverage, where the Wilson interval fails ====
GRID = [i / 1000 for i in range(1, 1000)] + [0.0015, 0.0055, 0.0175, 0.00005, 0.99995]


@pytest.mark.parametrize("n", [10, 30])
def test_exact_coverage_is_at_least_95_percent_for_every_true_proportion_on_a_fine_grid(n):
    """For n = 10 and n = 30 and every true proportion on a grid of 1,000 values (including the rare-event values 0.0015, 0.0055, 0.0175), the exact probability that the interval contains the truth is at least 0.95 (minus 1e-9 for float summation)."""
    ivs = [interval(k, n) for k in range(n + 1)]
    worst = min(coverage(n, p, ivs) for p in GRID)
    assert worst >= 0.95 - 1e-9, worst


def test_exact_coverage_for_n_50_on_a_coarser_grid():
    """For n = 50, coverage is at least 95% on every true proportion in steps of 0.0025."""
    n = 50
    ivs = [interval(k, n) for k in range(n + 1)]
    assert min(coverage(n, i / 400, ivs) for i in range(1, 400)) >= 0.95 - 1e-9


@pytest.mark.parametrize("n", [10, 30])
def test_the_wilson_interval_fails_the_same_coverage_test(n):
    """On the same grid the 95% Wilson interval's exact coverage drops below 90% (it is about 83.8% at n=10 and 84.8% at n=30), so the guarantee is real and the test can fail."""
    ivs = [wilson_interval(k, n) for k in range(n + 1)]
    worst = min(coverage(n, p, ivs) for p in GRID)
    assert worst < 0.90, worst


def test_coverage_is_conservative_not_exactly_95_percent_somewhere():
    """The exact interval is conservative: its coverage never dips below the level, and it is strictly above 95% on a typical true proportion (this is what 'at least' means)."""
    n = 30
    ivs = [interval(k, n) for k in range(n + 1)]
    assert coverage(n, 0.3, ivs) > 0.95


def test_exact_rational_coverage_at_chosen_proportions():
    """At true proportions 1/100, 1/10 and 1/2 for n = 10 the coverage, summed in exact fractions over the float ends, is at least 19/20."""
    n = 10
    ivs = [interval(k, n) for k in range(n + 1)]
    for p in (Fraction(1, 100), Fraction(1, 10), Fraction(1, 2)):
        c = sum((math.comb(n, k) * p**k * (1 - p) ** (n - k) for k in range(n + 1) if Fraction(ivs[k][0]) <= p <= Fraction(ivs[k][1])), Fraction(0))
        assert c >= Fraction(19, 20)


# ==== Shape of the interval ====
@settings(max_examples=40, deadline=None)
@given(st.integers(min_value=1, max_value=40).flatmap(lambda n: st.tuples(st.integers(min_value=0, max_value=n), st.just(n))))
def test_the_interval_contains_the_observed_proportion_and_stays_inside_zero_one(kn):
    """For every count the interval contains the observed proportion and lies in [0, 1]."""
    k, n = kn
    lo, hi = interval(k, n)
    assert 0.0 <= lo <= k / n <= hi <= 1.0


def test_both_ends_never_decrease_as_the_success_count_grows():
    """For a fixed number of trials, more successes move both ends up (weakly)."""
    for n in (5, 12, 25):
        ivs = [interval(k, n) for k in range(n + 1)]
        assert all(a[0] <= b[0] and a[1] <= b[1] for a, b in zip(ivs, ivs[1:]))


def test_the_interval_is_symmetric_under_swapping_successes_and_failures():
    """The interval for n-k successes is one minus the interval for k successes, with ends swapped, to within the outward rounding of a few ulp."""
    for n in (7, 20):
        for k in range(n + 1):
            lo, hi = interval(k, n)
            lo2, hi2 = interval(n - k, n)
            assert lo2 == pytest.approx(1 - hi, abs=1e-12) and hi2 == pytest.approx(1 - lo, abs=1e-12)


def test_more_confidence_gives_a_wider_interval_and_more_trials_a_narrower_one():
    """Confidence 0.99 is wider than 0.95, which is wider than 0.80; and 10 times more trials at the same proportion halve the width roughly."""
    w = lambda c: (lambda lo, hi: hi - lo)(*exact_interval(7, 20, c))
    assert w(0.99) > w(0.95) > w(0.80)
    small, large = (lambda r: r[1] - r[0])(interval(5, 10)), (lambda r: r[1] - r[0])(interval(50, 100))
    assert large < small


def test_the_exact_interval_is_wider_than_wilson_at_the_centre_and_at_zero_successes():
    """At 5 of 10 the exact interval (0.187, 0.813) is wider than Wilson's (0.237, 0.763); at 0 of 10 the exact upper end 0.3085 exceeds Wilson's 0.2775."""
    e, w = interval(5, 10), wilson_interval(5, 10)
    assert e[0] < w[0] and e[1] > w[1]
    assert interval(0, 10)[1] > wilson_interval(0, 10)[1]


# ==== Argument rules ====
@pytest.mark.parametrize("args,exc", [((1, 0), ValueError), ((11, 10), ValueError), ((-1, 10), ValueError), ((1.0, 10), TypeError), ((1, 10.0), TypeError), ((True, 10), TypeError), ((1, True), TypeError), (("1", 10), TypeError)])
def test_count_arguments_follow_the_same_rules_as_the_other_interval_functions(args, exc):
    """Zero trials, more successes than trials and negative successes are a ValueError; floats, bools and strings as counts are a TypeError."""
    with pytest.raises(exc):
        exact_interval(*args)


@pytest.mark.parametrize("c,exc", [(0, ValueError), (1, ValueError), (0.0, ValueError), (1.0, ValueError), (-0.1, ValueError), (1.5, ValueError), (float("nan"), ValueError), (True, TypeError), ("0.95", TypeError), (None, TypeError)])
def test_confidence_must_lie_strictly_between_zero_and_one(c, exc):
    """Confidence 0 or 1 (exactly), outside [0, 1], nan: ValueError; a bool, a string or None: TypeError."""
    with pytest.raises(exc):
        exact_interval(3, 10, c)


def test_the_function_is_deterministic():
    """The same arguments always give the same pair, bit for bit."""
    assert exact_interval(13, 40) == exact_interval(13, 40)


# ==== Agreement with the independent JavaScript implementation in the Lab page ====
CASES = [(5, 10), (0, 10), (10, 10), (33, 35), (1, 10), (27, 28), (8, 8), (0, 1), (1, 1), (3, 100), (50, 100)]


def lab_source():
    text = LAB.read_text()
    start = text.index("function binomCdf(")
    end = text.index("\n\n// ---------- Logic Cave", start)
    return text[start:end]


@pytest.mark.skipif(shutil.which("node") is None or not LAB.exists(), reason="node or the Lab page source is not available")
def test_the_labs_javascript_exact_interval_agrees_with_the_python_one_on_the_same_cases():
    """Running the Lab page's own binomCdf and exact functions (extracted verbatim from lab/src/lab.html) in node gives the same 95% interval as the Python function for 11 cases, including 5/10, 0/10 and 33/35, to within 1e-9."""
    script = lab_source() + "\nconst out=" + json.dumps(CASES) + ".map(([k,n])=>exact(k,n)); console.log(JSON.stringify(out));"
    js = json.loads(subprocess.run(["node", "-e", script], capture_output=True, text=True, timeout=60, check=True).stdout)
    for (k, n), (jlo, jhi) in zip(CASES, js):
        lo, hi = exact_interval(k, n)
        assert lo == pytest.approx(jlo, abs=1e-9) and hi == pytest.approx(jhi, abs=1e-9), (k, n)


@pytest.mark.skipif(shutil.which("node") is None or not LAB.exists(), reason="node or the Lab page source is not available")
def test_the_lab_source_still_contains_the_functions_this_test_extracts():
    """The extraction markers exist in the Lab source, so the cross-check cannot silently test nothing."""
    src = lab_source()
    assert "function exact(" in src and "function binomCdf(" in src
