"""Contract tests for conditioning and exact queries: reweight, condition, probability, marginals, normalise.

The explainable core is Bayes' rule on a belief of possible worlds; the adversarial core is IMPOSSIBLE evidence, which must give a
flagged INVALID Judgment and never a made-up number (not 0, not 1, not nan).
"""
import itertools
from fractions import Fraction

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from dsdk import logic
from dsdk.core import Judgment, Status
from dsdk.logic import And, Const, Iff, Implies, Not, Or, Var
from dsdk.prob import (
    Belief, UnmodelledVariableError, WeightedWorld, condition, marginals, normalise, prior_belief, probability, reweight,
)

from prob_helpers import Fr, conj, formulas, prior_maps, ref_eval, ref_prob, ref_vars, ref_worlds, total_of

A, B, C = Var("A"), Var("B"), Var("C")
b2 = prior_belief({"A": Fr(1, 5), "B": Fr(1, 5)})


def known(j):
    assert j.status is Status.KNOWN, j
    return j.value


# ==== Exact probabilities and conditionals on worked examples ====
def test_marginal_of_independent_prior_is_the_prior():
    """Under an independent prior the probability of A is its prior 1/5, of A and B is 1/25 and of A or B is 9/25."""
    assert known(probability(b2, A)) == Fr(1, 5)
    assert known(probability(b2, And(A, B))) == Fr(1, 25)
    assert known(probability(b2, Or(A, B))) == Fr(9, 25)


def test_known_values_are_exact_fractions_including_zero_and_one():
    """Probabilities 0 and 1 are KNOWN Fraction values, not failures."""
    zero, one = probability(b2, Const(False)), probability(b2, Const(True))
    assert zero.status is Status.KNOWN and zero.value == 0 and isinstance(zero.value, Fraction)
    assert one.status is Status.KNOWN and one.value == 1


def test_conditional_probability_is_bayes_rule():
    """P(A | A or B) = P(A) / P(A or B) = (1/5) / (9/25) = 5/9 -- the Wumpus numbers in miniature."""
    assert known(probability(b2, A, Or(A, B))) == Fr(5, 9)


def test_bayes_theorem_in_both_directions():
    """P(A|B) P(B) == P(B|A) P(A) == P(A and B), for a correlated belief."""
    b = prior_belief({"A": Fr(1, 3), "B": Fr(1, 2)}, Implies(A, B))
    pa, pb = known(probability(b, A)), known(probability(b, B))
    a_given_b, b_given_a = known(probability(b, A, B)), known(probability(b, B, A))
    assert a_given_b * pb == b_given_a * pa == known(probability(b, And(A, B)))


def test_law_of_total_probability():
    """P(q) equals P(q|B)P(B) + P(q|not B)P(not B) for a correlated belief."""
    b = prior_belief({"A": Fr(1, 3), "B": Fr(1, 4), "C": Fr(2, 3)}, Implies(A, Or(B, C)))
    q = Or(A, C)
    split = known(probability(b, q, B)) * known(probability(b, B)) + known(probability(b, q, Not(B))) * known(probability(b, Not(B)))
    assert split == known(probability(b, q))


def test_certain_evidence_changes_nothing_and_given_equal_to_query_is_one():
    """Conditioning on a true constant changes nothing, P(A|A) is 1 and P(not A|A) is 0."""
    b = prior_belief({"A": Fr(1, 3), "B": Fr(1, 2)})
    assert known(probability(b, A, Const(True))) == known(probability(b, A))
    assert known(probability(b, A, A)) == 1
    assert known(probability(b, Not(A), A)) == 0


def test_entailment_means_conditional_probability_one_when_evidence_is_possible():
    """If the evidence entails q (logic.entails) and the evidence is possible, P(q | evidence) is exactly 1."""
    b = prior_belief({"A": Fr(1, 3), "B": Fr(1, 2)})
    evidence = And(A, B)
    assert logic.entails([evidence], Or(A, Var("B")))
    assert known(probability(b, Or(A, B), evidence)) == 1


# ==== Impossible evidence is INVALID and unmodelled variables are UNKNOWN ====
IMPOSSIBLE = [And(A, Not(A)), Const(False), And(B, Not(B))]


@pytest.mark.parametrize("evidence", IMPOSSIBLE)
def test_impossible_evidence_is_invalid_never_a_number(evidence):
    """P(q | contradiction) is undefined. logic.entails([contradiction], anything) is vacuously TRUE, but the probability must
    NOT be reported as 1 ('fabricated certainty') -- nor as 0."""
    b = prior_belief({"A": Fr(1, 5), "B": Fr(1, 5)})
    assert logic.entails([evidence], A) and logic.entails([evidence], Not(A)), "premise: the logic is vacuous here"
    for q in (A, Not(A), Const(True), Const(False)):
        j = probability(b, q, evidence)
        assert j.status is Status.INVALID and j.value is None
        assert j.reason.strip() and "probability zero" in j.reason


def test_evidence_that_the_prior_makes_impossible_is_invalid():
    """Evidence logically possible but with prior probability 0 (A has prior 0): still INVALID, not 'KNOWN 0'."""
    b = prior_belief({"A": 0, "B": Fr(1, 2)})
    assert logic.is_satisfiable(A)
    j = probability(b, B, A)
    assert j.status is Status.INVALID


def test_zero_total_belief_makes_every_unconditional_question_invalid():
    """A belief with zero total weight (contradictory constraint, or evidence of zero probability) answers INVALID with reason mentioning zero total weight."""
    empty = prior_belief({"A": Fr(1, 2)}, And(A, Not(A)))
    assert empty.total == 0
    j = probability(empty, A)
    assert j.status is Status.INVALID and "zero total weight" in j.reason
    assert probability(empty, A, Const(True)).status is Status.INVALID
    nowhere = prior_belief({"A": 0})
    assert probability(condition(nowhere, A), A).status is Status.INVALID


def test_conditioning_then_asking_on_impossible_evidence_is_invalid():
    """After conditioning on a contradiction every question, the marginals and the normalisation are INVALID."""
    dead = condition(b2, And(A, Not(A)))
    assert dead.total == 0
    assert probability(dead, A).status is Status.INVALID
    assert marginals(dead).status is Status.INVALID
    assert normalise(dead).status is Status.INVALID


def test_unmodelled_variable_is_unknown_not_invalid_not_zero():
    """A query over variables the belief does not model is UNKNOWN with the reason listing them sorted, in both the query and the evidence position."""
    j = probability(b2, And(Var("Z"), Var("Y")))
    assert j.status is Status.UNKNOWN and j.value is None
    assert "unmodelled variables: Y, Z" == j.reason
    j2 = probability(b2, A, Var("W"))
    assert j2.status is Status.UNKNOWN and "W" in j2.reason


def test_unmodelled_check_comes_before_the_zero_denominator_check():
    """The unmodelled-variable check runs before the zero-weight check, so a dead belief asked about an unknown variable is UNKNOWN."""
    empty = prior_belief({"A": Fr(1, 2)}, And(A, Not(A)))
    assert probability(empty, Var("Z")).status is Status.UNKNOWN


@pytest.mark.parametrize("args", [("A",), (b2, "A"), (b2, A, "B"), (None, A), (b2, 1)])
def test_probability_argument_types(args):
    """A non-belief, a non-formula query, a non-formula evidence or a number in place of a belief are a TypeError."""
    with pytest.raises(TypeError):
        probability(*args)


def test_probability_never_mutates_or_depends_on_call_order():
    """Asking the same question twice gives equal answers and leaves the belief unchanged."""
    before = b2
    first = probability(b2, A, Or(A, B))
    again = probability(b2, A, Or(A, B))
    assert first == again and b2 == before


# ==== Reweighting and conditioning a belief ====
def test_reweight_calls_likelihood_once_per_world_in_order_with_fresh_dicts():
    """Reweighting calls the likelihood once per world in world order with a fresh dict each time, multiplies each weight by it, and a function that tampers with its argument cannot alter the belief."""
    seen = []

    def lik(a):
        seen.append(dict(a))
        a["A"] = "tampered"  # must not leak into the belief
        return Fr(1, 2)

    out = reweight(b2, lik)
    assert seen == [w.assignment() for w in b2.worlds]
    assert [w.weight for w in out.worlds] == [w.weight / 2 for w in b2.worlds]
    assert [w.values for w in out.worlds] == [w.values for w in b2.worlds], "worlds themselves are untouched"
    assert out.variables == b2.variables


def test_reweight_accepts_ints_floats_fractions_and_keeps_zero_weight_worlds():
    """Likelihoods may be ints, floats or Fractions, and worlds whose weight becomes 0 stay in the belief."""
    out = reweight(b2, lambda a: 0 if a["A"] else 0.5)
    assert len(out.worlds) == len(b2.worlds)
    assert [w.weight for w in out.worlds] == [Fr(16, 25) / 2, Fr(4, 25) / 2, 0, 0]


@pytest.mark.parametrize("bad,exc", [(-1, ValueError), (float("nan"), ValueError), ("x", TypeError), (None, TypeError), (True, TypeError)])
def test_reweight_rejects_bad_likelihood_values(bad, exc):
    """A likelihood that returns a negative, nan, string, None or bool is rejected."""
    with pytest.raises(exc):
        reweight(b2, lambda a: bad)


def test_reweight_argument_types_and_input_not_changed():
    """A non-belief or non-callable is a TypeError, and the input belief is unchanged afterwards."""
    with pytest.raises(TypeError):
        reweight("belief", lambda a: 1)
    with pytest.raises(TypeError):
        reweight(b2, 1)
    snapshot = [(w.values, w.weight) for w in b2.worlds]
    reweight(b2, lambda a: 3)
    assert [(w.values, w.weight) for w in b2.worlds] == snapshot


def test_condition_keeps_only_matching_worlds_and_total_becomes_the_evidence_mass():
    """Conditioning on A-or-B keeps the three matching worlds with their weights 4/25, 4/25 and 1/25, keeps the excluded world with weight 0, and makes the total 9/25."""
    c = condition(b2, Or(A, B))
    assert [(w.values, w.weight) for w in c.worlds if w.weight] == [((("A", False), ("B", True)), Fr(4, 25)), ((("A", True), ("B", False)), Fr(4, 25)), ((("A", True), ("B", True)), Fr(1, 25))]
    assert len(c.worlds) == 4, "the excluded world stays, with weight 0"
    assert c.total == Fr(9, 25) == b2.mass(Or(A, B))


def test_condition_is_idempotent_commutative_and_equals_conditioning_on_the_conjunction():
    """Conditioning twice on the same evidence changes nothing more, the order of two pieces of evidence does not matter, and both equal conditioning once on their conjunction."""
    e1, e2 = Or(A, B), Not(And(A, B))
    once = condition(b2, e1)
    assert condition(once, e1) == once
    ab = condition(condition(b2, e1), e2)
    ba = condition(condition(b2, e2), e1)
    both = condition(b2, And(e1, e2))
    assert ab == ba == both


def test_condition_on_true_is_identity_and_on_false_zeroes_everything():
    """Conditioning on true returns the same belief, and on false gives total 0 while keeping every world."""
    assert condition(b2, Const(True)) == b2
    dead = condition(b2, Const(False))
    assert dead.total == 0 and all(w.weight == 0 for w in dead.worlds) and len(dead.worlds) == len(b2.worlds)


def test_condition_does_not_normalise():
    """Unnormalised on purpose: a second condition multiplies the masses, and total is P(evidence)."""
    c = condition(condition(b2, Or(A, B)), A)
    assert c.total == Fr(1, 5)  # P(A and (A or B)) = P(A)


def test_condition_errors():
    """Conditioning on an unmodelled variable raises an error naming it, and wrong argument types are a TypeError."""
    with pytest.raises(UnmodelledVariableError) as info:
        condition(b2, Var("Z"))
    assert info.value.names == ("Z",)
    with pytest.raises(TypeError):
        condition(b2, "A")
    with pytest.raises(TypeError):
        condition("belief", A)


def test_condition_on_impossible_evidence_returns_a_dead_belief_not_an_exception():
    """Conditioning on a contradiction returns a belief with total 0 instead of raising."""
    dead = condition(b2, And(A, Not(A)))
    assert isinstance(dead, Belief) and dead.total == 0


# ==== Marginals and normalisation ====
def test_marginals_table_and_order():
    """After conditioning on a breeze the marginals are returned in variable order with both pit probabilities equal to 5/9."""
    j = marginals(condition(b2, Or(A, B)))
    assert j.status is Status.KNOWN
    assert list(j.value) == ["A", "B"]
    assert j.value == {"A": Fr(5, 9), "B": Fr(5, 9)}


def test_marginals_of_belief_over_no_variables():
    """A belief over no variables has an empty marginal table."""
    assert known(marginals(prior_belief({}))) == {}


def test_marginals_rejects_non_belief():
    """Marginals of something that is not a belief is a TypeError."""
    with pytest.raises(TypeError):
        marginals([1])


def test_normalise_sums_to_one_keeps_order_and_ratios():
    """Normalising the breeze posterior gives weights 0, 4/9, 4/9, 1/9 summing to 1 in the same world order, and normalising again changes nothing."""
    c = condition(b2, Or(A, B))
    n = known(normalise(c))
    assert n.total == 1
    assert [w.values for w in n.worlds] == [w.values for w in c.worlds]
    assert [w.weight for w in n.worlds] == [Fr(0), Fr(4, 9), Fr(4, 9), Fr(1, 9)]
    assert known(normalise(n)) == n, "idempotent"


def test_normalise_invalid_for_zero_total_and_rejects_non_belief():
    """Normalising a zero-weight belief is INVALID, and a non-belief is a TypeError."""
    j = normalise(condition(b2, Const(False)))
    assert j.status is Status.INVALID and "zero total weight" in j.reason
    with pytest.raises(TypeError):
        normalise(3)


# ==== Properties checked against an independent brute-force oracle ====
@settings(max_examples=60)
@given(prior_maps(), formulas(), formulas(), formulas())
def test_probability_matches_the_brute_force_oracle(priors, constraint, query, given_):
    """For random priors, constraints, queries and evidence, probability equals the independent itertools computation exactly, and is INVALID exactly when that computation has a zero denominator."""
    vs = ref_vars(constraint) | ref_vars(query) | ref_vars(given_)
    full = dict(priors)
    for v in vs - set(full):
        full[v] = Fr(1, 2)
    b = prior_belief(full, constraint)
    got = probability(b, query, given_)
    expected = ref_prob(full, query, given_, constraint)
    if expected is None:
        assert got.status is Status.INVALID
    else:
        assert got.status is Status.KNOWN and got.value == expected
        assert 0 <= got.value <= 1


@settings(max_examples=60)
@given(prior_maps(), formulas(), formulas())
def test_condition_then_probability_equals_given_form(priors, e, q):
    """Asking P(q | e) directly gives the same answer as conditioning on e and then asking P(q)."""
    full = dict(priors)
    for v in (ref_vars(e) | ref_vars(q)) - set(full):
        full[v] = Fr(1, 3)
    b = prior_belief(full)
    direct = probability(b, q, e)
    via = probability(condition(b, e), q)
    assert direct.status == via.status
    if direct.status is Status.KNOWN:
        assert direct.value == via.value


@settings(max_examples=40)
@given(prior_maps(), formulas())
def test_complement_rule_and_additivity(priors, q):
    """For random queries P(q) + P(not q) equals exactly 1."""
    full = dict(priors)
    for v in ref_vars(q) - set(full):
        full[v] = Fr(1, 2)
    b = prior_belief(full)
    p, np_ = known(probability(b, q)), known(probability(b, Not(q)))
    assert p + np_ == 1


@settings(max_examples=40)
@given(prior_maps())
def test_normalised_weights_equal_the_posterior_of_each_world(priors):
    """After conditioning on 'some variable is true', each normalised world weight is that world's conditional probability."""
    names = sorted(priors)
    some = Var(names[0])
    for n in names[1:]:
        some = Or(some, Var(n))
    b = condition(prior_belief(priors), some)
    if b.total == 0:
        return
    n = known(normalise(b))
    for w in n.worlds:
        this_world = conj(*[Var(k) if v else Not(Var(k)) for k, v in w.values])
        assert w.weight == known(probability(prior_belief(priors), this_world, some))
