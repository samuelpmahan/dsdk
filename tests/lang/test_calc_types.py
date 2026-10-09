"""Contract tests for calc.typecheck: types as KNOWN Judgments, static errors as INVALID Judgments naming the offending node."""
from types import MappingProxyType

import pytest

from dsdk.core import Judgment, Status
from dsdk.lang.calc import BinOp, BoolLit, IntLit, Type, Var, typecheck

from lang_helpers import T, right_sum, show

INT, BOOL = Type.INT, Type.BOOL

WELL_TYPED = [
    ("1", INT), ("-7", INT), ("true", BOOL), ("(1 + 2)", INT), ("(1 - 2)", INT), ("((1 * 2) + 3)", INT), ("(1 < 2)", BOOL),
    ("(1 == 2)", BOOL), ("(true == false)", BOOL), ("((1 < 2) == (3 < 4))", BOOL), ("(not true)", BOOL),
    ("(true and false)", BOOL), ("(true or false)", BOOL), ("((1 < 2) and (not (2 < 1)))", BOOL),
    ("(if true then 1 else 2)", INT), ("(if (1 < 2) then true else false)", BOOL), ("(if true then (1 + 2) else (3 * 4))", INT),
    ("(let x = 1 in (x + 1))", INT), ("(let x = true in (if x then 1 else 2))", INT), ("(let x = 1 in (let y = (x < 2) in y))", BOOL),
    ("(let x = 1 in (let x = true in x))", BOOL),
    ("(let x = 1 in ((let x = true in x) == (x == 1)))", BOOL),
    ("(let x = 1 in (let x = (x + 1) in x))", INT),
    ("(if (let b = true in b) then (let n = 1 in n) else 2)", INT),
]


@pytest.mark.parametrize("src,ty", WELL_TYPED, ids=[s for s, _ in WELL_TYPED])
def test_well_typed_programs_are_known_with_their_type(src, ty):
    """A well-typed closed program is Judgment(KNOWN, Type) with empty reason; shadowing may change a variable's type inside its scope only."""
    j = typecheck(T(src))
    assert j == Judgment(Status.KNOWN, ty), f"{src}: {j}"


# (source, tag, source of the OFFENDING node)
ILL_TYPED = [
    ("(1 + true)", "operand type mismatch", "(1 + true)"),
    ("(true + 1)", "operand type mismatch", "(true + 1)"),
    ("(true * false)", "operand type mismatch", "(true * false)"),
    ("(1 - true)", "operand type mismatch", "(1 - true)"),
    ("(1 < true)", "operand type mismatch", "(1 < true)"),
    ("(true < false)", "operand type mismatch", "(true < false)"),
    ("(1 == true)", "operand type mismatch", "(1 == true)"),
    ("(true == 1)", "operand type mismatch", "(true == 1)"),
    ("(1 and true)", "operand type mismatch", "(1 and true)"),
    ("(true and 1)", "operand type mismatch", "(true and 1)"),
    ("(1 or 2)", "operand type mismatch", "(1 or 2)"),
    ("(not 1)", "operand type mismatch", "(not 1)"),
    ("(if 1 then 2 else 3)", "condition not Bool", "(if 1 then 2 else 3)"),
    ("(if true then 1 else false)", "branch type mismatch", "(if true then 1 else false)"),
    ("(if true then false else 1)", "branch type mismatch", "(if true then false else 1)"),
    ("x", "unbound variable", "x"),
    ("(x + 1)", "unbound variable", "x"),
    ("(let x = 1 in y)", "unbound variable", "y"),
    ("(let x = x in x)", "unbound variable", "x"),
    ("(let y = x in 1)", "unbound variable", "x"),
    ("((let x = 1 in x) + x)", "unbound variable", "x"),
    # children are checked before their parent, left to right
    ("((1 + true) + 2)", "operand type mismatch", "(1 + true)"),
    ("(1 + (true + 1))", "operand type mismatch", "(true + 1)"),
    ("((1 + true) + (false + 1))", "operand type mismatch", "(1 + true)"),
    ("(if 1 then (1 + true) else 2)", "operand type mismatch", "(1 + true)"),
    ("(if true then 1 else (not 5))", "operand type mismatch", "(not 5)"),
    ("(let x = (1 + true) in y)", "operand type mismatch", "(1 + true)"),
    ("(let x = 1 in (x + true))", "operand type mismatch", "(x + true)"),
    ("(not (1 + true))", "operand type mismatch", "(1 + true)"),
    # the If checks its condition before comparing branches
    ("(if 1 then true else 2)", "condition not Bool", "(if 1 then true else 2)"),
    # a variable's type follows the innermost binding
    ("(let x = 1 in (let x = true in (x + 1)))", "operand type mismatch", "(x + 1)"),
    ("(let x = true in (let x = 1 in (not x)))", "operand type mismatch", "(not x)"),
]


@pytest.mark.parametrize("src,tag,node", ILL_TYPED, ids=[s for s, _, _ in ILL_TYPED])
def test_ill_typed_programs_are_invalid_and_name_the_offending_node(src, tag, node):
    """A static type error is Judgment(INVALID, None, reason) with reason exactly `tag: source-of-the-offending-node`; the FIRST failure in left-to-right post-order is reported."""
    j = typecheck(T(src))
    assert j.status is Status.INVALID and j.value is None, f"{src}: {j}"
    assert j.reason == f"{tag}: {node}", f"{src}: got {j.reason!r}"


def test_known_value_is_a_type_member_not_a_string():
    """KNOWN carries a Type enum member, so `.value is Type.INT` (not 'Int')."""
    j = typecheck(IntLit(3))
    assert j.status is Status.KNOWN and j.value is Type.INT and j.reason == ""


def test_environment_supplies_free_variable_types():
    """env maps names to Types; a Var found there has that type, a missing one is unbound."""
    assert typecheck(Var("x"), {"x": BOOL}) == Judgment(Status.KNOWN, BOOL)
    assert typecheck(T("(x + y)"), {"x": INT, "y": INT}) == Judgment(Status.KNOWN, INT)
    assert typecheck(T("(x + y)"), {"x": INT}).reason == "unbound variable: y"
    assert typecheck(T("(x + 1)"), {"x": BOOL}).reason == "operand type mismatch: (x + 1)"
    assert typecheck(T("(let x = y in x)"), {"y": INT}) == Judgment(Status.KNOWN, INT)
    assert typecheck(T("(let y = true in y)"), {"y": INT}) == Judgment(Status.KNOWN, BOOL), "let shadows the environment"


def test_environment_is_not_mutated_and_let_does_not_leak():
    """typecheck never writes to env, and a let-bound name disappears after the let (env stays as given, outer x keeps its type)."""
    env = {"x": INT}
    typecheck(T("(let x = true in (let q = 1 in x))"), env)
    assert env == {"x": INT}
    assert typecheck(T("((let x = true in x) == (x < 3))"), env) == Judgment(Status.KNOWN, BOOL)
    assert typecheck(T("((let x = true in x) and (x < 3))"), env) == Judgment(Status.KNOWN, BOOL)
    assert typecheck(T("((let q = 1 in q) + q)"), env).reason == "unbound variable: q"


def test_environment_may_be_any_mapping_or_none():
    """None means empty, and a read-only mapping works."""
    assert typecheck(IntLit(1), None) == Judgment(Status.KNOWN, INT)
    assert typecheck(Var("x"), MappingProxyType({"x": INT})) == Judgment(Status.KNOWN, INT)


def test_static_type_error_is_not_the_same_as_getting_stuck():
    """typecheck says INVALID for BOTH `(1 + true)` and `(if true then 1 else (1 + true))`, even though only the first ever gets stuck: the checker is conservative (that is what soundness costs)."""
    assert typecheck(T("(1 + true)")).status is Status.INVALID
    assert typecheck(T("(if true then 1 else (1 + true))")).status is Status.INVALID


@pytest.mark.parametrize("bad", [3, "1 + 2", None, [1]])
def test_typecheck_rejects_non_exprs_with_typeerror(bad):
    """Only an Expr can be checked; a str is not parsed implicitly."""
    with pytest.raises(TypeError):
        typecheck(bad)


def test_never_raises_for_ill_typed_input():
    """Ill-typedness is reported through the Judgment, not by an exception."""
    assert typecheck(BinOp("+", BoolLit(True), BoolLit(True))).status is Status.INVALID


def test_deep_terms_typecheck_under_the_default_recursion_limit():
    """A 200-deep right-nested sum is Int; replacing its innermost leaf by `true` is reported at the innermost addition."""
    assert typecheck(right_sum(200)) == Judgment(Status.KNOWN, INT)
    e = BoolLit(True)
    for _ in range(200):
        e = BinOp("+", IntLit(1), e)
    j = typecheck(e)
    assert j.reason == "operand type mismatch: (1 + true)", "the innermost node is the first failure in post-order"
    assert show(e).startswith("(1 + (1 + ")
