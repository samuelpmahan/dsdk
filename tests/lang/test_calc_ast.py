"""Contract tests for the Calc AST: validation, structural equality, size, free variables, substitution, values, canonical source."""
import dataclasses

import pytest

from dsdk import logic
from dsdk.lang.calc import (
    OPS, BinOp, BoolLit, Expr, If, IntLit, Let, Not, Var, free_vars, from_python, is_value, size, substitute, to_python,
    to_source,
)

from lang_helpers import T, left_sum, right_sum, show

# ------------------------------------------------------------------ construction rules
@pytest.mark.parametrize("v", [0, 1, -1, 10**30, -(10**30)])
def test_intlit_accepts_any_int(v):
    """IntLit holds an exact Python int of any sign and size."""
    assert IntLit(v).value == v


@pytest.mark.parametrize("bad", [True, False, 1.0, "1", None, (1,)])
def test_intlit_rejects_non_int_including_bool(bad):
    """IntLit(True) would make IntLit(1) == IntLit(True) by Python equality; bool is rejected with TypeError."""
    with pytest.raises(TypeError):
        IntLit(bad)


@pytest.mark.parametrize("bad", [1, 0, None, "true", 1.0])
def test_boollit_requires_a_real_bool(bad):
    """BoolLit(1) is a TypeError: only True/False."""
    with pytest.raises(TypeError):
        BoolLit(bad)


@pytest.mark.parametrize("name", ["x", "_", "x1", "_a_b", "True", "TRUE", "letx", "ifx", "android", "Not", "iff", "t"])
def test_var_accepts_identifiers_that_are_not_keywords(name):
    """ASCII identifiers are fine; near-keywords (`letx`, `Not`, `android`, `iff`) are not keywords."""
    assert Var(name).name == name


@pytest.mark.parametrize(
    "name", ["", "1a", "a b", "a-b", "é", "a\n", " x", "true", "false", "let", "in", "if", "then", "else", "and", "or", "not", "x.y", "a(b"]
)
def test_var_rejects_bad_names_and_keywords(name):
    """Anything outside [A-Za-z_][A-Za-z0-9_]* or equal to a Calc keyword is a ValueError (else to_source would not parse back)."""
    with pytest.raises(ValueError):
        Var(name)


@pytest.mark.parametrize("bad", [None, 1, b"x", ("x",)])
def test_var_name_must_be_str(bad):
    """A non-str name is a TypeError, distinct from a malformed str."""
    with pytest.raises(TypeError):
        Var(bad)


@pytest.mark.parametrize("op", OPS)
def test_binop_accepts_each_operator(op):
    """The seven operators + - * < == and or are the whole set."""
    assert BinOp(op, IntLit(1), IntLit(2)).op == op


def test_ops_constant_lists_the_seven_operators():
    """OPS is the exact operator tuple in the documented order."""
    assert OPS == ("+", "-", "*", "<", "==", "and", "or")
    assert [BinOp(op, IntLit(1), IntLit(2)).op for op in OPS] == list(OPS)


@pytest.mark.parametrize("op", ["/", "<=", "&&", "AND", "", "not", "=", "->", None])
def test_binop_rejects_unknown_operators(op):
    """An operator outside OPS is a ValueError (None included: it is simply not one of them)."""
    with pytest.raises(ValueError):
        BinOp(op, IntLit(1), IntLit(2))


def test_children_must_be_exprs():
    """Every child slot is type-checked: strings, ints, None and even logic Formulas are TypeErrors."""
    one = IntLit(1)
    for bad in ["x", 1, None, True, logic.Var("a")]:
        with pytest.raises(TypeError):
            BinOp("+", bad, one)
        with pytest.raises(TypeError):
            BinOp("+", one, bad)
        with pytest.raises(TypeError):
            Not(bad)
        with pytest.raises(TypeError):
            If(bad, one, one)
        with pytest.raises(TypeError):
            If(one, bad, one)
        with pytest.raises(TypeError):
            If(one, one, bad)
        with pytest.raises(TypeError):
            Let("x", bad, one)
        with pytest.raises(TypeError):
            Let("x", one, bad)


def test_let_name_is_validated_like_var_name():
    """`let if = 1 in 2` cannot be represented: keyword and malformed binder names are ValueError, non-str is TypeError."""
    one = IntLit(1)
    with pytest.raises(ValueError):
        Let("if", one, one)
    with pytest.raises(ValueError):
        Let("1x", one, one)
    with pytest.raises(TypeError):
        Let(5, one, one)
    assert Let("x", one, one).name == "x"


def test_every_node_class_is_an_expr_subclass():
    """Every concrete node class derives from Expr (parsers and checkers dispatch on that)."""
    for node in (IntLit(1), BoolLit(True), Var("x"), BinOp("+", IntLit(1), IntLit(2)), Not(BoolLit(True)),
                 If(BoolLit(True), IntLit(1), IntLit(2)), Let("x", IntLit(1), Var("x"))):
        assert isinstance(node, Expr)


# ------------------------------------------------------------------ equality / immutability
def test_equality_is_structural_and_class_sensitive():
    """IntLit(1) != BoolLit(True); operand order matters; no normalisation (a+b != b+a, (a+b)+c != a+(b+c))."""
    assert IntLit(1) != BoolLit(True)
    assert IntLit(1) == IntLit(1)
    a, b, c = Var("a"), Var("b"), Var("c")
    assert BinOp("+", a, b) != BinOp("+", b, a)
    assert BinOp("+", BinOp("+", a, b), c) != BinOp("+", a, BinOp("+", b, c))
    assert BinOp("+", a, b) != BinOp("-", a, b)
    assert Let("x", a, b) != Let("y", a, b)
    assert BinOp("+", a, b) == BinOp("+", Var("a"), Var("b"))


def test_nodes_are_hashable_and_usable_in_sets():
    """Equal nodes hash equal; this is what lets traces and caches key on terms."""
    e1, e2 = T("(let x = 1 in (x + 2))"), T("(let x = 1 in (x + 2))")
    assert e1 == e2 and hash(e1) == hash(e2)
    assert len({e1, e2, IntLit(3)}) == 2


def test_nodes_are_frozen():
    """Assigning to a node raises FrozenInstanceError (immutable AST)."""
    n = IntLit(1)
    with pytest.raises(dataclasses.FrozenInstanceError):
        n.value = 2
    v = Var("x")
    with pytest.raises(dataclasses.FrozenInstanceError):
        v.name = "y"


# ------------------------------------------------------------------ size
@pytest.mark.parametrize(
    "src,expected",
    [("1", 1), ("true", 1), ("x", 1), ("(1 + 2)", 3), ("(not true)", 2), ("(if true then 1 else 2)", 4),
     ("(let x = 1 in x)", 3), ("(let x = (1 + 2) in (x * x))", 7), ("((1 + 2) + (3 + 4))", 7), ("(a and a)", 3)],
)
def test_size_counts_nodes_with_repetition(src, expected):
    """size is the tree size (every occurrence counts; the let binder is not a node)."""
    assert size(T(src)) == expected


def test_size_of_deep_terms_under_default_recursion_limit():
    """Depth 200 works: right_sum(200) has 401 nodes."""
    assert size(right_sum(200)) == 401 and size(left_sum(200)) == 401


# ------------------------------------------------------------------ free variables
@pytest.mark.parametrize(
    "src,expected",
    [("1", set()), ("x", {"x"}), ("(x + y)", {"x", "y"}), ("(let x = 1 in x)", set()), ("(let x = 1 in y)", {"y"}),
     ("(let x = x in x)", {"x"}), ("(let x = 1 in (let y = x in (y + z)))", {"z"}),
     ("((let x = 1 in x) + x)", {"x"}), ("(if a then b else c)", {"a", "b", "c"}), ("(not p)", {"p"})],
)
def test_free_vars(src, expected):
    """A let binds its name only in the BODY: the bound expression sees the outer scope, so `let x = x in x` still has x free."""
    assert free_vars(T(src)) == frozenset(expected)


# ------------------------------------------------------------------ substitution
@pytest.mark.parametrize(
    "src,name,val,expected",
    [
        ("x", "x", "5", "5"),
        ("y", "x", "5", "y"),
        ("(x + x)", "x", "5", "(5 + 5)"),
        ("(x + y)", "x", "true", "(true + y)"),
        ("(let x = 1 in x)", "x", "9", "(let x = 1 in x)"),
        ("(let x = x in x)", "x", "9", "(let x = 9 in x)"),
        ("(let y = x in (y + x))", "x", "9", "(let y = 9 in (y + 9))"),
        ("(let y = 1 in (y + x))", "y", "9", "(let y = 1 in (y + x))"),
        ("((let x = 2 in x) + x)", "x", "1", "((let x = 2 in x) + 1)"),
        ("(if x then x else x)", "x", "false", "(if false then false else false)"),
        ("(not x)", "x", "true", "(not true)"),
        ("(let x = 1 in (let x = 2 in x))", "x", "0", "(let x = 1 in (let x = 2 in x))"),
        ("(let y = 1 in (let x = 2 in x))", "x", "0", "(let y = 1 in (let x = 2 in x))"),
        ("(let y = 1 in (let x = 2 in (x + y)))", "y", "7", "(let y = 1 in (let x = 2 in (x + y)))"),
        ("(let y = x in (let x = 2 in (x + y)))", "x", "7", "(let y = 7 in (let x = 2 in (x + y)))"),
    ],
)
def test_substitute_respects_shadowing(src, name, val, expected):
    """substitute replaces FREE occurrences only: the bound expression of a let is always searched, its body only if the binder differs from `name`."""
    assert substitute(T(src), name, T(val)) == T(expected), f"substitute({src}, {name}, {val})"


def test_substitute_returns_equal_term_when_name_not_free_and_leaves_input_alone():
    """Substituting an absent name is the identity (by equality); the input node is immutable anyway."""
    e = T("(let x = (1 + y) in (x * x))")
    assert substitute(e, "z", IntLit(3)) == e
    assert e == T("(let x = (1 + y) in (x * x))")


def test_substitute_only_takes_closed_values_so_capture_cannot_happen():
    """Only IntLit/BoolLit may be substituted (TypeError otherwise): a Var would be capturable under a binder, a literal never is."""
    e = T("(let y = 1 in x)")
    for bad in (Var("y"), T("(1 + 2)"), 5, None):
        with pytest.raises(TypeError):
            substitute(e, "x", bad)
    assert substitute(e, "x", IntLit(5)) == T("(let y = 1 in 5)")


def test_substitute_argument_types():
    """Non-Expr term and non-str name are TypeErrors."""
    with pytest.raises(TypeError):
        substitute("x", "x", IntLit(1))
    with pytest.raises(TypeError):
        substitute(Var("x"), 5, IntLit(1))


def test_substitute_on_a_deep_term():
    """Depth 200 under the default recursion limit; every `x` leaf is replaced."""
    e = Var("x")
    for _ in range(200):
        e = BinOp("+", e, Var("x"))
    got = substitute(e, "x", IntLit(1))
    assert got == left_sum(200)


# ------------------------------------------------------------------ values
def test_is_value():
    """Exactly the two literal node types are values; a variable is not."""
    assert is_value(IntLit(0)) and is_value(BoolLit(False))
    assert not is_value(Var("x")) and not is_value(T("(1 + 2)")) and not is_value(Not(BoolLit(True)))


def test_to_python_and_from_python():
    """Values convert to Python int/bool and back, keeping bool and int apart (bool is checked first)."""
    assert to_python(IntLit(3)) == 3 and type(to_python(IntLit(3))) is int
    assert to_python(BoolLit(True)) is True
    assert from_python(True) == BoolLit(True) and from_python(1) == IntLit(1) and from_python(0) == IntLit(0)
    assert from_python(False) == BoolLit(False) and from_python(-7) == IntLit(-7)
    assert to_python(from_python(10**40)) == 10**40


@pytest.mark.parametrize("bad", [1.5, None, "1", [1]])
def test_from_python_rejects_non_int_non_bool(bad):
    """Floats, None and strings are not Calc values."""
    with pytest.raises(TypeError):
        from_python(bad)


def test_to_python_rejects_non_values():
    """A non-value Expr is a ValueError and a non-Expr is a TypeError."""
    with pytest.raises(ValueError):
        to_python(Var("x"))
    with pytest.raises(ValueError):
        to_python(T("(1 + 2)"))
    with pytest.raises(TypeError):
        to_python(3)


@pytest.mark.parametrize("fn", [size, free_vars, to_source, is_value])
@pytest.mark.parametrize("bad", [3, "x", None, logic.Var("a")])
def test_structural_functions_reject_non_exprs(fn, bad):
    """Passing a non-Expr (including a logic Formula) is a TypeError, not an AttributeError or a silent answer."""
    with pytest.raises(TypeError):
        fn(bad)


# ------------------------------------------------------------------ canonical source
@pytest.mark.parametrize(
    "e,src",
    [
        (lambda: IntLit(3), "3"), (lambda: IntLit(0), "0"), (lambda: IntLit(-3), "-3"), (lambda: IntLit(10**25), "10000000000000000000000000"),
        (lambda: BoolLit(True), "true"), (lambda: BoolLit(False), "false"), (lambda: Var("x"), "x"),
        (lambda: BinOp("+", IntLit(1), IntLit(2)), "(1 + 2)"), (lambda: BinOp("-", IntLit(1), IntLit(-2)), "(1 - -2)"),
        (lambda: BinOp("*", IntLit(-1), Var("x")), "(-1 * x)"), (lambda: BinOp("<", Var("a"), Var("b")), "(a < b)"),
        (lambda: BinOp("==", Var("a"), Var("b")), "(a == b)"), (lambda: BinOp("and", Var("a"), Var("b")), "(a and b)"),
        (lambda: BinOp("or", Var("a"), Var("b")), "(a or b)"), (lambda: Not(Var("a")), "(not a)"),
        (lambda: Not(Not(BoolLit(True))), "(not (not true))"),
        (lambda: If(Var("c"), IntLit(1), IntLit(2)), "(if c then 1 else 2)"),
        (lambda: Let("x", IntLit(1), BinOp("+", Var("x"), IntLit(1))), "(let x = 1 in (x + 1))"),
        (lambda: BinOp("+", BinOp("+", IntLit(1), IntLit(2)), IntLit(3)), "((1 + 2) + 3)"),
        (lambda: BinOp("+", IntLit(1), BinOp("+", IntLit(2), IntLit(3))), "(1 + (2 + 3))"),
    ],
)
def test_to_source_is_fully_parenthesised_canonical_text(e, src):
    """to_source prints with single spaces and parentheses around every compound node; the exact text is the cross-language format."""
    assert to_source(e()) == src


def test_to_source_matches_the_independent_printer_on_a_deep_term():
    """Depth 200 prints without recursion errors and agrees with the test-suite's own printer."""
    e = right_sum(200)
    assert to_source(e) == show(e)
    assert to_source(e).count("(") == 200
