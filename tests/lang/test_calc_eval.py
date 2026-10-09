"""Contract tests for the big-step reference evaluator `calc.evaluate` (independent of step/trace)."""
import pytest

from dsdk.lang import calc
from dsdk.lang.calc import BinOp, BoolLit, IntLit, StuckError, evaluate

from lang_helpers import T, right_sum

VALUES = [
    ("5", 5), ("-5", -5), ("true", True), ("false", False),
    ("(1 + 2)", 3), ("(10 - 3)", 7), ("(3 - 10)", -7), ("(4 * 5)", 20), ("(2 * (3 + 4))", 14), ("((10 - 3) - 2)", 5), ("(10 - (3 - 2))", 9),
    ("(1 < 2)", True), ("(2 < 1)", False), ("(2 < 2)", False), ("(3 == 3)", True), ("(3 == 4)", False),
    ("(true == true)", True), ("(true == false)", False), ("((1 < 2) == (3 < 4))", True),
    ("(not true)", False), ("(not (not true))", True), ("(true and false)", False), ("(true or false)", True),
    ("(if true then 1 else 2)", 1), ("(if false then 1 else 2)", 2), ("(if (1 < 2) then (3 + 4) else (5 + 6))", 7),
    ("(let x = 3 in (x * x))", 9), ("(let x = (1 + 2) in (x * x))", 9),
    # short circuit: the right side is not evaluated, so it may be stuck
    ("(false and (1 + true))", False), ("(false and x)", False), ("(true or (1 + true))", True), ("(true or x)", True),
    ("(if true then 1 else (1 + true))", 1), ("(if false then (1 + true) else 2)", 2), ("(if true then 3 else x)", 3),
    ("(let x = 1 in 5)", 5),
    # ill-typed but not stuck: the dynamic semantics just returns what the rules produce
    ("(true and 5)", 5), ("(false or 7)", 7),
    # shadowing and scope
    ("(let x = 1 in (let x = 2 in x))", 2),
    ("(let x = 1 in ((let x = 2 in x) + x))", 3),
    ("(let x = 5 in (let x = (x + 1) in x))", 6),
    ("(let x = 1 in (let y = (x + 1) in (let x = 10 in (x + y))))", 12),
    ("(let x = 1 in (let y = x in (let x = 2 in y)))", 1),
    ("(let x = 2 in (let y = (let x = 3 in (x * x)) in (x + y)))", 11),
    ("((let x = 1 in x) + (let x = 2 in x))", 3),
    ("(let x = true in (let x = (if x then 1 else 2) in x))", 1),
]


@pytest.mark.parametrize("src,expected", VALUES, ids=[s for s, _ in VALUES])
def test_evaluate_returns_the_python_value_with_the_right_type(src, expected):
    """evaluate returns an int for Int results and a real bool for Bool results (True != the int 1 here)."""
    got = evaluate(T(src))
    assert got == expected and type(got) is type(expected), f"{src}: got {got!r} ({type(got).__name__})"


STUCK = [
    "(1 + true)", "(true + 1)", "(true * true)", "(1 < true)", "(1 == true)", "(true == 1)", "(1 and true)", "(1 or true)", "(not 1)",
    "(if 1 then 2 else 3)", "x", "(x + 1)", "(let y = 1 in x)", "(let y = x in 1)", "(let x = (1 + true) in 5)", "((1 + true) + 2)",
    "(2 + (1 + true))", "((1 + true) and false)", "(false or (1 + true))", "(true and (1 + true))", "(true and x)", "(false or x)",
    "(if true then (1 + true) else 2)", "(let x = 1 in (let y = 2 in z))",
]


@pytest.mark.parametrize("src", STUCK)
def test_stuck_terms_raise_stuckerror_carrying_the_program(src):
    """Evaluation that cannot continue raises StuckError (not TypeError/KeyError/NameError); `.term` is the evaluated program."""
    e = T(src)
    with pytest.raises(StuckError) as ei:
        evaluate(e)
    assert ei.value.term == e


def test_arithmetic_is_exact_python_integers():
    """No overflow or float rounding: 30-digit operands multiply exactly, and 2**200 by repeated products stays exact."""
    big = 123456789012345678901234567890
    assert evaluate(BinOp("*", IntLit(big), IntLit(big))) == big * big
    e = IntLit(2)
    for _ in range(199):
        e = BinOp("*", IntLit(2), e)
    assert evaluate(e) == 2**200
    assert evaluate(BinOp("-", IntLit(0), IntLit(big))) == -big
    assert evaluate(BinOp("<", IntLit(big), IntLit(big + 1))) is True


def test_booleans_and_ints_are_never_conflated():
    """`1 == true` is stuck although Python says 1 == True; `evaluate` of an Int literal is never a bool and vice versa."""
    with pytest.raises(StuckError):
        evaluate(T("(1 == true)"))
    with pytest.raises(StuckError):
        evaluate(T("(0 == false)"))
    assert type(evaluate(IntLit(1))) is int and type(evaluate(BoolLit(True))) is bool
    assert type(evaluate(T("(1 == 1)"))) is bool


def test_evaluate_is_independent_of_step_and_trace(monkeypatch):
    """evaluate is the oracle the small-step functions are compared with, so it must not be implemented via step or trace."""
    def boom(*a, **k):
        raise AssertionError("evaluate must not call step/trace")
    monkeypatch.setattr(calc, "step", boom)
    monkeypatch.setattr(calc, "trace", boom)
    monkeypatch.setattr(calc, "classify", boom)
    assert evaluate(T("(let x = (1 + 2) in (if (x < 4) then (x * x) else 0))")) == 9
    with pytest.raises(StuckError):
        evaluate(T("(1 + true)"))


def test_variable_capture_is_impossible_because_only_values_are_bound():
    """`let y = x in ...` inside a scope that rebinds x later still sees the OUTER x's value: the binding is evaluated where it is written."""
    assert evaluate(T("(let x = 1 in (let y = x in (let x = 100 in (y + x))))")) == 101
    assert evaluate(T("(let x = 1 in (let f = (x + 1) in (let x = 50 in (f * x))))")) == 100


def test_deep_terms_evaluate_under_the_default_recursion_limit():
    """A 200-deep right-nested sum evaluates to 201 and a 200-deep chain of lets to its innermost binding."""
    assert evaluate(right_sum(200)) == 201
    e = calc.Var("x")
    for _ in range(200):
        e = calc.Let("x", IntLit(1), e)
    assert evaluate(e) == 1


@pytest.mark.parametrize("bad", ["1 + 2", 5, None])
def test_evaluate_rejects_non_exprs(bad):
    """Only an Expr is evaluated; a str is not parsed implicitly."""
    with pytest.raises(TypeError):
        evaluate(bad)
