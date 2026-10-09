"""Integration tests: expectations of typed Calc expressions over beliefs (dsdk.lang x dsdk.logic x dsdk.prob, with dsdk.core for belief series).

Every test runs at least two layers on REAL output of the lower one: Calc text -> dsdk.lang parse_calc, typecheck, bridge.bind_assignment and evaluate ->
exact weighted average in dsdk.prob over worlds that are dsdk.logic models. Independent expectations: hand-computed fractions (the Wumpus 10/9), the
probability function for indicator expressions, a Python re-evaluation of the same expression tree, linearity of expectation, and exact binomial intervals
for sampled indicator expressions.
"""
import json
from fractions import Fraction
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from dsdk.core import PxC, Status
from dsdk.lang import calc, parse_formula
from dsdk.lang.bridge import bind_assignment
from dsdk.logic import And, Not, Var
from dsdk.prob import (
    MeanEstimate, current_belief, exact_interval, expectation, observe_text, prior_belief, probability, sample_expectation, start_series,
)

ROOT = Path(__file__).resolve().parents[2]
KB = json.loads((ROOT / "fixtures" / "logic" / "wumpus_kb.json").read_text())
Fr = Fraction
PITS = "(if P22 then 1 else 0) + (if P31 then 1 else 0)"


def known(j):
    assert j.status is Status.KNOWN, j
    return j.value


def kb_belief(p):
    """The Wumpus knowledge base from the fixture's string premises (language package), weighted by an independent pit prior p (probability package)."""
    constraint = None
    for prem in KB["premises"]:
        f = parse_formula(prem["string"])
        constraint = f if constraint is None else And(constraint, f)
    return prior_belief({v: p for v in KB["variables"] if v.startswith("P")}, constraint)


# ==== The Wumpus numbers computed by a Calc expression ====
def test_expected_number_of_pits_among_p22_and_p31_is_ten_ninths():
    """On the Wumpus knowledge base with pit prior 1/5, the Calc expression counting pits at P22 and P31 has expectation exactly 10/9, which equals P(P22) + P(P31) = 5/9 + 5/9."""
    b = kb_belief(Fr(1, 5))
    assert known(expectation(b, PITS)) == Fr(10, 9)
    assert known(probability(b, Var("P22"))) + known(probability(b, Var("P31"))) == Fr(10, 9)


def test_the_expectation_follows_the_prior_like_the_closed_form_two_over_two_minus_p():
    """For a range of pit priors p the expected pit count at P22 and P31 is 2/(2-p), twice the closed form 1/(2-p) for each cell."""
    for p in (Fr(1, 10), Fr(1, 5), Fr(1, 2), Fr(7, 10)):
        assert known(expectation(kb_belief(p), PITS)) == 2 / (2 - p)


def test_the_expected_total_number_of_pits_over_all_five_cells_counts_the_three_safe_cells_as_zero():
    """Counting all five pit cells gives 10/9 as well, because P11, P12 and P21 are false in every model of the knowledge base."""
    all_five = " + ".join(f"(if {c} then 1 else 0)" for c in ("P11", "P12", "P21", "P22", "P31"))
    assert known(expectation(kb_belief(Fr(1, 5)), all_five)) == Fr(10, 9)


def test_conditional_expectation_with_evidence_written_as_a_formula():
    """Two independent pits with prior 1/5 and the breeze evidence "A | B" (a formula, parsed by the language package) have expected pit count 10/9 given the breeze; the unconditional expectation is 2/5."""
    b = prior_belief({"A": Fr(1, 5), "B": Fr(1, 5)})
    expr = "(if A then 1 else 0) + (if B then 1 else 0)"
    assert known(expectation(b, expr, "A | B")) == Fr(10, 9)
    assert known(expectation(b, expr)) == Fr(2, 5)


def test_expectation_at_prior_half_given_the_breeze_is_four_thirds():
    """At pit prior 1/2 the three worlds that survive the breeze are equally likely, so the expected pit count is (1 + 1 + 2)/3 = 4/3."""
    b = prior_belief({"A": Fr(1, 2), "B": Fr(1, 2)})
    assert known(expectation(b, "(if A then 1 else 0) + (if B then 1 else 0)", "A | B")) == Fr(4, 3)


def test_let_bindings_negative_literals_and_big_integers_are_exact():
    """A let-bound constant, a negative result and a ten-digit coefficient all give exact fractions: 3*P(A) - 3*(1-P(A)) and 1000000007 times the indicator."""
    b = prior_belief({"A": Fr(1, 4)})
    assert known(expectation(b, "let k = 3 in (if A then k else 0 - k)")) == Fr(3, 4) - Fr(9, 4)
    assert known(expectation(b, "1000000007 * (if A then 1 else 0)")) == Fr(1000000007, 4)


def test_a_constant_expression_has_that_constant_as_expectation_when_the_belief_is_possible():
    """The expression 2 + 3 reads no variables, so its expectation is 5 for any belief of positive weight, even one over unrelated variables."""
    assert known(expectation(prior_belief({"A": Fr(1, 3)}), "2 + 3")) == 5


# ==== Agreement with the probability layer for indicator expressions ====
def test_indicator_expressions_equal_the_marginals_for_every_variable():
    """For each variable X of a three-variable belief, the expectation of "if X then 1 else 0" equals the exact marginal probability of X."""
    b = prior_belief({"A": Fr(1, 3), "B": Fr(1, 2), "C": Fr(3, 4)}, None)
    for x in ("A", "B", "C"):
        assert known(expectation(b, f"if {x} then 1 else 0")) == known(probability(b, Var(x)))


def test_a_compound_indicator_equals_the_probability_of_the_corresponding_formula():
    """The Calc indicator "if A and not B then 1 else 0" has expectation equal to the probability of the logic formula A and not B, under a constrained belief."""
    b = prior_belief({"A": Fr(1, 3), "B": Fr(1, 2), "C": Fr(1, 5)}, parse_formula("A | C", relaxed=True))
    assert known(expectation(b, "if A and not B then 1 else 0")) == known(probability(b, And(Var("A"), Not(Var("B")))))


def test_conditional_expectation_of_an_indicator_is_the_conditional_probability():
    """The expectation of an indicator given evidence text equals probability(query, given) for the same pair."""
    b = prior_belief({"A": Fr(1, 3), "B": Fr(1, 2), "C": Fr(1, 5)})
    j = expectation(b, "if A then 1 else 0", "B | C")
    assert known(j) == known(probability(b, Var("A"), parse_formula("B | C", relaxed=True)))


# ==== Linearity of expectation across random beliefs and random expressions ====
VARS = ["A", "B", "C"]


def exprs():
    leaf = st.integers(min_value=-3, max_value=3).map(calc.IntLit) | st.builds(
        lambda v, a, b: calc.If(calc.Var(v), calc.IntLit(a), calc.IntLit(b)), st.sampled_from(VARS), st.integers(-4, 4), st.integers(-4, 4)
    )
    return st.recursive(
        leaf,
        lambda c: st.builds(lambda a, b: calc.BinOp("+", a, b), c, c)
        | st.builds(lambda a, b: calc.BinOp("-", a, b), c, c)
        | st.builds(lambda k, a: calc.BinOp("*", calc.IntLit(k), a), st.integers(-3, 3), c),
        max_leaves=5,
    )


def py_eval(e, world):
    """Independent evaluator of the generated expression subset (no dsdk.lang involved)."""
    if isinstance(e, calc.IntLit):
        return e.value
    if isinstance(e, calc.If):
        return py_eval(e.then if world[e.cond.name] else e.orelse, world)
    a, b = py_eval(e.left, world), py_eval(e.right, world)
    return {"+": a + b, "-": a - b, "*": a * b}[e.op]


probs = st.sampled_from([Fr(0), Fr(1, 10), Fr(1, 4), Fr(1, 3), Fr(1, 2), Fr(3, 4), Fr(1)])


@settings(max_examples=60, deadline=None)
@given(st.fixed_dictionaries({v: probs for v in VARS}), exprs(), exprs(), st.integers(-3, 3))
def test_linearity_of_expectation_holds_exactly_for_random_beliefs_and_expressions(priors, a, b, k):
    """For random beliefs and random Calc expressions, E[a + b] = E[a] + E[b], E[a - b] = E[a] - E[b] and E[k*a] = k*E[a] exactly, or all sides are INVALID together when the belief is dead."""
    belief = prior_belief(priors)
    sa, sb = calc.to_source(a), calc.to_source(b)
    ea, eb = expectation(belief, sa), expectation(belief, sb)
    plus, minus, scaled = expectation(belief, f"({sa}) + ({sb})"), expectation(belief, f"({sa}) - ({sb})"), expectation(belief, f"{k} * ({sa})")
    assert ea.status is eb.status is plus.status is minus.status is scaled.status
    if ea.status is Status.KNOWN:
        assert plus.value == ea.value + eb.value and minus.value == ea.value - eb.value and scaled.value == k * ea.value


@settings(max_examples=60, deadline=None)
@given(st.fixed_dictionaries({v: probs for v in VARS}), exprs())
def test_the_expectation_equals_a_python_reevaluation_of_the_same_expression_tree(priors, e):
    """The Calc pipeline (parse, type-check, bind world, evaluate) gives the same exact expectation as summing an independent Python evaluation of the expression tree over the belief's worlds."""
    belief = prior_belief(priors)
    j = expectation(belief, calc.to_source(e))
    total = belief.total
    if total == 0:
        assert j.status is Status.INVALID
        return
    expected = sum((w.weight * py_eval(e, w.assignment()) for w in belief.worlds), Fr(0)) / total
    assert known(j) == expected


@settings(max_examples=40, deadline=None)
@given(exprs(), st.fixed_dictionaries({v: st.booleans() for v in VARS}))
def test_a_well_typed_expression_never_gets_stuck_when_the_world_is_bound(e, world):
    """Type safety in action: every generated well-typed expression, with the world bound as nested lets, evaluates to an int without a StuckError, and agrees with the independent evaluator."""
    t = calc.typecheck(e, {v: calc.Type.BOOL for v in VARS})
    assert t.status is Status.KNOWN and t.value is calc.Type.INT
    assert calc.evaluate(bind_assignment(e, world)) == py_eval(e, world)


# ==== Text and meaning problems are flagged, never guessed ====
@pytest.mark.parametrize("text,offset", [("1 +", 3), ("1 + + 2", 4), ("(if A then 1 else", 17), ("A @ 1", 2), ("", 0)])
def test_unparseable_calc_text_is_invalid_and_names_the_offset(text, offset):
    """A Calc text that does not lex or parse gives INVALID whose reason starts "unparseable expression:" and ends with "(at offset N)" for the first bad position."""
    j = expectation(prior_belief({"A": Fr(1, 2)}), text)
    assert j.status is Status.INVALID and j.value is None
    assert j.reason.startswith("unparseable expression: ") and f"(at offset {offset})" in j.reason


def test_a_type_error_is_invalid_with_the_type_checkers_own_reason():
    """An ill-typed expression gives INVALID whose reason is "ill-typed expression: " followed by exactly the reason dsdk.lang.typecheck gives for the same term."""
    b = prior_belief({"A": Fr(1, 2)})
    for text in ("1 + true", "if A then 1 else true", "A + 1", "if 1 then 2 else 3"):
        expr = calc.parse_calc(text)
        checker = calc.typecheck(expr, {"A": calc.Type.BOOL} if "A" in text else {})
        j = expectation(b, text)
        assert checker.status is Status.INVALID and j.status is Status.INVALID
        assert j.reason == "ill-typed expression: " + checker.reason


def test_a_bool_expression_is_not_an_integer_expression():
    """A well-typed Bool expression such as "A and B" or "A == B" is INVALID with a reason that says it is not an integer expression and has type Bool; probability() is the tool for those."""
    b = prior_belief({"A": Fr(1, 2), "B": Fr(1, 2)})
    for text in ("A and B", "A == B", "1 < 2", "true"):
        j = expectation(b, text)
        assert j.status is Status.INVALID and j.reason.startswith("not an integer expression: ") and "has type Bool" in j.reason


def test_unmodelled_variables_are_unknown_and_checked_before_types():
    """An expression reading a variable the belief does not model is UNKNOWN with the names sorted, even if the expression would also be ill-typed."""
    b = prior_belief({"A": Fr(1, 2)})
    assert expectation(b, "if Z then 1 else 0").reason == "unmodelled variables: Z"
    j = expectation(b, "Y + Z + true")
    assert j.status is Status.UNKNOWN and j.reason == "unmodelled variables: Y, Z"


def test_parse_errors_win_over_unmodelled_variables():
    """A text that does not parse is reported as unparseable even if it mentions unknown names."""
    assert expectation(prior_belief({"A": Fr(1, 2)}), "Z +").reason.startswith("unparseable expression")


def test_dead_beliefs_and_impossible_evidence_are_invalid_not_numbers():
    """A belief of zero total weight gives INVALID "zero total weight"; evidence of probability zero gives INVALID "probability zero"; neither is reported as 0."""
    dead = prior_belief({"A": Fr(1, 2)}, parse_formula("A & ~A", relaxed=True))
    live = prior_belief({"A": Fr(1, 2)})
    assert "zero total weight" in expectation(dead, "1 + 1").reason and expectation(dead, "1 + 1").status is Status.INVALID
    j = expectation(live, "if A then 1 else 0", "A & ~A")
    assert j.status is Status.INVALID and "probability zero" in j.reason


def test_evidence_text_problems_are_labelled_like_the_ask_function():
    """Unparseable evidence is INVALID with the role "evidence text" and the offset, and evidence over an unmodelled variable is UNKNOWN."""
    b = prior_belief({"A": Fr(1, 2)})
    j = expectation(b, "if A then 1 else 0", "A &")
    assert j.status is Status.INVALID and j.reason.startswith("unparseable evidence text: ") and "(at offset 3)" in j.reason
    assert expectation(b, "1", "Z").status is Status.UNKNOWN


def test_calc_text_problems_are_reported_before_evidence_problems():
    """When both texts are bad, the Calc text is the one reported."""
    assert expectation(prior_belief({"A": Fr(1, 2)}), "1 +", "A &").reason.startswith("unparseable expression")


@pytest.mark.parametrize("args", [("belief", "1"), (None, "1")])
def test_non_belief_is_a_type_error(args):
    """A non-belief is a TypeError."""
    with pytest.raises(TypeError):
        expectation(*args)


def test_non_string_texts_are_type_errors():
    """Non-string Calc text or evidence text is a TypeError (a Python type problem, not a text problem)."""
    b = prior_belief({"A": Fr(1, 2)})
    with pytest.raises(TypeError):
        expectation(b, 5)
    with pytest.raises(TypeError):
        expectation(b, "1", 5)


# ==== Sampled estimates against the exact answer ====
def test_the_sampled_estimate_is_within_four_standard_errors_of_ten_ninths():
    """Sampling 20000 worlds of the Wumpus knowledge base and averaging the pit count gives a mean within four standard errors of the exact 10/9."""
    m = known(sample_expectation(kb_belief(Fr(1, 5)), PITS, 20000, 3))
    assert isinstance(m, MeanEstimate) and m.n == 20000 and abs(m.mean - 10 / 9) < 4 * m.stderr


def test_sampled_indicator_counts_lie_inside_the_exact_binomial_interval_of_the_exact_answer():
    """For an indicator expression the sampled success count is binomial, and over 200 seeds the exact 95% Clopper-Pearson interval around the sample proportion contains the exact expectation 5/9 in at least 185 cases."""
    b = kb_belief(Fr(1, 5))
    hits = 0
    for seed in range(200):
        m = known(sample_expectation(b, "if P22 then 1 else 0", 600, seed))
        lo, hi = exact_interval(round(m.mean * 600), 600)
        hits += lo <= 5 / 9 <= hi
    assert hits >= 185


def test_sampling_is_deterministic_and_stderr_shrinks_with_more_draws():
    """The same arguments give the same estimate bit for bit, and 100 times more draws shrink the standard error by about a factor of ten."""
    b = kb_belief(Fr(1, 5))
    assert sample_expectation(b, PITS, 500, 9) == sample_expectation(b, PITS, 500, 9)
    small, large = known(sample_expectation(b, PITS, 200, 1)), known(sample_expectation(b, PITS, 20000, 1))
    assert large.stderr < small.stderr / 5


def test_sampling_verdicts_for_zero_draws_dead_belief_and_text_problems():
    """Zero draws is UNKNOWN, a dead belief is INVALID, and text problems are reported as for the exact function; argument errors raise even for a dead belief."""
    live, dead = prior_belief({"A": Fr(1, 2)}), prior_belief({"A": Fr(1, 2)}, parse_formula("A & ~A", relaxed=True))
    assert sample_expectation(live, "1", 0, 1).status is Status.UNKNOWN
    assert sample_expectation(dead, "1", 5, 1).status is Status.INVALID
    assert sample_expectation(live, "1 +", 5, 1).reason.startswith("unparseable expression")
    assert sample_expectation(live, "Z", 5, 1).status is Status.UNKNOWN
    assert sample_expectation(live, "true", 5, 1).reason.startswith("not an integer expression")
    with pytest.raises(ValueError):
        sample_expectation(dead, "1", -1, 1)
    with pytest.raises(TypeError):
        sample_expectation(live, "1", 5, "x")


# ==== Expectations follow belief updates recorded in the kernel store ====
def test_expected_pit_count_before_and_after_observing_the_breeze_through_the_store():
    """With two pits of prior 1/5, the expected pit count is 2/5 before and 10/9 after observing the text "A | B" through the kernel store (core x lang x prob), read from the stored belief."""
    store = PxC()
    start_series(store, "s", prior_belief({"A": Fr(1, 5), "B": Fr(1, 5)}))
    expr = "(if A then 1 else 0) + (if B then 1 else 0)"
    assert known(expectation(current_belief(store, "s").value, expr)) == Fr(2, 5)
    assert observe_text(store, "s", "A | B").status is Status.KNOWN
    assert known(expectation(current_belief(store, "s").value, expr)) == Fr(10, 9)
