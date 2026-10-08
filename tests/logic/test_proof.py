"""Contract tests for dsdk.logic.proof: the explicit inference checker (valid chains, rejected fallacies, citation rules)."""
import pytest
from hypothesis import given, strategies as st

from dsdk.logic import And, CheckResult, Const, Iff, Implies, Not, Or, Rule, Step, Var, check

from helpers import formulas, ref_countermodel

P, Q, R = "p", "q", "r"


def v(n):
    return Var(n)


def S(f, rule, *cites):
    return Step(f, rule, tuple(cites))


def assert_ok(result, ctx=""):
    assert isinstance(result, CheckResult)
    assert result.ok is True and result.bad_step is None and result.reason == "", f"{ctx}: expected a valid proof, got {result}"


def assert_bad(result, index, ctx=""):
    assert isinstance(result, CheckResult)
    assert result.ok is False, f"{ctx}: proof should have been rejected"
    assert result.bad_step == index, f"{ctx}: first invalid step is {index}, checker said {result.bad_step} ({result.reason})"
    assert result.reason.strip(), f"{ctx}: a human-readable reason is required"


# =========================== Step construction ==============================
def test_step_default_cites_is_empty_tuple():
    """A premise step needs no cites argument."""
    assert Step(v(P), Rule.PREMISE).cites == ()


@pytest.mark.parametrize(
    "build",
    [
        lambda: Step("p", Rule.PREMISE),  # formula must be a Formula
        lambda: Step(Var("p"), "premise"),  # rule must be a Rule member
        lambda: Step(Var("p"), Rule.PREMISE, [0]),  # cites must be a tuple
        lambda: Step(Var("p"), Rule.MODUS_PONENS, (0, "1")),  # cites must be ints
        lambda: Step(Var("p"), Rule.MODUS_PONENS, (True,)),  # bool is not an index
    ],
)
def test_step_rejects_malformed_fields(build):
    """Malformed steps are TypeErrors at construction, so check() only sees well-typed data."""
    with pytest.raises(TypeError):
        build()


def test_rule_values_are_the_documented_names():
    """Reasons and serialisation use the snake_case rule names."""
    assert {r.value for r in Rule} == {
        "premise", "modus_ponens", "modus_tollens", "and_intro", "and_elim_left",
        "and_elim_right", "or_intro_left", "or_intro_right", "double_negation_elim"}


# =========================== valid proofs ===================================
def test_empty_proof_is_valid():
    """Degenerate: no steps -> nothing unjustified (also with no premises)."""
    assert_ok(check([], []), "empty proof")
    assert_ok(check([], [v(P)]), "empty proof, some premises")


def test_premises_only_and_repeated_premise():
    """A premise may be restated, and premises may be listed in any order."""
    p, q = v(P), v(Q)
    assert_ok(check([S(q, Rule.PREMISE), S(p, Rule.PREMISE), S(q, Rule.PREMISE)], [p, q]))


def test_premise_match_is_structural_not_identity():
    """A separately built but equal formula counts as the premise; premises may come from a generator."""
    assert_ok(check([S(And(v(P), v(Q)), Rule.PREMISE)], (f for f in [And(v(P), v(Q))])))


def test_modus_ponens_valid():
    """From p->q and p, conclude q; cites are (implication, antecedent)."""
    p, q = v(P), v(Q)
    proof = [S(Implies(p, q), Rule.PREMISE), S(p, Rule.PREMISE), S(q, Rule.MODUS_PONENS, 0, 1)]
    assert_ok(check(proof, [Implies(p, q), p]))


def test_modus_tollens_valid():
    """From p->q and ~q, conclude ~p; cites are (implication, negated consequent)."""
    p, q = v(P), v(Q)
    proof = [S(Implies(p, q), Rule.PREMISE), S(Not(q), Rule.PREMISE), S(Not(p), Rule.MODUS_TOLLENS, 0, 1)]
    assert_ok(check(proof, [Implies(p, q), Not(q)]))


def test_and_rules_valid_including_same_cite_twice():
    """and_intro builds And(f[i], f[j]) (i==j allowed); the eliminations pick the left/right conjunct."""
    p, q = v(P), v(Q)
    proof = [
        S(And(p, q), Rule.PREMISE),
        S(p, Rule.AND_ELIM_LEFT, 0),
        S(q, Rule.AND_ELIM_RIGHT, 0),
        S(And(q, p), Rule.AND_INTRO, 2, 1),
        S(And(p, p), Rule.AND_INTRO, 1, 1),
    ]
    assert_ok(check(proof, [And(p, q)]))


def test_or_introduction_with_arbitrary_other_disjunct():
    """or_intro_left/right allow ANY formula as the new disjunct (even an unrelated or constant one)."""
    p = v(P)
    junk = Iff(Const(False), v("zzz"))
    proof = [S(p, Rule.PREMISE), S(Or(p, junk), Rule.OR_INTRO_LEFT, 0), S(Or(junk, p), Rule.OR_INTRO_RIGHT, 0)]
    assert_ok(check(proof, [p]))


def test_double_negation_elimination_valid_and_odd_depth():
    """~~p |- p; and ~~~p |- ~p (strip exactly two negations)."""
    p = v(P)
    assert_ok(check([S(Not(Not(p)), Rule.PREMISE), S(p, Rule.DOUBLE_NEGATION_ELIM, 0)], [Not(Not(p))]))
    nnn = Not(Not(Not(p)))
    assert_ok(check([S(nnn, Rule.PREMISE), S(Not(p), Rule.DOUBLE_NEGATION_ELIM, 0)], [nnn]))


def test_longer_mixed_proof():
    """A six-step derivation mixing rules (and_elim -> modus_ponens -> and_intro)."""
    p, q, r = v(P), v(Q), v(R)
    prem = [And(p, q), Implies(p, r)]
    proof = [
        S(prem[0], Rule.PREMISE), S(prem[1], Rule.PREMISE),
        S(p, Rule.AND_ELIM_LEFT, 0), S(r, Rule.MODUS_PONENS, 1, 2),
        S(q, Rule.AND_ELIM_RIGHT, 0), S(And(r, q), Rule.AND_INTRO, 3, 4),
    ]
    assert_ok(check(proof, prem))


# =========================== the fallacies (must be rejected) ===============
def test_affirming_the_consequent_is_rejected():
    """From p->q and q, concluding p is a fallacy; no cite order makes modus_ponens accept it."""
    p, q = v(P), v(Q)
    prem = [Implies(p, q), q]
    base = [S(prem[0], Rule.PREMISE), S(prem[1], Rule.PREMISE)]
    for cites in [(0, 1), (1, 0)]:
        res = check(base + [S(p, Rule.MODUS_PONENS, *cites)], prem)
        assert_bad(res, 2, f"affirming the consequent via cites {cites}")
        assert "modus_ponens" in res.reason


def test_denying_the_antecedent_is_rejected():
    """From p->q and ~p, concluding ~q is a fallacy; modus_tollens must not accept it."""
    p, q = v(P), v(Q)
    prem = [Implies(p, q), Not(p)]
    proof = [S(prem[0], Rule.PREMISE), S(prem[1], Rule.PREMISE), S(Not(q), Rule.MODUS_TOLLENS, 0, 1)]
    assert_bad(check(proof, prem), 2, "denying the antecedent")


def test_modus_ponens_cite_order_matters():
    """The contract is (implication first, antecedent second); (antecedent, implication) is rejected."""
    p, q = v(P), v(Q)
    prem = [Implies(p, q), p]
    base = [S(prem[0], Rule.PREMISE), S(prem[1], Rule.PREMISE)]
    assert_ok(check(base + [S(q, Rule.MODUS_PONENS, 0, 1)], prem))
    assert_bad(check(base + [S(q, Rule.MODUS_PONENS, 1, 0)], prem), 2, "swapped cites")


def test_modus_ponens_wrong_conclusion_or_wrong_antecedent():
    """MP must produce exactly the consequent, from exactly the antecedent."""
    p, q, r = v(P), v(Q), v(R)
    prem = [Implies(p, q), p, r]
    base = [S(prem[0], Rule.PREMISE), S(prem[1], Rule.PREMISE), S(r, Rule.PREMISE)]
    assert_bad(check(base + [S(r, Rule.MODUS_PONENS, 0, 1)], prem), 3, "wrong conclusion")
    assert_bad(check(base + [S(q, Rule.MODUS_PONENS, 0, 2)], prem), 3, "antecedent r does not match p")


def test_and_intro_order_matters():
    """And(f[i], f[j]) is ordered: citing (p, q) cannot justify And(q, p)."""
    p, q = v(P), v(Q)
    base = [S(p, Rule.PREMISE), S(q, Rule.PREMISE)]
    assert_ok(check(base + [S(And(p, q), Rule.AND_INTRO, 0, 1)], [p, q]))
    assert_bad(check(base + [S(And(q, p), Rule.AND_INTRO, 0, 1)], [p, q]), 2, "swapped conjuncts")


@pytest.mark.parametrize(
    "build_conclusion, rule",
    [
        (lambda p, q: q, Rule.AND_ELIM_LEFT),  # left elim must give left
        (lambda p, q: p, Rule.AND_ELIM_RIGHT),  # right elim must give right
    ],
)
def test_and_elimination_picks_the_right_side(build_conclusion, rule):
    """and_elim_left/right are not interchangeable."""
    p, q = v(P), v(Q)
    proof = [S(And(p, q), Rule.PREMISE), S(build_conclusion(p, q), rule, 0)]
    assert_bad(check(proof, [And(p, q)]), 1)


def test_and_elimination_on_non_conjunction_rejected():
    """Eliminating from an Or (or a bare variable) is invalid."""
    p, q = v(P), v(Q)
    assert_bad(check([S(Or(p, q), Rule.PREMISE), S(p, Rule.AND_ELIM_LEFT, 0)], [Or(p, q)]), 1)
    assert_bad(check([S(p, Rule.PREMISE), S(p, Rule.AND_ELIM_LEFT, 0)], [p]), 1)


def test_or_intro_must_keep_the_cited_formula_on_the_correct_side():
    """or_intro_left needs Or(f[i], X); putting f[i] on the right is or_intro_right, and vice versa."""
    p, q = v(P), v(Q)
    base = [S(p, Rule.PREMISE)]
    assert_bad(check(base + [S(Or(q, p), Rule.OR_INTRO_LEFT, 0)], [p]), 1)
    assert_bad(check(base + [S(Or(p, q), Rule.OR_INTRO_RIGHT, 0)], [p]), 1)
    assert_bad(check(base + [S(Or(q, q), Rule.OR_INTRO_LEFT, 0)], [p]), 1, "neither side is the cited formula")
    assert_bad(check(base + [S(And(p, q), Rule.OR_INTRO_LEFT, 0)], [p]), 1, "not even an Or")


def test_double_negation_elim_needs_two_negations():
    """~p |- p is classical-looking nonsense: a single negation must be rejected."""
    p = v(P)
    assert_bad(check([S(Not(p), Rule.PREMISE), S(p, Rule.DOUBLE_NEGATION_ELIM, 0)], [Not(p)]), 1)


def test_modus_tollens_needs_negated_consequent():
    """MT with a cited step that is not ~q is rejected."""
    p, q = v(P), v(Q)
    prem = [Implies(p, q), q]
    proof = [S(prem[0], Rule.PREMISE), S(q, Rule.PREMISE), S(Not(p), Rule.MODUS_TOLLENS, 0, 1)]
    assert_bad(check(proof, prem), 2)


# =========================== premises =======================================
def test_premise_step_must_be_one_of_the_premises():
    """A 'premise' not in the premise list is smuggling in an assumption."""
    p, q = v(P), v(Q)
    res = check([S(p, Rule.PREMISE), S(q, Rule.PREMISE)], [p])
    assert_bad(res, 1, "q is not a premise")
    assert "premise" in res.reason
    assert_bad(check([S(p, Rule.PREMISE)], []), 0, "no premises at all")


def test_premise_step_must_not_cite():
    """premise takes zero cites."""
    p = v(P)
    res = check([S(p, Rule.PREMISE), S(p, Rule.PREMISE, 0)], [p])
    assert_bad(res, 1)
    assert "cites" in res.reason


# =========================== citation discipline ============================
@pytest.mark.parametrize("cite, label", [(2, "its own step"), (3, "a later step"), (-1, "a negative index"), (99, "out of range")])
def test_citing_non_earlier_steps_is_rejected(cite, label):
    """Step 2 may only cite indices 0 and 1: own, later, negative and out-of-range indices break the proof's acyclicity."""
    p = v(P)
    proof = [S(p, Rule.PREMISE), S(p, Rule.PREMISE), S(p, Rule.AND_ELIM_LEFT, cite), S(p, Rule.PREMISE)]
    res = check(proof, [p])
    assert_bad(res, 2, label)
    assert "earlier" in res.reason, "citation failures must say the cite is not an earlier step"


def test_circular_justification_is_rejected():
    """Step 0 citing step 1 which cites step 0: both are non-earlier cites, first bad step is 0."""
    p = v(P)
    proof = [S(p, Rule.AND_ELIM_LEFT, 1), S(And(p, p), Rule.AND_INTRO, 0, 0)]
    assert_bad(check(proof, []), 0, "forward reference")


@pytest.mark.parametrize(
    "step_builder",
    [
        lambda p, q: S(q, Rule.MODUS_PONENS, 0),
        lambda p, q: S(q, Rule.MODUS_PONENS, 0, 0, 0),
        lambda p, q: S(q, Rule.AND_INTRO, 0),
        lambda p, q: S(q, Rule.AND_ELIM_LEFT, 0, 0),
        lambda p, q: S(q, Rule.AND_ELIM_RIGHT),
        lambda p, q: S(q, Rule.OR_INTRO_LEFT),
        lambda p, q: S(q, Rule.DOUBLE_NEGATION_ELIM, 0, 0),
        lambda p, q: S(q, Rule.MODUS_TOLLENS),
    ],
)
def test_wrong_number_of_cites_is_rejected(step_builder):
    """Each rule has a fixed arity; the reason must mention 'cites'."""
    p, q = v(P), v(Q)
    res = check([S(p, Rule.PREMISE), step_builder(p, q)], [p])
    assert_bad(res, 1)
    assert "cites" in res.reason


# =========================== reporting ======================================
def test_first_invalid_step_is_reported_not_later_ones():
    """Steps 2 and 4 are both invalid; the checker must report 2 and stop."""
    p, q = v(P), v(Q)
    proof = [
        S(p, Rule.PREMISE), S(q, Rule.PREMISE),
        S(q, Rule.AND_ELIM_LEFT, 0),  # invalid: p is not a conjunction
        S(And(p, q), Rule.AND_INTRO, 0, 1),
        S(p, Rule.PREMISE, 0),  # also invalid
    ]
    assert_bad(check(proof, [p, q]), 2)


def test_reason_format_mentions_step_index_and_rule_name():
    """Reason text starts with 'step <i> (<rule>): ' so tooling can parse it."""
    p, q = v(P), v(Q)
    res = check([S(p, Rule.PREMISE), S(q, Rule.MODUS_PONENS, 0, 0)], [p])
    assert_bad(res, 1)
    assert res.reason.startswith("step 1 (modus_ponens): ")
    assert res.reason[len("step 1 (modus_ponens): "):].strip(), "a non-empty detail must follow the prefix"


def test_checkresult_is_frozen():
    """Results are values; mutation must fail."""
    res = check([], [])
    with pytest.raises(Exception):
        res.ok = False  # type: ignore[misc]


# =========================== soundness property =============================
def pool():
    return [Var("a"), Not(Var("b")), Const(True)]


def options(steps):
    """All (rule, cites, conclusion) the contract allows, computed by an independent reference."""
    out = []
    n = len(steps)
    for i in range(n):
        fi = steps[i]
        for x in pool():
            out.append((Rule.OR_INTRO_LEFT, (i,), Or(fi, x)))
            out.append((Rule.OR_INTRO_RIGHT, (i,), Or(x, fi)))
        if isinstance(fi, And):
            out.append((Rule.AND_ELIM_LEFT, (i,), fi.left))
            out.append((Rule.AND_ELIM_RIGHT, (i,), fi.right))
        if isinstance(fi, Not) and isinstance(fi.operand, Not):
            out.append((Rule.DOUBLE_NEGATION_ELIM, (i,), fi.operand.operand))
        for j in range(n):
            fj = steps[j]
            out.append((Rule.AND_INTRO, (i, j), And(fi, fj)))
            if isinstance(fi, Implies) and fi.left == fj:
                out.append((Rule.MODUS_PONENS, (i, j), fi.right))
            if isinstance(fi, Implies) and fj == Not(fi.right):
                out.append((Rule.MODUS_TOLLENS, (i, j), Not(fi.left)))
    return out


def entailed(premises, f):
    return ref_countermodel(premises, f) is None


@given(st.lists(formulas(names=["a", "b"], max_leaves=4), min_size=1, max_size=3), st.data())
def test_property_reference_derivations_are_accepted_and_sound(premises, data):
    """Completeness+soundness of the oracle: any chain built from the documented rules is accepted by check, and every line is entailed."""
    steps = [S(f, Rule.PREMISE) for f in premises]
    for _ in range(data.draw(st.integers(0, 6))):
        opts = options([s.formula for s in steps])
        rule, cites, concl = data.draw(st.sampled_from(opts))
        steps.append(S(concl, rule, *cites))
    assert_ok(check(steps, premises), "a derivation built from the rules must check")
    assert all(entailed(premises, s.formula) for s in steps), "oracle bug: a rule produced a non-consequence"


@given(st.lists(formulas(names=["a", "b"], max_leaves=4), min_size=1, max_size=3), st.data(), formulas(names=["a", "b"]))
def test_property_checker_never_accepts_a_non_consequence(premises, data, junk):
    """Soundness of the CHECKER: corrupt one line of a valid proof; if it still checks ok, every line must still be entailed by the premises."""
    steps = [S(f, Rule.PREMISE) for f in premises]
    for _ in range(data.draw(st.integers(1, 6))):
        rule, cites, concl = data.draw(st.sampled_from(options([s.formula for s in steps])))
        steps.append(S(concl, rule, *cites))
    i = data.draw(st.integers(0, len(steps) - 1))
    bad = list(steps)
    bad[i] = Step(junk, steps[i].rule, steps[i].cites)
    if check(bad, premises).ok:
        assert all(entailed(premises, s.formula) for s in bad), "checker accepted a line that is not a consequence"
