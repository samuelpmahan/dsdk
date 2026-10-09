"""Contract tests for small-step semantics: exact rules, evaluation order, stuck vs value vs ill-typed, shadowing, traces."""
import pytest

from dsdk.lang.calc import BinOp, BoolLit, IntLit, Let, Outcome, Var, classify, step, trace

from lang_helpers import T, right_sum, show

# (term, result of ONE step as canonical source, or None when the term is a value or stuck)
STEPS = [
    # arithmetic and comparison: values in, value out
    ("(1 + 2)", "3"), ("(5 - 7)", "-2"), ("(-2 * -3)", "6"), ("(3 * 0)", "0"), ("(1 < 2)", "true"), ("(2 < 2)", "false"),
    ("(1 == 1)", "true"), ("(1 == 2)", "false"), ("(true == true)", "true"), ("(true == false)", "false"), ("(false == false)", "true"),
    ("(99999999999999999999 * 99999999999999999999)", "9999999999999999999800000000000000000001"),
    # left operand first, and only then the right one
    ("((1 + 2) + (3 + 4))", "(3 + (3 + 4))"), ("(3 + (3 + 4))", "(3 + 7)"), ("(1 + (2 + 3))", "(1 + 5)"),
    ("((1 + 2) * (3 + 4))", "(3 * (3 + 4))"), ("((1 < 2) == (3 < 4))", "(true == (3 < 4))"), ("(x + (1 + 2))", None),
    ("((2 * 3) - (1 + 1))", "(6 - (1 + 1))"),
    # not
    ("(not true)", "false"), ("(not false)", "true"), ("(not (not true))", "(not false)"), ("(not (1 < 2))", "(not true)"),
    # if: condition first, then ONLY the chosen branch is kept
    ("(if true then 1 else 2)", "1"), ("(if false then 1 else 2)", "2"), ("(if (1 < 2) then (3 + 4) else (5 + 6))", "(if true then (3 + 4) else (5 + 6))"),
    ("(if true then 1 else (1 + true))", "1"), ("(if false then (1 + true) else 2)", "2"), ("(if true then (1 + 1) else 0)", "(1 + 1)"),
    # and / or short-circuit; the right side is never looked at under A2 / O2
    ("(false and (1 + true))", "false"), ("(false and x)", "false"), ("(true and (1 < 2))", "(1 < 2)"), ("(true and x)", "x"),
    ("(true or x)", "true"), ("(true or (1 + true))", "true"), ("(false or (1 < 2))", "(1 < 2)"), ("(false or x)", "x"),
    ("((1 < 2) and x)", "(true and x)"), ("((1 < 2) or x)", "(true or x)"), ("(((1 < 2) and (2 < 1)) or (1 < 3))", "((true and (2 < 1)) or (1 < 3))"),
    ("(true and 5)", "5"),
    # let: bound expression first (call by value); then substitute the VALUE into the body
    ("(let x = (1 + 2) in (x * x))", "(let x = 3 in (x * x))"), ("(let x = 3 in (x * x))", "(3 * 3)"),
    ("(let x = 1 in 5)", "5"), ("(let x = true in (if x then 1 else 2))", "(if true then 1 else 2)"),
    ("(let x = 1 in (let x = 2 in x))", "(let x = 2 in x)"),
    ("(let x = 1 in ((let x = 2 in x) + x))", "((let x = 2 in x) + 1)"),
    ("(let x = 1 in (let y = x in (let x = 2 in (x + y))))", "(let y = 1 in (let x = 2 in (x + y)))"),
    ("(let x = 5 in (let x = (x + 1) in x))", "(let x = (5 + 1) in x)"),
    # no step: values
    ("5", None), ("-5", None), ("true", None), ("false", None),
    # no step: stuck because operands are values of the wrong kind
    ("(1 + true)", None), ("(true + 1)", None), ("(true * true)", None), ("(1 < true)", None), ("(true < 2)", None),
    ("(1 == true)", None), ("(true == 1)", None), ("(1 and true)", None), ("(1 or true)", None), ("(not 1)", None),
    ("(if 1 then 2 else 3)", None),
    # no step: a free variable is stuck, not a value
    ("x", None), ("(x + 1)", None), ("(1 + x)", None), ("(not x)", None), ("(if x then 1 else 2)", None), ("(let y = x in 1)", None),
    # stuck inside an evaluation position makes the whole term stuck
    ("((1 + true) + 2)", None), ("(2 + (1 + true))", None), ("(not (1 + true))", None), ("(if (1 + true) then 1 else 2)", None),
    ("(let x = (1 + true) in 5)", None), ("((1 + true) and false)", None), ("((1 + true) + (2 + 2))", None),
    ("(1 + (true + 2))", None), ("((x + 1) < 2)", None),
]


@pytest.mark.parametrize("src,nxt", STEPS, ids=[s for s, _ in STEPS])
def test_single_step_follows_the_exact_rules(src, nxt):
    """step applies exactly one rule (call-by-value, left to right, leftmost-innermost, and/or short-circuit) or returns None."""
    got = step(T(src))
    if nxt is None:
        assert got is None, f"{src} should not step, got {show(got) if got is not None else got}"
    else:
        assert got == T(nxt), f"{src} should step to {nxt}, got {show(got)}"


def test_step_returns_none_not_the_same_term_for_values():
    """A value does not step to itself (that would loop traces forever): the result is None."""
    assert step(IntLit(1)) is None and step(BoolLit(False)) is None


# ------------------------------------------------------------------ three different outcomes
def test_value_step_and_stuck_are_three_distinct_outcomes():
    """VALUE (a literal), STEP (a rule applies), STUCK (neither): a stuck term is not a value and not a term that can still reduce."""
    assert classify(T("5")) is Outcome.VALUE and classify(T("true")) is Outcome.VALUE
    assert classify(T("(1 + 2)")) is Outcome.STEP
    assert classify(T("(1 + true)")) is Outcome.STUCK
    assert classify(T("x")) is Outcome.STUCK, "an unbound variable is stuck, not a value"
    assert len({Outcome.VALUE, Outcome.STEP, Outcome.STUCK}) == 3


VALUE_SOURCES = ("5", "-5", "true", "false")


@pytest.mark.parametrize("src,nxt", STEPS, ids=[s for s, _ in STEPS])
def test_classify_agrees_with_step_on_every_table_row(src, nxt):
    """classify is derived from step: literals are VALUE, other terms that step are STEP, all remaining terms are STUCK."""
    if src in VALUE_SOURCES:
        expected = Outcome.VALUE
    elif nxt is None:
        expected = Outcome.STUCK
    else:
        expected = Outcome.STEP
    assert classify(T(src)) is expected, src


def test_ill_typed_does_not_imply_stuck_and_stuck_implies_ill_typed_example():
    """`(if true then 1 else (1 + true))` is ill-typed statically but reduces to the value 1 (not stuck); `(1 + true)` is stuck."""
    e = T("(if true then 1 else (1 + true))")
    assert classify(e) is Outcome.STEP
    assert [show(x) for x in trace(e)] == [show(e), "1"]
    assert classify(T("(1 + true)")) is Outcome.STUCK


# ------------------------------------------------------------------ traces
TRACES = [
    ("5", ["5"]),
    ("(1 + 2)", ["(1 + 2)", "3"]),
    ("((1 + 2) + (3 + 4))", ["((1 + 2) + (3 + 4))", "(3 + (3 + 4))", "(3 + 7)", "10"]),
    ("((1 + 1) + (2 + 2))", ["((1 + 1) + (2 + 2))", "(2 + (2 + 2))", "(2 + 4)", "6"]),
    ("((1 + 2) * (3 + 4))", ["((1 + 2) * (3 + 4))", "(3 * (3 + 4))", "(3 * 7)", "21"]),
    ("(if (1 < 2) then (3 + 4) else (5 + 6))", ["(if (1 < 2) then (3 + 4) else (5 + 6))", "(if true then (3 + 4) else (5 + 6))", "(3 + 4)", "7"]),
    ("(let x = (1 + 2) in (x * x))", ["(let x = (1 + 2) in (x * x))", "(let x = 3 in (x * x))", "(3 * 3)", "9"]),
    ("(let x = 1 in (let x = 2 in x))", ["(let x = 1 in (let x = 2 in x))", "(let x = 2 in x)", "2"]),
    ("(let x = 1 in ((let x = 2 in x) + x))", ["(let x = 1 in ((let x = 2 in x) + x))", "((let x = 2 in x) + 1)", "(2 + 1)", "3"]),
    ("(let x = 5 in (let x = (x + 1) in x))", ["(let x = 5 in (let x = (x + 1) in x))", "(let x = (5 + 1) in x)", "(let x = 6 in x)", "6"]),
    ("(let x = 1 in (let y = x in (let x = 2 in y)))", ["(let x = 1 in (let y = x in (let x = 2 in y)))", "(let y = 1 in (let x = 2 in y))", "(let x = 2 in 1)", "1"]),
    ("((1 < 2) and ((3 < 4) and (5 < 6)))", ["((1 < 2) and ((3 < 4) and (5 < 6)))", "(true and ((3 < 4) and (5 < 6)))", "((3 < 4) and (5 < 6))", "(true and (5 < 6))", "(5 < 6)", "true"]),
    ("(false and ((1 + 1) < 3))", ["(false and ((1 + 1) < 3))", "false"]),
    ("(not (not (1 < 2)))", ["(not (not (1 < 2)))", "(not (not true))", "(not false)", "true"]),
    # stuck traces END at the stuck term
    ("(1 + true)", ["(1 + true)"]),
    ("((1 + 1) + true)", ["((1 + 1) + true)", "(2 + true)"]),
    ("(let x = (1 + 1) in (x + true))", ["(let x = (1 + 1) in (x + true))", "(let x = 2 in (x + true))", "(2 + true)"]),
    ("x", ["x"]),
    ("(let y = 1 in (y + x))", ["(let y = 1 in (y + x))", "(1 + x)"]),
]


@pytest.mark.parametrize("src,expected", TRACES, ids=[s for s, _ in TRACES])
def test_trace_lists_every_term_from_start_to_value_or_stuck(src, expected):
    """trace returns [e0, ..., en] including the start and the final value/stuck term, each obtained by one step."""
    got = trace(T(src))
    assert [show(x) for x in got] == expected
    assert got[0] == T(src)


def test_evaluation_order_is_observable_left_operand_first():
    """In `(1+1) + (2+2)` the FIRST step must reduce the left addition; a right-first implementation gives `(1 + 1) + 4`."""
    assert show(step(T("((1 + 1) + (2 + 2))"))) == "(2 + (2 + 2))"
    assert show(step(T("((2 * 3) < (1 + 1))"))) == "(6 < (1 + 1))"


def test_stuck_left_operand_blocks_the_right_one():
    """With a stuck left operand the right operand is NEVER reduced (trace length 1); left-to-right evaluation is observable here."""
    assert [show(x) for x in trace(T("((1 + true) + (2 + 2))"))] == ["((1 + true) + (2 + 2))"]
    assert [show(x) for x in trace(T("((1 + true) * (2 * 2))"))] == ["((1 + true) * (2 * 2))"]


def test_call_by_value_let_is_stuck_when_the_bound_expression_is_stuck():
    """`let x = (1 + true) in 5` is stuck under call-by-value; a lazy (call-by-name) reading would reach 5."""
    assert classify(T("(let x = (1 + true) in 5)")) is Outcome.STUCK
    assert [show(x) for x in trace(T("(let x = (1 + true) in 5)"))] == ["(let x = (1 + true) in 5)"]


def test_if_discards_the_other_branch_unevaluated():
    """Neither branch is touched until the condition is a value, and the untaken one is dropped without a single step on it."""
    steps = [show(x) for x in trace(T("(if (1 < 2) then 7 else ((1 + 1) + (2 + 2)))"))]
    assert steps == ["(if (1 < 2) then 7 else ((1 + 1) + (2 + 2)))", "(if true then 7 else ((1 + 1) + (2 + 2)))", "7"]


def test_short_circuit_and_or_in_traces():
    """`false and <stuck>` finishes with false; `<stuck> and false` is stuck: the order of operands is semantics."""
    assert classify(trace(T("(false and (1 + true))"))[-1]) is Outcome.VALUE
    assert classify(trace(T("((1 + true) and false)"))[-1]) is Outcome.STUCK
    assert classify(trace(T("(true or (1 + true))"))[-1]) is Outcome.VALUE
    assert classify(trace(T("(false or (1 + true))"))[-1]) is Outcome.STUCK
    assert [show(x) for x in trace(T("(true and (1 + true))"))] == ["(true and (1 + true))", "(1 + true)"]


def test_shadowing_and_no_capture_in_substitution_steps():
    """Substitution during `let` must skip rebound names and never alter the bound expression of an inner let that mentions the outer name."""
    assert show(step(T("(let x = 1 in (let y = x in (let x = 2 in (x + y))))"))) == "(let y = 1 in (let x = 2 in (x + y)))"
    assert show(trace(T("(let x = 1 in (let y = x in (let x = 2 in (x + y))))"))[-1]) == "3"
    assert show(trace(T("(let x = 1 in ((let x = 2 in x) + x))"))[-1]) == "3"


def test_step_does_not_mutate_its_argument():
    """Terms are immutable values; stepping twice from the same term gives equal results."""
    e = T("(let x = (1 + 2) in (x * x))")
    first = step(e)
    assert step(e) == first and e == T("(let x = (1 + 2) in (x * x))")


def test_trace_of_a_deep_term_has_one_step_per_addition():
    """right_sum(200) has 200 additions: 201 terms, the last is the integer 201, and nothing recurses past the limit."""
    t = trace(right_sum(200))
    assert len(t) == 201 and t[-1] == IntLit(201)
    assert show(t[1]).count("(") == 199, "the INNERMOST addition (the only one with two literal operands) reduces first"


def test_step_and_trace_and_classify_reject_non_exprs():
    """Only Exprs are accepted; strings are not parsed implicitly."""
    for fn in (step, trace, classify):
        for bad in ("1 + 2", 5, None):
            with pytest.raises(TypeError):
                fn(bad)


def test_let_with_a_value_bound_substitutes_in_one_step():
    """`Let(x, v, body)` with v a value rewrites straight to body[x:=v]; no intermediate Let remains."""
    e = Let("x", IntLit(4), BinOp("+", Var("x"), Var("x")))
    assert step(e) == BinOp("+", IntLit(4), IntLit(4))
