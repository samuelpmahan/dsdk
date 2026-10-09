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


# ------------------------------------------------------------------ sample_worlds
def test_sample_worlds_shape_and_determinism():
    s = known(sample_worlds(PRIOR, 25, 4))
    assert isinstance(s, tuple) and len(s) == 25
    assert all(item in {w.values for w in PRIOR.worlds} for item in s)
    assert known(sample_worlds(PRIOR, 25, 4)) == s
    assert known(sample_worlds(PRIOR, 25, 5)) != s


def test_sample_worlds_matches_the_shared_draw_primitive():
    draws = inverse_cdf_draws([w.weight for w in PRIOR.worlds], 40, 99)
    assert known(sample_worlds(PRIOR, 40, 99)) == tuple(PRIOR.worlds[i].values for i in draws)


def test_sample_worlds_never_returns_zero_weight_worlds():
    s = known(sample_worlds(POSTERIOR, 3000, 8))
    assert (("A", False), ("B", False)) not in s, "the 'Neither' world is impossible given the breeze"
    assert set(s) == {w.values for w in POSTERIOR.worlds if w.weight > 0}


def test_sample_frequencies_match_the_exact_posterior():
    n = 30000
    s = known(sample_worlds(POSTERIOR, n, 2))
    for values, p in [((("A", True), ("B", False)), 4 / 9), ((("A", False), ("B", True)), 4 / 9), ((("A", True), ("B", True)), 1 / 9)]:
        assert abs(s.count(values) / n - p) < 5 * math.sqrt(p * (1 - p) / n)


def test_sample_zero_draws_is_known_empty():
    assert sample_worlds(PRIOR, 0, 1) == Judgment(Status.KNOWN, (), "")


def test_sample_from_a_dead_belief_is_invalid():
    dead = condition(PRIOR, And(A, Not(A)))
    j = sample_worlds(dead, 5, 0)
    assert j.status is Status.INVALID and "zero total weight" in j.reason


@pytest.mark.parametrize("args", [("b", 3, 0), (PRIOR, 3.0, 0), (PRIOR, -1, 0), (PRIOR, True, 0), (PRIOR, 3, 1.5), (PRIOR, 3, True), (PRIOR, 3, "0")])
def test_sample_worlds_argument_errors(args):
    with pytest.raises((TypeError, ValueError)):
        sample_worlds(*args)


def test_argument_errors_win_over_invalid_belief():
    dead = condition(PRIOR, Const(False))
    with pytest.raises(ValueError):
        sample_worlds(dead, -1, 0)
    with pytest.raises(TypeError):
        sample_worlds(dead, 1, "x")


# ------------------------------------------------------------------ estimate_probability
def test_unconditional_estimate_counts_hits_among_the_draws():
    j = estimate_probability(PRIOR, A, 1000, 3)
    e = known(j)
    assert isinstance(e, Estimate)
    samples = known(sample_worlds(PRIOR, 1000, 3))
    hits = sum(1 for v in samples if dict(v)["A"])
    assert (e.successes, e.trials, e.drawn) == (hits, 1000, 1000)
    assert e == make_estimate(hits, 1000, 1000)


def test_conditional_estimate_is_rejection_sampling_from_the_prior():
    e = known(estimate_probability(PRIOR, A, 4000, 6, given=BREEZE))
    samples = known(sample_worlds(PRIOR, 4000, 6))
    kept = [dict(v) for v in samples if evaluate(BREEZE, dict(v))]
    assert e.drawn == 4000 and e.trials == len(kept) < 4000
    assert e.successes == sum(1 for a in kept if a["A"])
    assert e.trials == pytest.approx(4000 * 9 / 25, rel=0.1), "about 36% of prior draws contain a pit"


def test_conditional_estimate_covers_the_wumpus_posterior_5_9():
    e = known(estimate_probability(PRIOR, A, 20000, 10, given=BREEZE))
    assert abs(e.p_hat - 5 / 9) < 4 * e.stderr
    assert e.low <= 5 / 9 <= e.high


def test_estimate_of_a_certain_event_has_zero_stderr_but_a_nondegenerate_interval():
    e = known(estimate_probability(PRIOR, Const(True), 50, 1))
    assert e.p_hat == 1.0 and e.stderr == 0.0 and e.low < 1.0 and e.high == 1.0


def test_impossible_evidence_is_unknown_for_the_sampler_not_invalid_and_not_a_number():
    for evidence in (And(A, Not(A)), Const(False)):
        j = estimate_probability(PRIOR, A, 500, 1, given=evidence)
        assert j.status is Status.UNKNOWN and j.value is None
        assert "impossible" in j.reason and "rare" in j.reason


def test_rare_evidence_is_also_unknown_with_too_few_draws():
    rare = prior_belief({"A": Fr(1, 1000), "B": Fr(1, 1000)})
    j = estimate_probability(rare, A, 20, 1, given=And(A, B))
    assert j.status is Status.UNKNOWN


def test_zero_draws_is_unknown():
    assert estimate_probability(PRIOR, A, 0, 1).status is Status.UNKNOWN


def test_dead_belief_is_invalid_even_without_evidence():
    dead = condition(PRIOR, Const(False))
    assert estimate_probability(dead, A, 10, 1).status is Status.INVALID


def test_unmodelled_variables_are_unknown_with_the_probability_reason():
    j = estimate_probability(PRIOR, Var("Z"), 10, 1)
    assert j.status is Status.UNKNOWN and j.reason == "unmodelled variables: Z"
    assert estimate_probability(PRIOR, A, 10, 1, given=Var("Y")).reason == "unmodelled variables: Y"


@pytest.mark.parametrize("args,kw", [(("b", A, 5, 1), {}), ((PRIOR, "A", 5, 1), {}), ((PRIOR, A, 5, 1), {"given": "B"}), ((PRIOR, A, 5.0, 1), {}), ((PRIOR, A, 5, 1.0), {}), ((PRIOR, A, -1, 1), {})])
def test_estimate_argument_errors(args, kw):
    with pytest.raises((TypeError, ValueError)):
        estimate_probability(*args, **kw)


# ------------------------------------------------------------------ compare_with_exact
def test_comparison_pairs_the_exact_fraction_with_the_estimate():
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
    assert compare_with_exact(PRIOR, Var("Z"), 10, 1).status is Status.UNKNOWN
    assert compare_with_exact(condition(PRIOR, Const(False)), A, 10, 1).status is Status.INVALID


def test_sampler_unknown_passes_through_when_exact_is_known():
    rare = prior_belief({"A": Fr(1, 1000), "B": Fr(1, 1000)})
    j = compare_with_exact(rare, A, 10, 1, given=And(A, B))
    assert j.status is Status.UNKNOWN, "exact is KNOWN (=1) but no draw was accepted"
    assert probability(rare, A, And(A, B)).status is Status.KNOWN


def test_monte_carlo_error_is_honest_95_percent_coverage_over_many_seeds():
    """Over 200 seeds the Wilson interval contains the exact value about 95% of the time (allow 90-100%)."""
    covered = sum(known(compare_with_exact(PRIOR, A, 1500, seed, given=BREEZE)).covered for seed in range(200))
    assert 180 <= covered <= 200


def test_z_scores_are_roughly_standard_normal_not_inflated():
    zs = [known(compare_with_exact(PRIOR, A, 1500, seed, given=BREEZE)).z_score for seed in range(200)]
    assert sum(z < 2 for z in zs) >= 180 and max(zs) < 4.5
    assert 0.5 < math.sqrt(sum(z * z for z in zs) / len(zs)) < 1.5


def test_error_shrinks_like_one_over_root_n():
    def mean_error(n):
        return sum(known(compare_with_exact(PRIOR, A, n, s, given=BREEZE)).error for s in range(60)) / 60

    small, large = mean_error(200), mean_error(20000)
    assert large < small / 5, "100x more draws should cut the typical error by about 10x"


def test_stderr_reported_matches_the_empirical_spread_across_seeds():
    ests = [known(estimate_probability(PRIOR, A, 1500, s, given=BREEZE)) for s in range(200)]
    mean = sum(e.p_hat for e in ests) / len(ests)
    sd = math.sqrt(sum((e.p_hat - mean) ** 2 for e in ests) / (len(ests) - 1))
    reported = sum(e.stderr for e in ests) / len(ests)
    assert sd == pytest.approx(reported, rel=0.25)


def test_comparison_on_the_conditioned_belief_without_rejection_has_no_waste():
    c = known(compare_with_exact(POSTERIOR, A, 2000, 3))
    assert c.exact == Fr(5, 9) and c.estimate.trials == c.estimate.drawn == 2000


# ------------------------------------------------------------------ forward_sample
def test_forward_sample_shape_names_sorted_and_determinism():
    net = sprinkler()
    s = forward_sample(net, 30, 4)
    assert len(s) == 30
    assert all(tuple(n for n, _ in x) == tuple(sorted(SPRINKLER_NODES)) and all(type(v) is bool for _, v in x) for x in s)
    assert forward_sample(net, 30, 4) == s and forward_sample(net, 30, 5) != s
    assert forward_sample(net, 10, 4) == s[:10]
    assert forward_sample(net, 0, 4) == ()


def test_forward_sample_matches_the_documented_algorithm():
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
    net = make_net(["X", "Y"], [("X", "Y")], {"X": {(): Fr(1)}, "Y": {(True,): Fr(0), (False,): Fr(1)}})
    for sample in forward_sample(net, 200, 0):
        assert dict(sample) == {"X": True, "Y": False}


def test_forward_sample_marginals_match_the_exact_joint():
    net = sprinkler()
    n = 30000
    samples = forward_sample(net, n, 12)
    exact = marginals(joint_belief(net)).value
    for name in SPRINKLER_NODES:
        p = float(exact[name])
        freq = sum(1 for s in samples if dict(s)[name]) / n
        assert abs(freq - p) < 5 * math.sqrt(p * (1 - p) / n), name


def test_forward_sample_conditional_by_rejection_approximates_explaining_away():
    net = sprinkler()
    samples = [dict(s) for s in forward_sample(net, 40000, 31)]
    wet = [s for s in samples if s["WetGrass"]]
    rain_given_wet = sum(s["Rain"] for s in wet) / len(wet)
    wet_sprinkler = [s for s in wet if s["Sprinkler"]]
    rain_given_both = sum(s["Rain"] for s in wet_sprinkler) / len(wet_sprinkler)
    assert rain_given_wet == pytest.approx(0.708, abs=0.02) and rain_given_both == pytest.approx(0.320, abs=0.03)
    assert rain_given_both < rain_given_wet


def test_forward_sample_burglary_root_frequency():
    n = 50000
    s = forward_sample(burglary(), n, 1)
    f = sum(1 for x in s if dict(x)["Burglary"]) / n
    assert abs(f - 0.001) < 5 * math.sqrt(0.001 * 0.999 / n)


@pytest.mark.parametrize("args", [("net", 1, 1), (sprinkler(), 1.0, 1), (sprinkler(), -1, 1), (sprinkler(), 1, 1.0), (sprinkler(), True, 1), (sprinkler(), 1, True)])
def test_forward_sample_argument_errors(args):
    with pytest.raises((TypeError, ValueError)):
        forward_sample(*args)
