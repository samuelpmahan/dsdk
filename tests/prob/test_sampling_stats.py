"""Contract tests for the statistics layer of dsdk.prob.sampling: standard_error, wilson_interval, Estimate/Comparison builders and
the shared inverse-CDF draw primitive.

The draw algorithm is pinned: ``random.Random(seed).random()`` per draw, ``bisect_right`` on float cumulative shares. The tests
re-implement it independently so an alternative (e.g. random.choices) cannot slip in.
"""
import bisect
import math
import random
from fractions import Fraction

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from dsdk.prob import Comparison, Estimate, Z95, inverse_cdf_draws, make_comparison, make_estimate, standard_error, wilson_interval

from prob_helpers import Fr


# ==== Standard error of a sampled proportion ====
def test_standard_error_known_values():
    """The standard error is 0.05 for 50 successes in 100 trials, 0 at the extremes, and matches sqrt(p(1-p)/n) for 1 in 4."""
    assert standard_error(50, 100) == pytest.approx(0.05)
    assert standard_error(0, 10) == 0.0 and standard_error(10, 10) == 0.0
    assert standard_error(1, 4) == pytest.approx(math.sqrt(0.25 * 0.75 / 4))


@pytest.mark.parametrize("args,exc", [((1, 0), ValueError), ((-1, 5), ValueError), ((6, 5), ValueError), ((1.0, 5), TypeError), ((1, 5.0), TypeError), ((True, 5), TypeError), ((1, True), TypeError), (("1", 5), TypeError)])
def test_standard_error_argument_rules(args, exc):
    """Trials must be an int of at least 1, successes an int between 0 and trials, and bools and floats are a TypeError."""
    with pytest.raises(exc):
        standard_error(*args)


def test_standard_error_shrinks_like_one_over_sqrt_n():
    """Ten times more trials at the same proportion divides the standard error by the square root of ten."""
    assert standard_error(500, 1000) == pytest.approx(standard_error(50, 100) / math.sqrt(10))


# ==== Wilson 95% interval of a sampled proportion ====
def test_wilson_known_values():
    """The 95% Wilson interval for 50 of 100 is (0.4038, 0.5962), for 0 of 10 it starts at exactly 0 and ends near 0.2775, and for 10 of 10 it ends at exactly 1."""
    lo, hi = wilson_interval(50, 100)
    assert (round(lo, 4), round(hi, 4)) == (0.4038, 0.5962)
    lo, hi = wilson_interval(0, 10)
    assert lo == 0.0 and hi == pytest.approx(0.2775, abs=1e-3)
    lo, hi = wilson_interval(10, 10)
    assert hi == 1.0 and lo == pytest.approx(0.7225, abs=1e-3)


def test_wilson_does_not_collapse_at_the_extremes_unlike_the_plain_interval():
    """With 0 successes the upper end is above 0, and with all successes the lower end is below 1, so the interval never collapses to a point."""
    for trials in (1, 5, 50):
        lo, hi = wilson_interval(0, trials)
        assert hi > 0
        lo, hi = wilson_interval(trials, trials)
        assert lo < 1


def test_wilson_default_z_is_z95_and_z_matters():
    """The default z is 1.96, and a larger z gives a wider interval than a smaller one around the same data."""
    assert Z95 == 1.96
    assert wilson_interval(30, 100) == wilson_interval(30, 100, Z95)
    narrow, wide = wilson_interval(30, 100, 1.0), wilson_interval(30, 100, 3.0)
    assert wide[0] < narrow[0] < narrow[1] < wide[1]


@pytest.mark.parametrize("z,exc", [(0, ValueError), (-1.0, ValueError), (float("inf"), ValueError), (float("nan"), ValueError), ("1.96", TypeError), (True, TypeError)])
def test_wilson_z_rules(z, exc):
    """z must be a positive finite number: zero, negative, infinite or nan is a ValueError, and a string or bool is a TypeError."""
    with pytest.raises(exc):
        wilson_interval(5, 10, z)


@pytest.mark.parametrize("args,exc", [((1, 0), ValueError), ((11, 10), ValueError), ((-1, 10), ValueError), ((1.5, 10), TypeError), ((True, 10), TypeError)])
def test_wilson_count_rules(args, exc):
    """The interval rejects zero trials, more successes than trials and negative successes (ValueError), and float or bool counts (TypeError)."""
    with pytest.raises(exc):
        wilson_interval(*args)


@settings(max_examples=100)
@given(st.integers(min_value=1, max_value=500).flatmap(lambda n: st.tuples(st.integers(min_value=0, max_value=n), st.just(n))))
def test_wilson_interval_properties(kn):
    """For every number of trials up to 500 and every success count, the interval lies inside [0, 1], contains the observed proportion, has positive width, and strictly surrounds it unless the proportion is 0 or 1."""
    k, n = kn
    lo, hi = wilson_interval(k, n)
    assert 0.0 <= lo <= k / n <= hi <= 1.0
    assert lo < hi
    if k not in (0, n):
        centre_ok = lo < k / n < hi
        assert centre_ok


def test_wilson_is_symmetric_under_swapping_success_and_failure():
    """Swapping successes and failures mirrors the interval: the interval for 3 of 20 is one minus the interval for 17 of 20."""
    lo, hi = wilson_interval(3, 20)
    lo2, hi2 = wilson_interval(17, 20)
    assert lo == pytest.approx(1 - hi2) and hi == pytest.approx(1 - lo2)


# ==== Estimates and exact-versus-sampled comparisons are built from counts ====
def test_make_estimate_fields():
    """An estimate built from counts records the counts, the observed proportion, the standard error and the Wilson interval."""
    e = make_estimate(30, 100, 120)
    assert isinstance(e, Estimate)
    assert (e.successes, e.trials, e.drawn) == (30, 100, 120)
    assert e.p_hat == 0.3
    assert e.stderr == standard_error(30, 100)
    assert (e.low, e.high) == wilson_interval(30, 100)



def test_make_estimate_accepts_a_single_trial():
    """The smallest legal estimate is one trial: one success in one draw gives p_hat 1 and a Wilson interval ending at 1, and zero successes gives p_hat 0 (the rule is 'at least one trial', not two)."""
    e = make_estimate(1, 1, 1)
    assert (e.successes, e.trials, e.drawn, e.p_hat) == (1, 1, 1, 1.0) and e.high == wilson_interval(1, 1)[1]
    assert make_estimate(0, 1, 3).p_hat == 0.0

@pytest.mark.parametrize("args,exc", [((1, 5, 4), ValueError), ((1, 0, 5), ValueError), ((6, 5, 5), ValueError), ((1, 5, 0), ValueError), ((1, 5.0, 5), TypeError)])
def test_make_estimate_rules(args, exc):
    """An estimate cannot have fewer draws than trials, zero trials, more successes than trials, or non-integer counts."""
    with pytest.raises(exc):
        make_estimate(*args)


def test_make_comparison_fields_covered_and_not():
    """A comparison records the exact value, the absolute error, the z-score, and whether the interval covers the exact value; an exact match has zero error and a far-off value is reported as not covered."""
    e = make_estimate(50, 100, 100)
    c = make_comparison(Fr(1, 2), e)
    assert isinstance(c, Comparison)
    assert c.exact == Fr(1, 2) and c.estimate is e
    assert c.error == 0.0 and c.z_score == 0.0 and c.covered is True
    far = make_comparison(Fr(9, 10), e)
    assert far.error == pytest.approx(0.4) and far.z_score == pytest.approx(0.4 / 0.05) and far.covered is False


def test_make_comparison_zero_stderr_cases():
    """When the standard error is zero the z-score is 0 for an exact hit and infinity for a miss."""
    hit = make_comparison(Fr(1), make_estimate(10, 10, 10))
    assert hit.error == 0.0 and hit.z_score == 0.0 and hit.covered
    miss = make_comparison(Fr(1, 2), make_estimate(10, 10, 10))
    assert miss.z_score == math.inf and not miss.covered


def test_covered_uses_the_wilson_interval_inclusive():
    """The interval is closed: an exact value sitting at the interval's end counts as covered, and a value outside does not."""
    e = make_estimate(0, 10, 10)
    assert make_comparison(Fr(0), e).covered
    assert not make_comparison(Fr(1, 2), e).covered


# ==== Seeded inverse-CDF draws follow the weights and are reproducible ====
def reference_draws(weights, n, seed):
    total = sum(weights)
    cum, run = [], Fraction(0)
    for w in weights:
        run += w
        cum.append(float(run / total))
    rng = random.Random(seed)
    return tuple(bisect.bisect_right(cum, rng.random()) for _ in range(n))


def test_draws_match_the_documented_algorithm():
    """The draws equal an independent re-implementation of the documented algorithm (one uniform draw per sample, first cumulative share above it)."""
    ws = [Fr(1, 5), Fr(3, 10), Fr(1, 2)]
    assert inverse_cdf_draws(ws, 50, 11) == reference_draws(ws, 50, 11)


def test_golden_draws_for_a_fixed_seed():
    """Pinned values: any change of the algorithm (even to another correct sampler) breaks reproducibility for users."""
    assert inverse_cdf_draws([Fr(1, 2), Fr(1, 2)], 10, 7) == reference_draws([Fr(1, 2), Fr(1, 2)], 10, 7)
    assert inverse_cdf_draws([Fr(4, 9), Fr(4, 9), Fr(1, 9)], 12, 2024) == reference_draws([Fr(4, 9), Fr(4, 9), Fr(1, 9)], 12, 2024)
    assert random.Random(7).random() < 0.5  # the first draw above is index 0 for seed 7 under the pinned generator
    assert inverse_cdf_draws([Fr(1, 2), Fr(1, 2)], 1, 7) == (0,)


def test_draws_are_deterministic_and_prefix_stable():
    """The same weights, count and seed give the same draws; fewer draws are a prefix of more draws; a different seed gives different draws."""
    ws = [Fr(1), Fr(2), Fr(3)]
    long = inverse_cdf_draws(ws, 40, 5)
    assert inverse_cdf_draws(ws, 40, 5) == long
    assert inverse_cdf_draws(ws, 10, 5) == long[:10]
    assert inverse_cdf_draws(ws, 40, 6) != long


def test_weights_need_not_be_normalised():
    """Weights that are proportional give identical draws, so callers need not normalise."""
    assert inverse_cdf_draws([Fr(2), Fr(6)], 30, 3) == inverse_cdf_draws([Fr(1, 4), Fr(3, 4)], 30, 3)


def test_zero_weight_outcomes_are_never_drawn_even_first_or_last():
    """Outcomes with weight zero, including the first and last positions, are never drawn in 2000 draws."""
    ws = [Fr(0), Fr(1, 3), Fr(0), Fr(2, 3), Fr(0)]
    draws = inverse_cdf_draws(ws, 2000, 1)
    assert set(draws) <= {1, 3}
    assert set(draws) == {1, 3}


def test_single_outcome_and_zero_draws():
    """A single outcome is always drawn, and asking for zero draws gives the empty tuple."""
    assert inverse_cdf_draws([Fr(5)], 4, 0) == (0, 0, 0, 0)
    assert inverse_cdf_draws([Fr(1, 2), Fr(1, 2)], 0, 9) == ()


def test_empirical_frequencies_follow_the_weights():
    """In 20000 draws each outcome's frequency is within 5 standard deviations of its weight."""
    ws = [Fr(1, 10), Fr(2, 10), Fr(7, 10)]
    n = 20000
    draws = inverse_cdf_draws(ws, n, 123)
    for i, w in enumerate(ws):
        assert abs(draws.count(i) / n - float(w)) < 5 * math.sqrt(float(w) * (1 - float(w)) / n)


@pytest.mark.parametrize(
    "weights,n,seed,exc",
    [
        ([], 1, 0, ValueError),
        ([Fr(0), Fr(0)], 1, 0, ValueError),
        ([Fr(-1), Fr(2)], 1, 0, ValueError),
        ([0.5, 0.5], 1, 0, TypeError),
        ([1, 2], 1, 0, TypeError),
        ([Fr(1)], -1, 0, ValueError),
        ([Fr(1)], 1.5, 0, TypeError),
        ([Fr(1)], True, 0, TypeError),
        ([Fr(1)], 1, 1.5, TypeError),
        ([Fr(1)], 1, True, TypeError),
        ([Fr(1)], 1, "7", TypeError),
    ],
)
def test_draw_argument_rules(weights, n, seed, exc):
    """Empty, all-zero, negative, float or int weights and bad counts or seeds are rejected with the documented ValueError or TypeError."""
    with pytest.raises(exc):
        inverse_cdf_draws(weights, n, seed)


def test_negative_and_large_seeds_are_ints_like_any_other():
    """Negative seeds and seeds larger than 64 bits are valid and reproduce the reference stream."""
    assert inverse_cdf_draws([Fr(1, 2), Fr(1, 2)], 5, -3) == reference_draws([Fr(1, 2), Fr(1, 2)], 5, -3)
    assert inverse_cdf_draws([Fr(1, 2), Fr(1, 2)], 5, 2**80) == reference_draws([Fr(1, 2), Fr(1, 2)], 5, 2**80)


@settings(max_examples=50)
@given(st.lists(st.integers(min_value=0, max_value=5), min_size=1, max_size=6).filter(lambda l: sum(l) > 0), st.integers(min_value=0, max_value=2**32), st.integers(min_value=0, max_value=30))
def test_draws_property_against_reference(ws, seed, n):
    """For random integer weights, seeds and counts, the draws equal the reference implementation and never select a zero-weight outcome."""
    frs = [Fr(w) for w in ws]
    got = inverse_cdf_draws(frs, n, seed)
    assert got == reference_draws(frs, n, seed)
    assert all(ws[i] > 0 for i in got)
