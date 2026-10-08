"""Contract tests for dsdk.logic.semantics: evaluate, Kleene evaluate_partial, models, truth tables, entailment."""
import collections.abc
import itertools

import pytest
from hypothesis import given, strategies as st

from dsdk.core import Judgment, Status
from dsdk.logic import (
    And, Const, Iff, Implies, Not, Or, UnassignedVariableError, Var, countermodel, entails, evaluate,
    evaluate_partial, is_satisfiable, is_valid, models, truth_table, variables,
)

from helpers import (
    formulas, left_chain, not_chain, ref_assignments, ref_countermodel, ref_eval, ref_models, ref_vars, right_chain,
)

T, F = True, False
BINARIES = [And, Or, Implies, Iff]
a, b, c = "a", "b", "c"


def V(n):
    return Var(n)


# =========================== evaluate (two-valued) ==========================
BOOL_TABLES = {
    And: lambda x, y: x and y,
    Or: lambda x, y: x or y,
    Implies: lambda x, y: (not x) or y,
    Iff: lambda x, y: x == y,
}


@pytest.mark.parametrize("cls", BINARIES)
@pytest.mark.parametrize("x, y", list(itertools.product([F, T], repeat=2)))
def test_evaluate_binary_connective_tables(cls, x, y):
    """Each connective matches its classical truth table on all four inputs."""
    assert evaluate(cls(V("x"), V("y")), {"x": x, "y": y}) is BOOL_TABLES[cls](x, y)


def test_evaluate_not_const_and_returns_real_bool():
    """Results are real bools (``is True``), including for Const-only formulas needing no assignment."""
    assert evaluate(Const(True), {}) is True and evaluate(Const(False), {}) is False
    assert evaluate(Not(Const(False)), {}) is True
    assert evaluate(Not(V("x")), {"x": True}) is False


def test_evaluate_tautology_and_contradiction():
    """x or not x is true under both assignments; x and not x under neither."""
    taut, contra = Or(V("x"), Not(V("x"))), And(V("x"), Not(V("x")))
    for v in (F, T):
        assert evaluate(taut, {"x": v}) is True and evaluate(contra, {"x": v}) is False


def test_evaluate_missing_variable_raises_unassigned():
    """Missing variable -> UnassignedVariableError (a KeyError) carrying the name."""
    with pytest.raises(UnassignedVariableError) as info:
        evaluate(And(V("x"), V("y")), {"x": True})
    assert info.value.name == "y"
    assert isinstance(info.value, KeyError)


def test_evaluate_reports_alphabetically_first_missing_variable():
    """When several are missing the error names the alphabetically first one (deterministic message)."""
    with pytest.raises(UnassignedVariableError) as info:
        evaluate(Or(V("b"), V("a")), {})
    assert info.value.name == "a"


@pytest.mark.parametrize(
    "build",
    [
        lambda: And(Const(False), Var("x")),
        lambda: Or(Const(True), Var("x")),
        lambda: Implies(Const(False), Var("x")),
        lambda: Or(Var("x"), Const(True)),
    ],
)
def test_evaluate_does_not_short_circuit_around_missing_variables(build):
    """evaluate RAISES even when the missing variable cannot affect the result (that is what evaluate_partial is for)."""
    with pytest.raises(UnassignedVariableError):
        evaluate(build(), {})


def test_evaluate_ignores_extra_keys():
    """Irrelevant assignment entries do not matter."""
    assert evaluate(V("x"), {"x": True, "zzz": False, "w": 17}) is True


@pytest.mark.parametrize("bad", [1, 0, None, "True", 1.0])
def test_evaluate_rejects_non_bool_values(bad):
    """Assignment values must be real bools; 1/0 would silently work in Python and hide bugs."""
    with pytest.raises(TypeError):
        evaluate(V("x"), {"x": bad})


# =========================== evaluate_partial (strong Kleene) ===============
U = None  # three-valued 'unknown' marker inside this test module only
KLEENE = {
    And: {(T, T): T, (T, F): F, (T, U): U, (F, T): F, (F, F): F, (F, U): F, (U, T): U, (U, F): F, (U, U): U},
    Or: {(T, T): T, (T, F): T, (T, U): T, (F, T): T, (F, F): F, (F, U): U, (U, T): T, (U, F): U, (U, U): U},
    Implies: {(T, T): T, (T, F): F, (T, U): U, (F, T): T, (F, F): T, (F, U): T, (U, T): T, (U, F): U, (U, U): U},
    Iff: {(T, T): T, (T, F): F, (T, U): U, (F, T): F, (F, F): T, (F, U): U, (U, T): U, (U, F): U, (U, U): U},
}


def env(**vals):
    """Build an assignment omitting every variable whose value is None (=unknown)."""
    return {k: v for k, v in vals.items() if v is not None}


def assert_kleene(j, expected, ctx):
    assert isinstance(j, Judgment), f"{ctx}: must return a dsdk.core.Judgment"
    if expected is None:
        assert j.status is Status.UNKNOWN and j.value is None, f"{ctx}: expected UNKNOWN, got {j}"
    else:
        assert j.status is Status.KNOWN and j.value is expected, f"{ctx}: expected KNOWN {expected}, got {j}"


@pytest.mark.parametrize("cls", BINARIES)
@pytest.mark.parametrize("x, y", list(itertools.product([T, F, U], repeat=2)))
def test_kleene_binary_tables_all_nine_combinations(cls, x, y):
    """Strong Kleene tables, hard-coded: e.g. F and U = F, T or U = T, F implies U = T, U iff anything = U."""
    j = evaluate_partial(cls(V("x"), V("y")), env(x=x, y=y))
    assert_kleene(j, KLEENE[cls][(x, y)], f"{cls.__name__}({x},{y})")


@pytest.mark.parametrize("x, expected", [(T, F), (F, T), (U, U)])
def test_kleene_not_table(x, expected):
    """Not flips known values and leaves unknown unknown."""
    assert_kleene(evaluate_partial(Not(V("x")), env(x=x)), expected, f"Not({x})")


def test_kleene_false_and_unknown_is_known_false_both_orders():
    """The headline Kleene case: False and x is KNOWN False regardless of x, in either operand position."""
    assert_kleene(evaluate_partial(And(Const(False), V("x")), {}), F, "F and x")
    assert_kleene(evaluate_partial(And(V("x"), Const(False)), {}), F, "x and F")
    assert_kleene(evaluate_partial(Or(Const(True), V("x")), {}), T, "T or x")
    assert_kleene(evaluate_partial(Or(V("x"), Const(True)), {}), T, "x or T")


def test_kleene_implication_shortcuts():
    """False -> x and x -> True are KNOWN True; True -> x and x -> False stay UNKNOWN."""
    assert_kleene(evaluate_partial(Implies(Const(False), V("x")), {}), T, "F->x")
    assert_kleene(evaluate_partial(Implies(V("x"), Const(True)), {}), T, "x->T")
    assert_kleene(evaluate_partial(Implies(Const(True), V("x")), {}), U, "T->x")
    assert_kleene(evaluate_partial(Implies(V("x"), Const(False)), {}), U, "x->F")


@pytest.mark.parametrize(
    "build",
    [
        lambda: Or(Var("x"), Not(Var("x"))),
        lambda: And(Var("x"), Not(Var("x"))),
        lambda: Implies(Var("x"), Var("x")),
        lambda: Iff(Var("x"), Var("x")),
    ],
)
def test_kleene_is_truth_functional_not_tautology_aware(build):
    """x or not x, x and not x, x->x, x<->x are UNKNOWN for unassigned x: Kleene logic does not realise both x's are the same.
    (A naive 'try both values' implementation would wrongly answer KNOWN.)"""
    assert_kleene(evaluate_partial(build(), {}), U, "same-variable formula")


def test_kleene_nested_shortcut_through_unknown_subterms():
    """KNOWN must propagate through deep structure: (x or y) and False = False; Not(F and x) = True."""
    assert_kleene(evaluate_partial(And(Or(V("x"), V("y")), Const(False)), {}), F, "(x|y)&F")
    assert_kleene(evaluate_partial(Not(And(Const(False), V("x"))), {}), T, "~(F&x)")
    assert_kleene(evaluate_partial(Iff(And(Const(False), V("x")), Const(False)), {}), T, "(F&x)<->F")


def test_partial_reason_lists_all_unassigned_variables_sorted():
    """UNKNOWN reason is exactly 'unassigned: ' + sorted names of ALL missing variables of f (even irrelevant ones)."""
    j = evaluate_partial(And(V("y"), Or(Const(True), V("x"))), {})
    assert j == Judgment(Status.UNKNOWN, None, "unassigned: x, y"), f"got {j!r}"
    j = evaluate_partial(Or(V("q"), V("p")), {"p": False})
    assert j.reason == "unassigned: q"


def test_partial_known_has_empty_reason():
    """KNOWN results carry no reason, even if some irrelevant variable was unassigned."""
    j = evaluate_partial(And(Const(False), V("x")), {})
    assert j == Judgment(Status.KNOWN, False, "")


def test_partial_const_only_formulas_are_known_with_empty_assignment():
    """Degenerate input: nothing to assign, so always KNOWN."""
    assert evaluate_partial(Const(True), {}) == Judgment(Status.KNOWN, True)
    assert evaluate_partial(Not(Implies(Const(True), Const(False))), {}) == Judgment(Status.KNOWN, True)


def test_partial_total_assignment_gives_known():
    """With every variable assigned the answer is KNOWN and equals evaluate."""
    f = Iff(V("x"), Not(V("y")))
    assert evaluate_partial(f, {"x": True, "y": False}) == Judgment(Status.KNOWN, True)


def test_partial_ignores_extra_keys_and_rejects_non_bool_values():
    """Extra keys are ignored; a non-bool value for a variable that occurs in f is a TypeError."""
    assert evaluate_partial(V("x"), {"x": True, "other": 5}) == Judgment(Status.KNOWN, True)
    with pytest.raises(TypeError):
        evaluate_partial(V("x"), {"x": 1})
    with pytest.raises(TypeError):
        evaluate_partial(V("x"), {"x": None})


@given(formulas(), st.data())
def test_property_partial_agrees_with_evaluate_on_total_assignments(f, data):
    """On a total assignment evaluate_partial is KNOWN and equals evaluate (the two evaluators must not disagree)."""
    env_ = {n: data.draw(st.booleans()) for n in sorted(ref_vars(f))}
    assert evaluate_partial(f, env_) == Judgment(Status.KNOWN, evaluate(f, env_))


@given(formulas(), st.data())
def test_property_partial_known_is_sound_for_every_completion(f, data):
    """If evaluate_partial says KNOWN v, then EVERY completion of the partial assignment evaluates to v (Kleene soundness)."""
    names = sorted(ref_vars(f))
    partial = {n: data.draw(st.booleans()) for n in names if data.draw(st.booleans())}
    j = evaluate_partial(f, partial)
    missing = [n for n in names if n not in partial]
    if j.status is not Status.KNOWN:
        return
    for combo in itertools.product([False, True], repeat=len(missing)):
        full = {**partial, **dict(zip(missing, combo))}
        assert ref_eval(f, full) is j.value, f"completion {full} disagrees with KNOWN {j.value}"


@given(formulas(), st.data())
def test_property_partial_is_monotone_in_information(f, data):
    """Assigning one more variable never changes a KNOWN answer (information only helps)."""
    names = sorted(ref_vars(f))
    partial = {n: data.draw(st.booleans()) for n in names if data.draw(st.booleans())}
    before = evaluate_partial(f, partial)
    free = [n for n in names if n not in partial]
    extended = {**partial, **{n: data.draw(st.booleans()) for n in free[:1]}}
    after = evaluate_partial(f, extended)
    if before.status is Status.KNOWN:
        assert after == before, "extra information changed a KNOWN answer"


# =========================== models / truth_table ==========================
def as_pairs(ms):
    return [tuple(sorted(m.items())) for m in ms]


def test_models_order_is_false_before_true_first_variable_slowest():
    """Enumeration order is itertools.product([F,T]) over sorted names: the contract that countermodel and A3 rely on."""
    out = list(models(Or(V("a"), V("b"))))
    assert out == [{"a": F, "b": T}, {"a": T, "b": F}, {"a": T, "b": T}]
    out3 = list(models(Or(V("a"), Or(V("b"), V("c")))))
    assert out3[0] == {"a": F, "b": F, "c": T} and out3[-1] == {"a": T, "b": T, "c": T} and len(out3) == 7


def test_models_names_sorted_by_plain_string_order_and_keys_in_that_order():
    """Sorting is plain str order: 'B' < '_' < 'a'; each dict's keys are in that order."""
    f = Or(Or(V("a"), V("B")), V("_"))
    out = list(models(f, over=["a", "_", "B"]))
    assert all(list(m) == ["B", "_", "a"] for m in out)
    assert out[0] == {"B": F, "_": F, "a": T}, "first model: all-False prefix, last (fastest) variable flips first"


def test_models_of_constants():
    """Const(True) has exactly one model (the empty assignment); Const(False) has none."""
    assert list(models(Const(True))) == [{}]
    assert list(models(Const(False))) == []


def test_models_contradiction_and_tautology_counts():
    """x and not x: 0 models; x or not x: 2 models (over its one variable)."""
    assert list(models(And(V("x"), Not(V("x"))))) == []
    assert len(list(models(Or(V("x"), Not(V("x")))))) == 2


def test_models_over_extends_the_variable_set():
    """Extra names in `over` are free variables: each doubles the model count, and ordering uses the sorted union."""
    out = list(models(V("a"), over=["b", "a"]))
    assert out == [{"a": T, "b": F}, {"a": T, "b": T}]
    assert len(list(models(Const(True), over=["p", "q", "r"]))) == 8


def test_models_over_duplicates_collapse():
    """Duplicates in `over` do not multiply the models."""
    assert len(list(models(V("a"), over=["a", "a", "b", "b"]))) == 2


def test_models_over_missing_a_formula_variable_is_valueerror():
    """`over` must cover variables(f); otherwise the models would be ill-defined."""
    with pytest.raises(ValueError):
        list(models(And(V("a"), V("b")), over=["a"]))


def test_models_is_a_lazy_iterator():
    """models returns a real iterator (iter(x) is x), so callers can stream/limit it."""
    it = models(Or(V("a"), V("b")))
    assert isinstance(it, collections.abc.Iterator) and iter(it) is it
    assert next(it) == {"a": F, "b": T}
    assert next(it) == {"a": T, "b": F}


def test_models_yields_fresh_dicts():
    """Mutating one yielded dict must not affect the others (a reused dict object is a classic bug)."""
    out = list(models(Or(V("a"), V("b"))))
    assert len({id(m) for m in out}) == len(out)
    out[0]["a"] = "corrupt"
    assert out[1] == {"a": T, "b": F} and out[2] == {"a": T, "b": T}


def test_truth_table_exact_rows_and_order():
    """truth_table lists ALL rows (including False) in enumeration order."""
    rows = truth_table(And(V("a"), V("b")))
    assert rows == [({"a": F, "b": F}, F), ({"a": F, "b": T}, F), ({"a": T, "b": F}, F), ({"a": T, "b": T}, T)]


def test_truth_table_const_only_has_one_row():
    """Zero variables -> a single row with the empty assignment."""
    assert truth_table(Const(True)) == [({}, True)]
    assert truth_table(Not(Const(True))) == [({}, False)]


def test_truth_table_rows_are_independent_dicts():
    """Rows must not share assignment dicts."""
    rows = truth_table(Or(V("a"), V("b")))
    rows[0][0]["a"] = "corrupt"
    assert rows[1][0] == {"a": F, "b": T}


@given(formulas())
def test_property_models_and_truth_table_match_reference(f):
    """models/truth_table agree with a naive enumerator, including ORDER."""
    assert list(models(f)) == ref_models(f)
    names = sorted(ref_vars(f))
    assert truth_table(f) == [(m, ref_eval(f, m)) for m in ref_assignments(names)]


# =========================== satisfiable / valid ===========================
def test_satisfiable_and_valid_basic_cases():
    """Tautology: valid+sat. Contradiction: unsat+not valid. Contingent: sat, not valid."""
    taut, contra, cont = Or(V("x"), Not(V("x"))), And(V("x"), Not(V("x"))), V("x")
    assert (is_satisfiable(taut), is_valid(taut)) == (True, True)
    assert (is_satisfiable(contra), is_valid(contra)) == (False, False)
    assert (is_satisfiable(cont), is_valid(cont)) == (True, False)


def test_satisfiable_and_valid_const_only_formulas():
    """Degenerate: no variables, one (empty) assignment."""
    assert (is_satisfiable(Const(True)), is_valid(Const(True))) == (True, True)
    assert (is_satisfiable(Const(False)), is_valid(Const(False))) == (False, False)


def test_valid_classics():
    """Peirce's law and De Morgan are valid; affirming the consequent as a formula is not."""
    x, y = V("x"), V("y")
    peirce = Implies(Implies(Implies(x, y), x), x)
    de_morgan = Iff(Not(And(x, y)), Or(Not(x), Not(y)))
    affirm = Implies(And(Implies(x, y), y), x)
    assert is_valid(peirce) and is_valid(de_morgan)
    assert not is_valid(affirm) and is_satisfiable(affirm)


@given(formulas())
def test_property_valid_iff_negation_unsatisfiable(f):
    """is_valid(f) == not is_satisfiable(Not(f)): the duality that defines validity."""
    assert is_valid(f) == (not is_satisfiable(Not(f)))


@given(formulas())
def test_property_sat_valid_match_reference(f):
    """is_satisfiable / is_valid agree with a naive enumeration."""
    ms = ref_models(f)
    assert is_satisfiable(f) == bool(ms)
    assert is_valid(f) == (len(ms) == 2 ** len(ref_vars(f)))


# =========================== entails / countermodel ========================
def test_entails_empty_premises_means_valid():
    """No premises: the conclusion must be a tautology."""
    assert entails([], Or(V("x"), Not(V("x")))) is True
    assert entails([], V("x")) is False
    assert entails([], Const(True)) is True and entails([], Const(False)) is False


def test_entails_contradictory_premises_entail_everything():
    """Ex falso: inconsistent premises entail any conclusion, even one over a fresh variable."""
    prem = [V("x"), Not(V("x"))]
    assert entails(prem, V("never_mentioned")) is True
    assert entails([Const(False)], Const(False)) is True


def test_entails_modus_ponens_yes_affirming_consequent_no():
    """{p->q, p} entails q; {p->q, q} does NOT entail p."""
    p, q = V("p"), V("q")
    assert entails([Implies(p, q), p], q) is True
    assert entails([Implies(p, q), q], p) is False


def test_entails_conclusion_with_fresh_variable():
    """Variables only in the conclusion count: {a} does not entail b, but entails a or b."""
    assert entails([V("a")], V("b")) is False
    assert entails([V("a")], Or(V("a"), V("b"))) is True


def test_entails_accepts_one_shot_generator_and_rejects_bare_formula():
    """premises may be any iterable (consumed once); a lone Formula instead of an iterable is a TypeError."""
    p, q = V("p"), V("q")
    assert entails((f for f in [Implies(p, q), p]), q) is True
    with pytest.raises(TypeError):
        entails(p, p)
    with pytest.raises(TypeError):
        countermodel(p, p)


def test_countermodel_none_when_entailed():
    """No countermodel exactly when the entailment holds."""
    p, q = V("p"), V("q")
    assert countermodel([Implies(p, q), p], q) is None


def test_countermodel_first_in_enumeration_order():
    """The FIRST countermodel in the module order is returned (not any/last/random)."""
    # premise a: (F,F),(F,T) fail the premise; (T,F) satisfies it and falsifies b -> first.
    assert countermodel([V("a")], V("b")) == {"a": T, "b": F}
    # no premises, conclusion a and b: (F,F) is the very first assignment.
    assert countermodel([], And(V("a"), V("b"))) == {"a": F, "b": F}
    # premise a or b, conclusion c over [a,b,c]: (F,F,F),(F,F,T) fail premise; (F,T,F) is first countermodel.
    assert countermodel([Or(V("a"), V("b"))], V("c")) == {"a": F, "b": T, "c": F}
    # premise a or b, conclusion a: only (F,T) works.
    assert countermodel([Or(V("a"), V("b"))], V("a")) == {"a": F, "b": T}


def test_countermodel_covers_variables_that_only_appear_in_premises():
    """Keys: the union of all variables, even ones irrelevant to the failure."""
    cm = countermodel([Or(V("b"), Not(V("b")))], V("a"))
    assert cm == {"a": F, "b": F}


def test_countermodel_of_unsatisfiable_conclusion_with_no_premises():
    """Const(False) has the countermodel {} (the single empty assignment)."""
    assert countermodel([], Const(False)) == {}
    assert countermodel([], Const(True)) is None


@given(st.lists(formulas(), max_size=3), formulas())
def test_property_entails_and_countermodel_match_reference(premises, conclusion):
    """entails/countermodel agree with a naive search; countermodel is None iff entails; and it really is a countermodel."""
    expected = ref_countermodel(premises, conclusion)
    assert countermodel(premises, conclusion) == expected
    assert entails(premises, conclusion) == (expected is None)
    if expected is not None:
        assert all(evaluate(p, expected) for p in premises) and not evaluate(conclusion, expected)


# =========================== deep nesting (depth 200 required) =============
DEPTH = 200


def test_deep_not_chain_evaluates_by_parity():
    """200 negations: even count -> same value, odd -> flipped (both evaluators)."""
    for n in (DEPTH, DEPTH + 1):
        f = not_chain(n, V("x"))
        for v in (F, T):
            want = v if n % 2 == 0 else (not v)
            assert evaluate(f, {"x": v}) is want
            assert evaluate_partial(f, {"x": v}) == Judgment(Status.KNOWN, want)
        assert evaluate_partial(f, {}).status is Status.UNKNOWN


def test_deep_chains_in_semantics():
    """Depth-200 left/right chains: models, validity, satisfiability and Kleene shortcuts all work."""
    x = V("x")
    right_imp = right_chain(Implies, DEPTH, x)  # x -> (x -> (... x))  valid
    assert is_valid(right_imp) and len(list(models(right_imp))) == 2
    left_and = left_chain(And, DEPTH, x)  # ((x&x)&x)... equals x
    assert list(models(left_and)) == [{"x": T}]
    deep_or_true = left_chain(Or, DEPTH, Const(True))
    assert evaluate(deep_or_true, {}) is True
    chain = left_chain(And, DEPTH, Const(False))
    assert evaluate_partial(And(chain, x), {}) == Judgment(Status.KNOWN, False)
    assert is_satisfiable(left_chain(Iff, DEPTH, x)) is True


def test_deep_formula_entailment():
    """entails/countermodel on depth-200 formulas (single variable, so enumeration is tiny)."""
    x = V("x")
    deep = not_chain(DEPTH, x)  # equivalent to x
    assert entails([deep], x) is True
    assert countermodel([], deep) == {"x": F}
