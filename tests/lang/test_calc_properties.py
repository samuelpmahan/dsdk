"""Hypothesis properties tying typecheck, step, trace and evaluate together: type safety (progress + preservation), agreement of big- and small-step, termination measure, substitution lemma."""
from hypothesis import given
from hypothesis import strategies as st

from dsdk.core import Judgment, Status
from dsdk.lang.calc import (
    BoolLit, IntLit, Outcome, StuckError, Type, classify, evaluate, free_vars, is_value, size, step, substitute, to_python,
    trace, typecheck,
)

from lang_helpers import OracleStuck, any_exprs, closed_typed, oracle_eval, show, typed_exprs

PY = {Type.INT: int, Type.BOOL: bool}


@given(closed_typed)
def test_progress_well_typed_closed_terms_are_never_stuck(case):
    """PROGRESS: a closed well-typed term is a value or can step. (Stuck = a bug in either the typing rules or the step rules.)"""
    ty, e = case
    assert typecheck(e) == Judgment(Status.KNOWN, ty), show(e)
    assert classify(e) in (Outcome.VALUE, Outcome.STEP), f"{show(e)} is well-typed yet stuck"


@given(closed_typed)
def test_preservation_every_step_keeps_the_type(case):
    """PRESERVATION: if e : T and e -> e' then e' : T (the generator gives e : T; every term of the trace must keep T)."""
    ty, e = case
    for before, after in zip(trace(e), trace(e)[1:]):
        assert step(before) == after
        assert typecheck(after) == Judgment(Status.KNOWN, ty), f"{show(before)} -> {show(after)} changed the type"


@given(closed_typed)
def test_type_safety_trace_ends_in_a_value_of_the_static_type(case):
    """TYPE SAFETY: a well-typed closed program evaluates to a value whose Python type matches its static type."""
    ty, e = case
    final = trace(e)[-1]
    assert is_value(final) and classify(final) is Outcome.VALUE
    assert type(to_python(final)) is PY[ty]


@given(closed_typed)
def test_big_step_equals_end_of_small_step_trace_on_well_typed_terms(case):
    """evaluate(e) == the value at the end of trace(e), with the same Python type (two independent implementations agree)."""
    _, e = case
    got, final = evaluate(e), to_python(trace(e)[-1])
    assert got == final and type(got) is type(final), show(e)


@given(any_exprs(max_leaves=12))
def test_big_step_agrees_with_small_step_on_arbitrary_terms(e):
    """Even for ill-typed and open terms: trace ends in a value  <=>  evaluate returns it; trace ends stuck  <=>  evaluate raises StuckError."""
    last = trace(e)[-1]
    if is_value(last):
        got = evaluate(e)
        assert got == to_python(last) and type(got) is type(to_python(last)), show(e)
    else:
        try:
            evaluate(e)
        except StuckError as err:
            assert err.term == e
        else:
            raise AssertionError(f"{show(e)} is stuck in the trace (at {show(last)}) but evaluate returned a value")


@given(any_exprs(max_leaves=12))
def test_evaluate_agrees_with_an_environment_based_oracle(e):
    """The test-suite's own environment-passing evaluator (no substitution) gives the same answer as evaluate on ANY term: substitution and environments are two views of one semantics."""
    try:
        want = oracle_eval(e)
    except OracleStuck:
        try:
            evaluate(e)
        except StuckError:
            return
        raise AssertionError(f"oracle is stuck on {show(e)} but evaluate returned")
    got = evaluate(e)
    assert got == want and type(got) is type(want), show(e)


@given(any_exprs(max_leaves=12))
def test_every_step_strictly_decreases_the_size_measure(e):
    """TERMINATION MEASURE: size strictly decreases at each step, so trace length <= size(e) - 1 and evaluation always halts (see tracks/A2/PROOFS.md)."""
    t = trace(e)
    sizes = [size(x) for x in t]
    assert all(b < a for a, b in zip(sizes, sizes[1:])), f"size did not shrink along {[show(x) for x in t]}"
    assert len(t) - 1 <= size(e) - 1


@given(any_exprs(max_leaves=12))
def test_steps_never_invent_free_variables(e):
    """free_vars(e') is a subset of free_vars(e) for every step e -> e' (substitution only removes variables)."""
    for before, after in zip(trace(e), trace(e)[1:]):
        assert free_vars(after) <= free_vars(before)


@given(any_exprs(max_leaves=12))
def test_stuck_terms_are_ill_typed(e):
    """CONTRAPOSITIVE OF SAFETY: if a closed term's trace ends stuck, typecheck must have reported INVALID."""
    if free_vars(e):
        return
    if classify(trace(e)[-1]) is Outcome.STUCK:
        assert typecheck(e).status is Status.INVALID, f"{show(e)} gets stuck but typechecks"


@given(any_exprs(max_leaves=10))
def test_typecheck_known_implies_no_unbound_variables(e):
    """Under env {x: Int, y: Bool}, a KNOWN result means every free variable is in the environment; an unbound-variable error names a free variable."""
    env = {"x": Type.INT, "y": Type.BOOL}
    j = typecheck(e, env)
    if j.status is Status.KNOWN:
        assert free_vars(e) <= set(env)
    elif j.reason.startswith("unbound variable: "):
        assert j.reason.split(": ", 1)[1] in free_vars(e)


@given(st.sampled_from([Type.INT, Type.BOOL]).flatmap(lambda t: typed_exprs(t, env=[("x", Type.INT)]).map(lambda e: (t, e))), st.integers(-5, 5))
def test_substitution_lemma_substituting_a_value_of_the_right_type_preserves_typing(case, n):
    """If x:Int |- e : T and v : Int then e[x := v] : T in the empty environment. This is the lemma that makes the `let` case of preservation work."""
    ty, e = case
    assert typecheck(e, {"x": Type.INT}) == Judgment(Status.KNOWN, ty)
    assert typecheck(substitute(e, "x", IntLit(n))) == Judgment(Status.KNOWN, ty), show(e)


@given(st.sampled_from([Type.INT, Type.BOOL]).flatmap(lambda t: typed_exprs(t, env=[("x", Type.BOOL)]).map(lambda e: (t, e))), st.booleans())
def test_substitution_lemma_for_bool_values(case, v):
    """Same lemma with a Bool variable and Bool literal."""
    ty, e = case
    assert typecheck(substitute(e, "x", BoolLit(v))) == Judgment(Status.KNOWN, ty), show(e)


@given(closed_typed)
def test_closed_well_typed_terms_have_no_free_variables(case):
    """The generator's closed terms are closed: free_vars is empty, so evaluate never reports an unbound variable for them."""
    _, e = case
    assert free_vars(e) == frozenset()
    evaluate(e)
