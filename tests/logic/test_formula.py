"""Contract tests for dsdk.logic.formula: construction, equality/hashing, variables, size, canonical to_str."""
import copy
import dataclasses

import pytest
from hypothesis import given

from dsdk.logic import And, Const, Formula, Iff, Implies, Not, Or, Var, size, to_str, variables

from helpers import formulas, left_chain, not_chain, parse, ref_vars, right_chain

BINARIES = [And, Or, Implies, Iff]


# ---------------------------- construction rules ---------------------------
@pytest.mark.parametrize("value", [True, False])
def test_const_accepts_bool(value):
    """Const holds exactly a bool."""
    assert Const(value).value is value


@pytest.mark.parametrize("bad", [1, 0, None, "True", 1.0])
def test_const_rejects_non_bool(bad):
    """Const(1) would make Const(1) == Const(True) by Python equality and corrupt hashing; only real bools allowed."""
    with pytest.raises(TypeError):
        Const(bad)


@pytest.mark.parametrize("name", ["a", "P12", "_x", "x_1", "True", "False", "TRUE", "trueish", "B11"])
def test_var_accepts_identifier_names(name):
    """Names matching [A-Za-z_][A-Za-z0-9_]* are legal; 'True' (capitalised) and 'trueish' are not reserved."""
    assert Var(name).name == name


@pytest.mark.parametrize("name", ["", "1a", "a b", "a-b", "a.b", "é", "a(", " a", "a\n", "true", "false", "~a"])
def test_var_rejects_bad_names(name):
    """Anything outside the ASCII identifier grammar, or the reserved atoms true/false, is a ValueError (else to_str would not round-trip)."""
    with pytest.raises(ValueError):
        Var(name)


@pytest.mark.parametrize("bad", [None, 1, b"a", ("a",)])
def test_var_name_must_be_str(bad):
    """A non-str name is a TypeError (distinct from a malformed str)."""
    with pytest.raises(TypeError):
        Var(bad)


@pytest.mark.parametrize("bad", ["a", 1, None, True, ("a",)])
def test_operands_must_be_formulas(bad):
    """Every operand slot rejects non-Formula values with TypeError, so ill-formed trees cannot exist."""
    ok = Var("a")
    with pytest.raises(TypeError):
        Not(bad)
    for cls in BINARIES:
        with pytest.raises(TypeError):
            cls(bad, ok)
        with pytest.raises(TypeError):
            cls(ok, bad)


def test_all_node_types_are_formulas():
    """isinstance(x, Formula) must hold for every node class (used by checks elsewhere)."""
    a = Var("a")
    for node in (Const(True), a, Not(a), And(a, a), Or(a, a), Implies(a, a), Iff(a, a)):
        assert isinstance(node, Formula), f"{type(node).__name__} must subclass Formula"


def test_formulas_are_immutable():
    """Frozen: shared sub-trees must never change under their users."""
    n = Not(Var("a"))
    with pytest.raises(dataclasses.FrozenInstanceError):
        n.operand = Var("b")  # type: ignore[misc]
    with pytest.raises(dataclasses.FrozenInstanceError):
        Var("a").name = "b"  # type: ignore[misc]


# ---------------------------- equality and hashing -------------------------
def test_structurally_equal_formulas_are_equal_and_hash_equal():
    """Two separately built, structurally identical formulas are interchangeable as dict keys."""
    def build():
        return Implies(And(Var("a"), Not(Var("b"))), Or(Const(True), Var("c")))

    x, y = build(), build()
    assert x is not y and x == y and hash(x) == hash(y)
    assert len({x, y}) == 1 and {x: 1}[y] == 1


def test_equality_is_class_sensitive_and_order_sensitive():
    """No normalisation: And(a,b) != And(b,a), And != Or, grouping matters. (Semantic equivalence is is_valid(Iff(..)), not ==.)"""
    a, b, c = Var("a"), Var("b"), Var("c")
    assert And(a, b) != And(b, a)
    assert And(a, b) != Or(a, b)
    assert Implies(a, b) != Iff(a, b)
    assert And(And(a, b), c) != And(a, And(b, c))
    assert Not(Not(a)) != a
    assert Const(True) != Const(False)
    assert Var("a") != Var("b")


def test_const_and_var_never_equal_other_kinds():
    """Different node classes with 'similar' payloads must not collide: Const(True) vs Var('True') etc."""
    assert Const(True) != Var("True")
    assert Var("a") != Not(Var("a"))
    assert Const(True) != True  # noqa: E712  (a node is not a bool)


def test_deepcopy_preserves_equality_and_hash():
    """Copying must not break structural equality (guards against identity-based eq/hash)."""
    f = And(Var("a"), Not(Const(False)))
    g = copy.deepcopy(f)
    assert f == g and hash(f) == hash(g)


@given(formulas())
def test_property_equal_formulas_hash_equal(f):
    """For any f: a deep copy equals f and hashes the same; this is the hash/eq contract."""
    g = copy.deepcopy(f)
    assert f == g and hash(f) == hash(g), "equal formulas must have equal hashes"


# ---------------------------- variables ------------------------------------
def test_variables_basic():
    """variables returns a frozenset of the names occurring anywhere, without duplicates."""
    f = Iff(Var("B11"), Or(Var("P12"), And(Var("P12"), Not(Var("P21")))))
    v = variables(f)
    assert isinstance(v, frozenset)
    assert v == frozenset({"B11", "P12", "P21"})


def test_variables_of_const_only_formula_is_empty():
    """Degenerate: no Var nodes -> empty frozenset (not None, not error)."""
    assert variables(Const(True)) == frozenset()
    assert variables(Implies(Const(False), Not(Const(True)))) == frozenset()


@pytest.mark.parametrize("bad", ["a", None, 3])
def test_variables_rejects_non_formula(bad):
    """Passing a str instead of a Formula is a bug in the caller: TypeError."""
    with pytest.raises(TypeError):
        variables(bad)


@given(formulas())
def test_property_variables_matches_reference(f):
    """variables agrees with an independent naive traversal."""
    assert variables(f) == frozenset(ref_vars(f))


# ---------------------------- size -----------------------------------------
def test_size_counts_every_node_occurrence():
    """size is TREE size: shared sub-formulas are counted each time they occur."""
    a = Var("a")
    assert size(a) == 1 and size(Const(True)) == 1
    assert size(Not(a)) == 2
    assert size(And(a, a)) == 3, "repeated sub-formula counted twice"
    assert size(Iff(Not(a), Or(a, Const(False)))) == 1 + 2 + (1 + 1 + 1)
    for cls in BINARIES:
        assert size(cls(a, Not(a))) == 4


@pytest.mark.parametrize("bad", ["a", None])
def test_size_rejects_non_formula(bad):
    """Non-formulas are rejected with TypeError."""
    with pytest.raises(TypeError):
        size(bad)


# ---------------------------- canonical string -----------------------------
@pytest.mark.parametrize(
    "build, expected",
    [
        (lambda: Var("a"), "a"),
        (lambda: Const(True), "true"),
        (lambda: Const(False), "false"),
        (lambda: Not(Var("a")), "(~a)"),
        (lambda: Not(Not(Var("a"))), "(~(~a))"),
        (lambda: And(Var("a"), Var("b")), "(a & b)"),
        (lambda: Or(Var("a"), Var("b")), "(a | b)"),
        (lambda: Implies(Var("a"), Var("b")), "(a -> b)"),
        (lambda: Iff(Var("a"), Var("b")), "(a <-> b)"),
        (lambda: And(Var("a"), Or(Var("b"), Const(False))), "(a & (b | false))"),
        (lambda: Implies(And(Var("a"), Var("b")), Var("c")), "((a & b) -> c)"),
        (lambda: And(And(Var("a"), Var("b")), Var("c")), "((a & b) & c)"),
        (lambda: And(Var("a"), And(Var("b"), Var("c"))), "(a & (b & c))"),
        (lambda: Iff(Var("B11"), Or(Var("P12"), Var("P21"))), "(B11 <-> (P12 | P21))"),
        (lambda: Not(And(Var("a"), Not(Var("b")))), "(~(a & (~b)))"),
        (lambda: Var("True"), "True"),
    ],
)
def test_to_str_exact_canonical_form(build, expected):
    """to_str must produce exactly the canonical string (A2's parser round-trips it): fully parenthesised, ASCII, single spaces."""
    assert to_str(build()) == expected, f"canonical form of {expected!r} differs"


@pytest.mark.parametrize("bad", ["a", None])
def test_to_str_rejects_non_formula(bad):
    """Non-formulas are rejected with TypeError."""
    with pytest.raises(TypeError):
        to_str(bad)


@given(formulas())
def test_property_to_str_round_trips_through_reference_parser(f):
    """The grammar in the docstring is unambiguous: a strict reference parser recovers exactly f from to_str(f)."""
    assert parse(to_str(f)) == f


@given(formulas())
def test_property_to_str_balanced_and_only_operator_spaces(f):
    """Shape check: parentheses balance and the only spaces are the single ones around binary operators."""
    s = to_str(f)
    assert s.count("(") == s.count(")")
    assert " " not in s.replace(" & ", "").replace(" | ", "").replace(" -> ", "").replace(" <-> ", "")


# ---------------------------- deep nesting (depth 200 required) ------------
DEPTH = 200


def test_deep_not_chain_all_functions_work():
    """Depth 200 under the default recursion limit must work (implementations: prefer an explicit stack)."""
    f = not_chain(DEPTH, Var("a"))
    assert variables(f) == frozenset({"a"})
    assert size(f) == DEPTH + 1
    assert to_str(f) == "(~" * DEPTH + "a" + ")" * DEPTH


@pytest.mark.parametrize("chain", [left_chain, right_chain])
@pytest.mark.parametrize("cls", BINARIES)
def test_deep_binary_chains(chain, cls):
    """Left- and right-leaning binary chains of depth 200 for every connective."""
    f = chain(cls, DEPTH, Var("a"))
    assert size(f) == 2 * DEPTH + 1, "n applications: n operator nodes + (n+1) leaves"
    s = to_str(f)
    assert s.count("(") == DEPTH and s.count(")") == DEPTH
    assert variables(f) == frozenset({"a"})


def test_deep_formulas_support_equality_and_hash():
    """Structural equality and hashing of two separately-built depth-200 formulas must not overflow the stack."""
    f, g = not_chain(DEPTH, Var("a")), not_chain(DEPTH, Var("a"))
    assert f == g and hash(f) == hash(g)
    assert f != not_chain(DEPTH + 1, Var("a"))
