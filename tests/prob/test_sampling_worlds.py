"""Contract tests: seeded sampling of beliefs and Bayes nets, and exact-vs-sampled comparison with Monte Carlo error.

Explainable: the sampler is a noisy estimate of the exact answer and says how noisy. Adversarial: impossible evidence -- exact says
INVALID (it can prove impossibility), the sampler says UNKNOWN (it only sees 'nothing accepted'); neither may invent a number.
"""
import math
import random
from fractions import Fraction

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from dsdk.core import Judgment, Status
from dsdk.graph import topological_order
from dsdk.logic import And, Const, Not, Or, Var, evaluate
from dsdk.prob import (
    Comparison, Estimate, compare_with_exact, condition, estimate_probability, forward_sample, inverse_cdf_draws, joint_belief,
    make_estimate, marginals, prior_belief, probability, sample_worlds,
)

from prob_helpers import Fr, SPRINKLER_NODES, burglary, make_net, sprinkler

A, B = Var("A"), Var("B")
BREEZE = Or(A, B)
PRIOR = prior_belief({"A": 0.2, "B": 0.2})
POSTERIOR = condition(PRIOR, BREEZE)  # unnormalised; the sampler normalises


def known(j):
    assert j.status is Status.KNOWN, j
    return j.value


# ==== Sampling possible worlds from a belief ====
def test_sample_worlds_shape_and_determinism():
    """Sampling gives a tuple of n worlds, each a world of the belief; the same seed repeats the sample and a different seed changes it."""
    s = known(sample_worlds(PRIOR, 25, 4))
    assert isinstance(s, tuple) and len(s) == 25
    assert all(item in {w.values for w in PRIOR.worlds} for item in s)
    assert known(sample_worlds(PRIOR, 25, 4)) == s
    assert known(sample_worlds(PRIOR, 25, 5)) != s


def test_sample_worlds_matches_the_shared_draw_primitive():
    """World sampling is exactly the shared inverse-CDF draw applied to the world weights, with no separate random calls."""
    draws = inverse_cdf_draws([w.weight for w in PRIOR.worlds], 40, 99)
    assert known(sample_worlds(PRIOR, 40, 99)) == tuple(PRIOR.worlds[i].values for i in draws)


def test_sample_worlds_never_returns_zero_weight_worlds():
    """Worlds with weight zero are never sampled, so after seeing a breeze the pit-free world never appears."""
    s = known(sample_worlds(POSTERIOR, 3000, 8))
    assert (("A", False), ("B", False)) not in s, "the 'Neither' world is impossible given the breeze"
    assert set(s) == {w.values for w in POSTERIOR.worlds if w.weight > 0}


def test_sample_frequencies_match_the_exact_posterior():
    """Sampling the Wumpus posterior 30000 times gives frequencies within 5 standard deviations of 4/9, 4/9 and 1/9."""
    n = 30000
    s = known(sample_worlds(POSTERIOR, n, 2))
    for values, p in [((("A", True), ("B", False)), 4 / 9), ((("A", False), ("B", True)), 4 / 9), ((("A", True), ("B", True)), 1 / 9)]:
        assert abs(s.count(values) / n - p) < 5 * math.sqrt(p * (1 - p) / n)


def test_sample_zero_draws_is_known_empty():
    """Asking for zero samples is a KNOWN empty tuple."""
    assert sample_worlds(PRIOR, 0, 1) == Judgment(Status.KNOWN, (), "")


def test_sample_from_a_dead_belief_is_invalid():
    """Sampling from a belief whose total weight is zero is INVALID, because there is nothing to sample."""
    dead = condition(PRIOR, And(A, Not(A)))
    j = sample_worlds(dead, 5, 0)
    assert j.status is Status.INVALID and "zero total weight" in j.reason


@pytest.mark.parametrize("args", [("b", 3, 0), (PRIOR, 3.0, 0), (PRIOR, -1, 0), (PRIOR, True, 0), (PRIOR, 3, 1.5), (PRIOR, 3, True), (PRIOR, 3, "0")])
def test_sample_worlds_argument_errors(args):
    """A non-belief, a float, negative or bool count, and a float, bool or string seed are all rejected."""
    with pytest.raises((TypeError, ValueError)):
        sample_worlds(*args)


def test_argument_errors_win_over_invalid_belief():
    """Argument errors are raised even when the belief is dead, so a bad count is never hidden behind an INVALID answer."""
    dead = condition(PRIOR, Const(False))
    with pytest.raises(ValueError):
        sample_worlds(dead, -1, 0)
    with pytest.raises(TypeError):
        sample_worlds(dead, 1, "x")


# ==== Estimating a probability by sampling, with rejection for evidence ====
def test_unconditional_estimate_counts_hits_among_the_draws():
    """An unconditional estimate counts how many of the sampled worlds satisfy the query and records n trials and n draws."""
    j = estimate_probability(PRIOR, A, 1000, 3)
    e = known(j)
    assert isinstance(e, Estimate)
    samples = known(sample_worlds(PRIOR, 1000, 3))
    hits = sum(1 for v in samples if dict(v)["A"])
    assert (e.successes, e.trials, e.drawn) == (hits, 1000, 1000)
    assert e == make_estimate(hits, 1000, 1000)


def test_conditional_estimate_is_rejection_sampling_from_the_prior():
    """A conditional estimate draws from the prior, keeps only worlds satisfying the evidence, and counts the query among the kept ones; about 36% of Wumpus prior draws survive the breeze."""
    e = known(estimate_probability(PRIOR, A, 4000, 6, given=BREEZE))
    samples = known(sample_worlds(PRIOR, 4000, 6))
    kept = [dict(v) for v in samples if evaluate(BREEZE, dict(v))]
    assert e.drawn == 4000 and e.trials == len(kept) < 4000
    assert e.successes == sum(1 for a in kept if a["A"])
    assert e.trials == pytest.approx(4000 * 9 / 25, rel=0.1), "about 36% of prior draws contain a pit"


def test_conditional_estimate_covers_the_wumpus_posterior_5_9():
    """With 20000 draws the estimate of P(pit at A | breeze) is within 4 standard errors of 5/9 and its interval contains 5/9."""
    e = known(estimate_probability(PRIOR, A, 20000, 10, given=BREEZE))
    assert abs(e.p_hat - 5 / 9) < 4 * e.stderr
    assert e.low <= 5 / 9 <= e.high


def test_estimate_of_a_certain_event_has_zero_stderr_but_a_nondegenerate_interval():
    """An event that always happens has proportion 1 and standard error 0, yet its Wilson interval still has a lower end below 1."""
    e = known(estimate_probability(PRIOR, Const(True), 50, 1))
    assert e.p_hat == 1.0 and e.stderr == 0.0 and e.low < 1.0 and e.high == 1.0


def test_impossible_evidence_is_unknown_for_the_sampler_not_invalid_and_not_a_number():
    """When no draw satisfies impossible evidence the sampler answers UNKNOWN (it cannot tell impossible from rare) and never a number."""
    for evidence in (And(A, Not(A)), Const(False)):
        j = estimate_probability(PRIOR, A, 500, 1, given=evidence)
        assert j.status is Status.UNKNOWN and j.value is None
        assert "impossible" in j.reason and "rare" in j.reason


def test_rare_evidence_is_also_unknown_with_too_few_draws():
    """Very rare but possible evidence also gives UNKNOWN when 20 draws contain none."""
    rare = prior_belief({"A": Fr(1, 1000), "B": Fr(1, 1000)})
    j = estimate_probability(rare, A, 20, 1, given=And(A, B))
    assert j.status is Status.UNKNOWN


def test_zero_draws_is_unknown():
    """Asking for an estimate from zero draws is UNKNOWN."""
    assert estimate_probability(PRIOR, A, 0, 1).status is Status.UNKNOWN


def test_dead_belief_is_invalid_even_without_evidence():
    """Estimating from a belief with zero total weight is INVALID."""
    dead = condition(PRIOR, Const(False))
    assert estimate_probability(dead, A, 10, 1).status is Status.INVALID


def test_unmodelled_variables_are_unknown_with_the_probability_reason():
    """A query or evidence variable the belief does not model gives UNKNOWN with the same reason text as the exact probability."""
    j = estimate_probability(PRIOR, Var("Z"), 10, 1)
    assert j.status is Status.UNKNOWN and j.reason == "unmodelled variables: Z"
    assert estimate_probability(PRIOR, A, 10, 1, given=Var("Y")).reason == "unmodelled variables: Y"


@pytest.mark.parametrize("args,kw", [(("b", A, 5, 1), {}), ((PRIOR, "A", 5, 1), {}), ((PRIOR, A, 5, 1), {"given": "B"}), ((PRIOR, A, 5.0, 1), {}), ((PRIOR, A, 5, 1.0), {}), ((PRIOR, A, -1, 1), {})])
def test_estimate_argument_errors(args, kw):
    """Wrong argument types or a negative count are rejected."""
    with pytest.raises((TypeError, ValueError)):
        estimate_probability(*args, **kw)


# ==== Exact answer next to the sampled one, with honest Monte Carlo error ====
def test_comparison_pairs_the_exact_fraction_with_the_estimate():
    """The comparison holds the exact 5/9 next to the sampled estimate, with error and coverage computed from them."""
    c = known(compare_with_exact(PRIOR, A, 3000, 21, given=BREEZE))
    assert isinstance(c, Comparison)
    assert c.exact == Fr(5, 9)
    assert c.estimate == known(estimate_probability(PRIOR, A, 3000, 21, given=BREEZE))
    assert c.error == abs(c.estimate.p_hat - 5 / 9)
    assert c.covered == (c.estimate.low <= 5 / 9 <= c.estimate.high)


def test_exact_invalid_wins_over_sampler_unknown():
    """The exact computation PROVES the evidence impossible; the sampler can only fail to see it. The proof is what gets reported."""
    j = compare_with_exact(PRIOR, A, 500, 1, given=And(A, Not(A)))
    assert j.status is Status.INVALID and "probability zero" in j.reason


def test_unmodelled_and_dead_belief_pass_through():
    """UNKNOWN for an unmodelled variable and INVALID for a dead belief pass through the comparison unchanged."""
    assert compare_with_exact(PRIOR, Var("Z"), 10, 1).status is Status.UNKNOWN
    assert compare_with_exact(condition(PRIOR, Const(False)), A, 10, 1).status is Status.INVALID


def test_sampler_unknown_passes_through_when_exact_is_known():
    """If the exact answer exists but the sampler saw no accepted draw, the comparison reports the sampler's UNKNOWN."""
    rare = prior_belief({"A": Fr(1, 1000), "B": Fr(1, 1000)})
    j = compare_with_exact(rare, A, 10, 1, given=And(A, B))
    assert j.status is Status.UNKNOWN, "exact is KNOWN (=1) but no draw was accepted"
    assert probability(rare, A, And(A, B)).status is Status.KNOWN


def test_monte_carlo_error_is_honest_95_percent_coverage_over_many_seeds():
    """Over 200 seeds the Wilson interval contains the exact value about 95% of the time (allow 90-100%)."""
    covered = sum(known(compare_with_exact(PRIOR, A, 1500, seed, given=BREEZE)).covered for seed in range(200))
    assert 180 <= covered <= 200


def test_z_scores_are_roughly_standard_normal_not_inflated():
    """Over 200 seeds at least 90% of z-scores are below 2, the largest is below 4.5 and their root-mean-square is between 0.5 and 1.5, as for a standard normal."""
    zs = [known(compare_with_exact(PRIOR, A, 1500, seed, given=BREEZE)).z_score for seed in range(200)]
    assert sum(z < 2 for z in zs) >= 180 and max(zs) < 4.5
    assert 0.5 < math.sqrt(sum(z * z for z in zs) / len(zs)) < 1.5


def test_error_shrinks_like_one_over_root_n():
    """With 100 times more draws the average error over 60 seeds is at least 5 times smaller."""
    def mean_error(n):
        return sum(known(compare_with_exact(PRIOR, A, n, s, given=BREEZE)).error for s in range(60)) / 60

    small, large = mean_error(200), mean_error(20000)
    assert large < small / 5, "100x more draws should cut the typical error by about 10x"


def test_stderr_reported_matches_the_empirical_spread_across_seeds():
    """The reported standard error matches the actual spread of the estimate across 200 seeds to within 25%."""
    ests = [known(estimate_probability(PRIOR, A, 1500, s, given=BREEZE)) for s in range(200)]
    mean = sum(e.p_hat for e in ests) / len(ests)
    sd = math.sqrt(sum((e.p_hat - mean) ** 2 for e in ests) / (len(ests) - 1))
    reported = sum(e.stderr for e in ests) / len(ests)
    assert sd == pytest.approx(reported, rel=0.25)


def test_comparison_on_the_conditioned_belief_without_rejection_has_no_waste():
    """Sampling a belief already conditioned on the evidence needs no rejection: every draw counts as a trial."""
    c = known(compare_with_exact(POSTERIOR, A, 2000, 3))
    assert c.exact == Fr(5, 9) and c.estimate.trials == c.estimate.drawn == 2000


# ==== Forward sampling from a Bayes net ====
def test_forward_sample_shape_names_sorted_and_determinism():
    """Forward samples have sorted variable names and real booleans, repeat for the same seed, differ for another seed, and the first 10 of 30 samples equal 10 samples."""
    net = sprinkler()
    s = forward_sample(net, 30, 4)
    assert len(s) == 30
    assert all(tuple(n for n, _ in x) == tuple(sorted(SPRINKLER_NODES)) and all(type(v) is bool for _, v in x) for x in s)
    assert forward_sample(net, 30, 4) == s and forward_sample(net, 30, 5) != s
    assert forward_sample(net, 10, 4) == s[:10]
    assert forward_sample(net, 0, 4) == ()


def test_forward_sample_matches_the_documented_algorithm():
    """Forward sampling equals an independent re-implementation: topological order, one uniform draw per node, true when the draw is below the table probability."""
    net = sprinkler()
    order = topological_order(net.structure)
    rng = random.Random(77)
    expected = []
    for _ in range(25):
        val = {}
        for v in order:
            p = net.cpts[v][tuple(val[q] for q in net.structure.predecessors(v))]
            val[v] = rng.random() < float(p)
        expected.append(tuple((k, val[k]) for k in sorted(val)))
    assert forward_sample(net, 25, 77) == tuple(expected)


def test_forward_sample_respects_probability_zero_and_one():
    """A node with probability 1 is always true and a node with probability 0 is always false in 200 samples."""
    net = make_net(["X", "Y"], [("X", "Y")], {"X": {(): Fr(1)}, "Y": {(True,): Fr(0), (False,): Fr(1)}})
    for sample in forward_sample(net, 200, 0):
        assert dict(sample) == {"X": True, "Y": False}


def test_forward_sample_marginals_match_the_exact_joint():
    """In the sprinkler network, 30000 forward samples give every variable a frequency within 5 standard deviations of its exact marginal."""
    net = sprinkler()
    n = 30000
    samples = forward_sample(net, n, 12)
    exact = marginals(joint_belief(net)).value
    for name in SPRINKLER_NODES:
        p = float(exact[name])
        freq = sum(1 for s in samples if dict(s)[name]) / n
        assert abs(freq - p) < 5 * math.sqrt(p * (1 - p) / n), name


def test_forward_sample_conditional_by_rejection_approximates_explaining_away():
    """Filtering forward samples gives P(Rain | wet grass) near 0.708 and P(Rain | wet grass and sprinkler) near 0.320, so the sprinkler explains away the rain."""
    net = sprinkler()
    samples = [dict(s) for s in forward_sample(net, 40000, 31)]
    wet = [s for s in samples if s["WetGrass"]]
    rain_given_wet = sum(s["Rain"] for s in wet) / len(wet)
    wet_sprinkler = [s for s in wet if s["Sprinkler"]]
    rain_given_both = sum(s["Rain"] for s in wet_sprinkler) / len(wet_sprinkler)
    assert rain_given_wet == pytest.approx(0.708, abs=0.02) and rain_given_both == pytest.approx(0.320, abs=0.03)
    assert rain_given_both < rain_given_wet


def test_forward_sample_burglary_root_frequency():
    """The rare root event (burglary, probability 0.001) appears with frequency within 5 standard deviations of 0.001 in 50000 samples."""
    n = 50000
    s = forward_sample(burglary(), n, 1)
    f = sum(1 for x in s if dict(x)["Burglary"]) / n
    assert abs(f - 0.001) < 5 * math.sqrt(0.001 * 0.999 / n)


@pytest.mark.parametrize("args", [("net", 1, 1), (sprinkler(), 1.0, 1), (sprinkler(), -1, 1), (sprinkler(), 1, 1.0), (sprinkler(), True, 1), (sprinkler(), 1, True)])
def test_forward_sample_argument_errors(args):
    """A non-net, a float, negative or bool count and a float or bool seed are rejected."""
    with pytest.raises((TypeError, ValueError)):
        forward_sample(*args)
