"""Contract tests: sampling the next-track model, exact-vs-sampled comparison, and held-out log loss (the Lost Lands instruments)."""
import math
from fractions import Fraction

import pytest

from dsdk.core import Status
from dsdk.prob import (
    Comparison, compare_next_track, fit_next_track, held_out_log_loss, inverse_cdf_draws, next_track_distribution,
    sample_next_tracks,
)

from prob_helpers import Fr

SEQS = [["a", "b", "c"], ["a", "b", "d"], ["b", "c"], ["a"]]
M = fit_next_track(SEQS)  # alpha 1; P(.|b) = a 1/7, b 1/7, c 3/7, d 2/7
M0 = fit_next_track(SEQS, alpha=0)


def known(j):
    assert j.status is Status.KNOWN, j
    return j.value


# ==== Sampling successor tracks ====
def test_samples_are_tracks_deterministic_and_match_the_shared_primitive():
    """Sampled successors are vocabulary tracks, repeat for the same seed, differ for another, and equal the shared inverse-CDF draw over the distribution."""
    s = known(sample_next_tracks(M, "b", 30, 5))
    assert isinstance(s, tuple) and len(s) == 30 and set(s) <= set(M.tracks)
    assert known(sample_next_tracks(M, "b", 30, 5)) == s
    probs = [p for _, p in known(next_track_distribution(M, "b"))]
    assert s == tuple(M.tracks[i] for i in inverse_cdf_draws(probs, 30, 5))
    assert known(sample_next_tracks(M, "b", 30, 6)) != s


def test_unsmoothed_model_never_samples_an_unseen_successor():
    """With smoothing 0 only successors that were actually observed (c and d after b) are ever sampled in 3000 draws."""
    s = known(sample_next_tracks(M0, "b", 3000, 1))
    assert set(s) == {"c", "d"}


def test_sample_frequencies_follow_the_distribution():
    """In 20000 samples every successor's frequency is within 5 standard deviations of its exact probability."""
    n = 20000
    s = known(sample_next_tracks(M, "b", n, 9))
    for t, p in known(next_track_distribution(M, "b")):
        p = float(p)
        assert abs(s.count(t) / n - p) < 5 * math.sqrt(p * (1 - p) / n)


def test_sampling_zero_draws():
    """Zero samples is a KNOWN empty tuple."""
    assert known(sample_next_tracks(M, "b", 0, 1)) == ()


def test_sampling_passes_through_missing_distributions():
    """An unseen track is NOT_OBSERVED and an empty unsmoothed row is UNKNOWN when sampling."""
    assert sample_next_tracks(M, "zzz", 5, 1).status is Status.NOT_OBSERVED
    assert sample_next_tracks(M0, "c", 5, 1).status is Status.UNKNOWN


@pytest.mark.parametrize("n,seed,exc", [(-1, 0, ValueError), (1.0, 0, TypeError), (True, 0, TypeError), (1, 0.5, TypeError), (1, True, TypeError)])
def test_sampling_argument_errors_even_for_missing_distributions(n, seed, exc):
    """A bad count or seed is rejected even when the track has no distribution."""
    with pytest.raises(exc):
        sample_next_tracks(M, "b", n, seed)
    with pytest.raises(exc):
        sample_next_tracks(M, "zzz", n, seed)


# ==== Exact next-track probability next to its sampled estimate ====
def test_comparison_exact_value_and_counts():
    """The comparison holds the exact probability 3/7 and an estimate whose success count equals the number of sampled c's among 5000 draws."""
    c = known(compare_next_track(M, "b", "c", 5000, 3))
    assert isinstance(c, Comparison) and c.exact == Fr(3, 7)
    draws = known(sample_next_tracks(M, "b", 5000, 3))
    assert (c.estimate.successes, c.estimate.trials, c.estimate.drawn) == (draws.count("c"), 5000, 5000)
    assert c.covered == (c.estimate.low <= 3 / 7 <= c.estimate.high)


def test_sampled_error_is_honest_over_many_seeds():
    """Across 200 seeds the 95% interval covers the exact value in 180 to 200 cases, and 100 times more draws shrinks the average error at least 5 times."""
    covered = sum(known(compare_next_track(M, "b", "c", 1500, s)).covered for s in range(200))
    assert 180 <= covered <= 200
    small = sum(known(compare_next_track(M, "b", "c", 100, s)).error for s in range(50)) / 50
    large = sum(known(compare_next_track(M, "b", "c", 10000, s)).error for s in range(50)) / 50
    assert large < small / 5


def test_a_zero_probability_target_is_estimated_as_zero_and_covered():
    """A target with exact probability 0 gets zero successes, is covered, and has z-score 0."""
    c = known(compare_next_track(M0, "b", "a", 400, 1))
    assert c.exact == 0 and c.estimate.successes == 0 and c.covered and c.z_score == 0.0


def test_comparison_not_observed_unknown_and_zero_draws():
    """An unseen track or target is NOT_OBSERVED, an empty unsmoothed row is UNKNOWN, and zero draws is UNKNOWN."""
    assert compare_next_track(M, "zzz", "a", 10, 1).status is Status.NOT_OBSERVED
    assert compare_next_track(M, "b", "zzz", 10, 1).status is Status.NOT_OBSERVED
    assert compare_next_track(M0, "c", "a", 10, 1).status is Status.UNKNOWN
    j = compare_next_track(M, "b", "c", 0, 1)
    assert j.status is Status.UNKNOWN and j.value is None


def test_comparison_argument_errors():
    """A negative count or a non-integer seed is rejected."""
    with pytest.raises(ValueError):
        compare_next_track(M, "b", "c", -1, 1)
    with pytest.raises(TypeError):
        compare_next_track(M, "b", "c", 5, "x")


# ==== Scoring held-out transitions with log loss ====
def test_log_loss_by_hand():
    """The held-out loss of (b,c) and (a,b) is the mean of -ln(3/7) and -ln(1/2), computed by hand."""
    pairs = [("b", "c"), ("a", "b")]
    expected = (-math.log(3 / 7) - math.log(1 / 2)) / 2
    assert known(held_out_log_loss(M, pairs)) == pytest.approx(expected)


def test_a_uniform_model_has_loss_log_vocabulary_size():
    """A model with no data and smoothing 1 over 4 tracks has loss ln 4 on any pairs."""
    m = fit_next_track([], alpha=1, vocabulary=list("abcd"))
    assert known(held_out_log_loss(m, [("a", "b"), ("c", "c")])) == pytest.approx(math.log(4))


def test_smoothing_rescues_a_held_out_transition_the_raw_model_calls_impossible():
    """A held-out pair the unsmoothed model calls impossible is INVALID, while the smoothed model scores it at -ln(1/7)."""
    pairs = [("b", "a")]
    j0 = held_out_log_loss(M0, pairs)
    assert j0.status is Status.INVALID and j0.value is None and "probability zero" in j0.reason
    assert known(held_out_log_loss(M, pairs)) == pytest.approx(-math.log(1 / 7))


def test_track_without_a_distribution_makes_the_loss_invalid():
    """A held-out pair starting at a track with no distribution makes the loss INVALID."""
    j = held_out_log_loss(M0, [("c", "a")])
    assert j.status is Status.INVALID


def test_one_impossible_pair_poisons_the_average():
    """One impossible pair among possible ones makes the whole loss INVALID rather than being skipped."""
    assert held_out_log_loss(M0, [("b", "c"), ("b", "a")]).status is Status.INVALID


def test_unseen_tracks_are_not_observed_even_with_smoothing():
    """A pair that mentions a track outside the vocabulary is NOT_OBSERVED even with smoothing."""
    j = held_out_log_loss(M, [("b", "c"), ("zzz", "a")])
    assert j.status is Status.NOT_OBSERVED and "zzz" in j.reason
    assert held_out_log_loss(M, [("a", "zzz")]).status is Status.NOT_OBSERVED


def test_not_observed_is_reported_before_invalid():
    """When both an impossible pair and an unseen track are present, the answer is NOT_OBSERVED."""
    assert held_out_log_loss(M0, [("b", "a"), ("zzz", "a")]).status is Status.NOT_OBSERVED


def test_no_pairs_is_unknown():
    """Scoring zero pairs is UNKNOWN."""
    j = held_out_log_loss(M, [])
    assert j.status is Status.UNKNOWN and j.value is None


def test_pairs_can_be_a_generator_and_are_type_checked():
    """Pairs may come from a generator, and shapes other than a 2-tuple of strings are a TypeError."""
    assert known(held_out_log_loss(M, (p for p in [("b", "c")]))) == pytest.approx(-math.log(3 / 7))
    for bad in ([("b",)], [["b", "c"]], [("b", 1)], ["bc"]):
        with pytest.raises(TypeError):
            held_out_log_loss(M, bad)
    with pytest.raises(TypeError):
        held_out_log_loss("model", [("b", "c")])


def test_better_model_has_lower_loss_on_data_it_was_fit_to():
    """A model fit to the pairs beats the uniform model on them: the instrument can rank recommenders."""
    uniform = fit_next_track([], vocabulary=list("abcd"))
    pairs = [(x, y) for s in SEQS for x, y in zip(s, s[1:])]
    assert known(held_out_log_loss(M, pairs)) < known(held_out_log_loss(uniform, pairs))


def test_smaller_alpha_is_better_on_training_pairs_larger_on_unseen_ones():
    """Smaller smoothing scores a seen transition better and a never-seen transition worse than larger smoothing."""
    train = [("b", "c")]
    unseen = [("b", "a")]
    lo, hi = fit_next_track(SEQS, alpha=Fr(1, 10)), fit_next_track(SEQS, alpha=1)
    assert known(held_out_log_loss(lo, train)) < known(held_out_log_loss(hi, train))
    assert known(held_out_log_loss(lo, unseen)) > known(held_out_log_loss(hi, unseen))
