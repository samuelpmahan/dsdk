"""Contract tests for dsdk.lang.formula_syntax: strict round-trip with logic.to_str, relaxed precedence, ambiguity, errors."""
import pytest
from hypothesis import given
from hypothesis import strategies as st

from dsdk.lang import LangError, LexError, ParseError, all_parses, parse_formula
from dsdk.logic import And, Const, Iff, Implies, Not, Or, Var, evaluate, is_valid, models, to_str, truth_table

from lang_helpers import formulas, relaxed_text

a, b, c, d = Var("a"), Var("b"), Var("c"), Var("d")
OPERAND = {"LPAREN", "TILDE", "NAME", "TRUE", "FALSE"}
OPS = {"AMP", "BAR", "ARROW", "IFF"}
STRICT_F = {"LPAREN", "NAME", "TRUE", "FALSE"}
STRICT_L = STRICT_F | {"TILDE"}
CATALAN = [1, 1, 2, 5, 14, 42]

STRICT_OK = [
    ("a", lambda: Var("a")),
    ("true", lambda: Const(True)),
    ("false", lambda: Const(False)),
    ("trueish", lambda: Var("trueish")),
    ("True", lambda: Var("True")),
    ("_x1", lambda: Var("_x1")),
    ("(~a)", lambda: Not(a)),
    ("(~(~a))", lambda: Not(Not(a))),
    ("(a & b)", lambda: And(a, b)),
    ("(a | b)", lambda: Or(a, b)),
    ("(a -> b)", lambda: Implies(a, b)),
    ("(a <-> b)", lambda: Iff(a, b)),
    ("((a & b) & c)", lambda: And(And(a, b), c)),
    ("(a & (b & c))", lambda: And(a, And(b, c))),
    ("((a & b) -> c)", lambda: Implies(And(a, b), c)),
    ("(a & (b | false))", lambda: And(a, Or(b, Const(False)))),
    ("(B11 <-> (P12 | P21))", lambda: Iff(Var("B11"), Or(Var("P12"), Var("P21")))),
    ("((~a) | (~b))", lambda: Or(Not(a), Not(b))),
    ("(~(a & b))", lambda: Not(And(a, b))),
    ("((a <-> b) <-> (c <-> d))", lambda: Iff(Iff(a, b), Iff(c, d))),
]


@pytest.mark.parametrize("text,build", STRICT_OK, ids=[t for t, _ in STRICT_OK])
def test_strict_accepts_canonical_strings(text, build):
    """Strict mode reads exactly what logic.to_str writes, and gives the structurally expected Formula (and to_str gives the text back)."""
    f = parse_formula(text)
    assert f == build(), f"{text!r} parsed to {f}"
    assert to_str(f) == text


# ------------------------------------------------------------------ strict mode rejects everything else, with exact errors
STRICT_BAD = [
    ("", 0, STRICT_F),
    (" ", 0, STRICT_F),
    ("1", 0, STRICT_F),
    ("~a", 0, STRICT_F),
    (" (a & b)", 0, STRICT_F),
    ("a & b", 1, {"END"}),
    ("a b", 1, {"END"}),
    ("a ", 1, {"END"}),
    ("(a)", 2, {"WS"}),
    ("(a&b)", 2, {"WS"}),
    ("(a  & b)", 2, {"WS"}),
    ("(a\t& b)", 2, {"WS"}),
    ("(a &b)", 4, {"WS"}),
    ("(a &  b)", 4, {"WS"}),
    ("( a & b)", 1, STRICT_L),
    ("(a & b )", 6, {"RPAREN"}),
    ("(a & b) ", 7, {"END"}),
    ("(a & b))", 7, {"END"}),
    ("(a & b) & c", 7, {"END"}),
    ("(a & b", 6, {"RPAREN"}),
    ("(a &", 4, {"WS"}),
    ("(a & ", 5, STRICT_F),
    ("(", 1, STRICT_L),
    ("()", 1, STRICT_L),
    ("(~", 2, STRICT_F),
    ("(~a", 3, {"RPAREN"}),
    ("(~ a)", 2, STRICT_F),
    ("(~~a)", 2, STRICT_F),
    ("((~a))", 5, {"WS"}),
    ("(a <- b)", 3, OPS),
    ("(a == b)", 3, OPS),
    ("(a and b)", 3, OPS),
    ("(a & b & c)", 6, {"RPAREN"}),
    ("(a -> b -> c)", 7, {"RPAREN"}),
]


@pytest.mark.parametrize("text,offset,expected", STRICT_BAD, ids=[repr(t) for t, _, _ in STRICT_BAD])
def test_strict_rejects_non_canonical_with_offset_and_expected(text, offset, expected):
    """Anything but the exact canonical grammar is a ParseError at the first offending token (or end of input), carrying what was expected there."""
    with pytest.raises(ParseError) as ei:
        parse_formula(text)
    assert ei.value.offset == offset, f"{text!r}: offset {ei.value.offset}, expected {offset}"
    assert ei.value.expected == frozenset(expected), f"{text!r}: expected-set {sorted(ei.value.expected)}"


def test_strict_is_the_default_and_relaxed_is_opt_in():
    """parse_formula(text) is strict; only relaxed=True accepts `a & b`."""
    with pytest.raises(ParseError):
        parse_formula("a & b")
    assert parse_formula("a & b", relaxed=True) == And(a, b)
    assert parse_formula("(a & b)") == parse_formula("(a & b)", relaxed=False) == And(a, b)


# ------------------------------------------------------------------ relaxed mode
RELAXED_OK = [
    ("a", "a"), ("  a  ", "a"), ("true", "true"), ("((a))", "a"), ("(((a & b)))", "(a & b)"), ("(~a)", "(~a)"),
    ("a & b", "(a & b)"), ("a&b", "(a & b)"), ("a|b", "(a | b)"), ("a->b", "(a -> b)"), ("a<->b", "(a <-> b)"),
    ("~a", "(~a)"), ("~ a", "(~a)"), ("~~a", "(~(~a))"), ("~(a)", "(~a)"), ("~(a & b)", "(~(a & b))"),
    ("~a & b", "((~a) & b)"), ("~a | ~b", "((~a) | (~b))"), ("~a -> b", "((~a) -> b)"),
    ("a | b & c", "(a | (b & c))"), ("a & b | c", "((a & b) | c)"),
    ("a & b & c", "((a & b) & c)"), ("a | b | c", "((a | b) | c)"),
    ("a -> b -> c", "(a -> (b -> c))"), ("a <-> b <-> c", "((a <-> b) <-> c)"),
    ("a -> b | c", "(a -> (b | c))"), ("a | b -> c", "((a | b) -> c)"),
    ("a <-> b -> c", "(a <-> (b -> c))"), ("a -> b <-> c", "((a -> b) <-> c)"),
    ("a & b -> c | d <-> e", "(((a & b) -> (c | d)) <-> e)"),
    ("(a -> b) -> c", "((a -> b) -> c)"), ("a -> (b -> c)", "(a -> (b -> c))"),
    ("(a & b) & c", "((a & b) & c)"), ("a & (b & c)", "(a & (b & c))"),
    ("B11 <-> P12 | P21", "(B11 <-> (P12 | P21))"),
    ("\ta\n&\r\nb ", "(a & b)"), ("true & false", "(true & false)"), ("trueish & falsey", "(trueish & falsey)"),
    ("~true", "(~true)"), ("if & then", "(if & then)"), ("let -> in", "(let -> in)"),
    ("a|b&c->d<->e", "(((a | (b & c)) -> d) <-> e)"),
]


@pytest.mark.parametrize("text,canonical", RELAXED_OK, ids=[t for t, _ in RELAXED_OK])
def test_relaxed_precedence_and_associativity(text, canonical):
    """Relaxed mode applies ~ > & > | > -> > <->, with -> right-associative and & | <-> left-associative; the result printed canonically pins the tree."""
    assert to_str(parse_formula(text, relaxed=True)) == canonical


def test_implication_is_right_associative_and_it_matters():
    """`a -> b -> c` is a -> (b -> c): the other grouping is a DIFFERENT formula (they disagree at a=F,b=F,c=F), so the choice is not cosmetic."""
    f = parse_formula("a -> b -> c", relaxed=True)
    assert f == Implies(a, Implies(b, c))
    other = Implies(Implies(a, b), c)
    assert f != other
    env = {"a": False, "b": False, "c": False}
    assert evaluate(f, env) is True and evaluate(other, env) is False


def test_and_or_iff_associativity_is_a_convention_not_semantics():
    """For & | <-> left vs right grouping gives equal truth tables (they are associative), so choosing left-associativity cannot change meaning."""
    for cls in (And, Or, Iff):
        left, right = cls(cls(a, b), c), cls(a, cls(b, c))
        assert left != right
        assert is_valid(Iff(left, right)), f"{cls.__name__} should be associative as a truth function"
    assert parse_formula("a <-> b <-> c", relaxed=True) == Iff(Iff(a, b), c)


def test_not_binds_tighter_than_everything():
    """`~a & b` is (~a) & b, never ~(a & b); the two differ at a=T,b=F."""
    f = parse_formula("~a & b", relaxed=True)
    assert f == And(Not(a), b)
    assert evaluate(f, {"a": True, "b": False}) is False and evaluate(Not(And(a, b)), {"a": True, "b": False}) is True


def test_relaxed_accepts_every_canonical_string_identically():
    """Relaxed is a superset of strict: for canonical text both modes give the same Formula."""
    for text, build in STRICT_OK:
        assert parse_formula(text, relaxed=True) == parse_formula(text) == build()


# ------------------------------------------------------------------ relaxed errors
AFTER0 = OPS | {"END"}
AFTERP = OPS | {"RPAREN"}
RELAXED_BAD = [
    ("", 0, OPERAND), ("   ", 3, OPERAND), ("&", 0, OPERAND), ("<->", 0, OPERAND), ("1", 0, OPERAND),
    ("a &", 3, OPERAND), ("a -> ", 5, OPERAND), ("a & & b", 4, OPERAND), ("~", 1, OPERAND), ("(", 1, OPERAND), ("()", 1, OPERAND),
    ("a b", 2, AFTER0), ("a)", 1, AFTER0), ("a ~ b", 2, AFTER0), ("a 1", 2, AFTER0),
    ("a < b", 2, AFTER0), ("a <- b", 2, AFTER0), ("a - b", 2, AFTER0), ("a == b", 2, AFTER0), ("a = b", 2, AFTER0),
    ("(a", 2, AFTERP), ("(a b)", 3, AFTERP), ("((a)", 4, AFTERP), ("(a & b", 6, AFTERP),
    ("(a & b))", 7, AFTER0),
]


@pytest.mark.parametrize("text,offset,expected", RELAXED_BAD, ids=[repr(t) for t, _, _ in RELAXED_BAD])
def test_relaxed_errors_carry_offset_and_expected_set(text, offset, expected):
    """Relaxed ParseErrors point at the first offending token (or the end) and list the token kinds the grammar would accept there; 'END' marks 'end of input allowed'."""
    with pytest.raises(ParseError) as ei:
        parse_formula(text, relaxed=True)
    assert ei.value.offset == offset, f"{text!r}: offset {ei.value.offset}, expected {offset}"
    assert ei.value.expected == frozenset(expected), f"{text!r}: expected-set {sorted(ei.value.expected)}"


@pytest.mark.parametrize("relaxed", [False, True])
@pytest.mark.parametrize(
    "text,offset",
    [("a @ b", 2), ("é", 0), ("(a & b) é", 8), ("a ∧ b", 2), ("a ->> b", 4), ("٣", 0), ("a & b", 1), ("a & ｂ", 4)],
)
def test_lex_errors_surface_as_lexerror_with_offset(relaxed, text, offset):
    """Illegal characters (including Unicode look-alikes) raise LexError with their index in both modes; LexError is a LangError but not a ParseError."""
    with pytest.raises(LexError) as ei:
        parse_formula(text, relaxed=relaxed)
    assert ei.value.offset == offset and isinstance(ei.value, LangError) and not isinstance(ei.value, ParseError)


@pytest.mark.parametrize("relaxed", [False, True])
def test_lexing_happens_before_parsing(relaxed):
    """`a a @` has a parse error at 2 and a lex error at 4; the whole text is tokenized first, so the LexError wins."""
    with pytest.raises(LexError) as ei:
        parse_formula("a a @", relaxed=relaxed)
    assert ei.value.offset == 4


@pytest.mark.parametrize("relaxed", [False, True])
@pytest.mark.parametrize("bad", [None, 5, b"a", ["a"]])
def test_non_string_is_typeerror(relaxed, bad):
    """parse_formula only takes str."""
    with pytest.raises(TypeError):
        parse_formula(bad, relaxed=relaxed)


# ------------------------------------------------------------------ the ambiguity lesson
def test_without_precedence_a_or_b_and_c_has_two_parse_trees():
    """A grammar with no precedence gives `a | b & c` two trees, in the documented order (root `|` first)."""
    assert all_parses("a | b & c") == [Or(a, And(b, c)), And(Or(a, b), c)]


def test_the_two_trees_have_different_truth_tables_so_ambiguity_is_a_real_bug():
    """The two readings of `a | b & c` disagree on a model (a=T,b=F,c=F), so a parser must pick one: precedence is what picks it."""
    first, second = all_parses("a | b & c")
    assert truth_table(first) != truth_table(second)
    env = {"a": True, "b": False, "c": False}
    assert evaluate(first, env) is True and evaluate(second, env) is False
    assert list(models(first)) != list(models(second))


def test_relaxed_mode_picks_the_conventional_tree_of_the_two():
    """Precedence resolves the ambiguity: `&` binds tighter, so relaxed gives the FIRST tree (a | (b & c))."""
    assert parse_formula("a | b & c", relaxed=True) == all_parses("a | b & c")[0]
    assert parse_formula("a & b | c", relaxed=True) == all_parses("a & b | c")[1]


def test_all_parses_order_and_mixed_operators():
    """Root operator index goes left to right; for each root, left trees vary slowest then right trees."""
    assert all_parses("a -> b <-> c") == [Implies(a, Iff(b, c)), Iff(Implies(a, b), c)]
    got = all_parses("a & b & c & d")
    assert got[0] == And(a, And(b, And(c, d)))
    assert got[1] == And(a, And(And(b, c), d))
    assert got[2] == And(And(a, b), And(c, d))
    assert got[3] == And(And(a, And(b, c)), d)
    assert got[4] == And(And(And(a, b), c), d)
    assert len(got) == 5


@pytest.mark.parametrize("k", range(6))
def test_number_of_parse_trees_is_catalan(k):
    """With k operators and no precedence there are Catalan(k) distinct trees (1,1,2,5,14,42): the combinatorial cost of ambiguity."""
    text = " | ".join(["a"] * (k + 1))
    got = all_parses(text)
    assert len(got) == CATALAN[k] == len(set(got))


@pytest.mark.parametrize("text", ["a &", "~a", "(a)", "", "& a", "a b", "a & & b", "a -> ~b"])
def test_all_parses_rejects_anything_but_atoms_and_binary_operators(text):
    """The precedence-free grammar has no ~ and no parentheses; other shapes are ParseErrors."""
    with pytest.raises(ParseError):
        all_parses(text)


def test_all_parses_lex_error():
    """Illegal characters are LexErrors here too."""
    with pytest.raises(LexError) as ei:
        all_parses("a ∧ b")
    assert ei.value.offset == 2


_atoms = st.sampled_from(["a", "b", "c", "true", "false"])
_binops = st.sampled_from(["&", "|", "->", "<->"])


@given(st.integers(0, 4).flatmap(lambda k: st.tuples(st.lists(_atoms, min_size=k + 1, max_size=k + 1), st.lists(_binops, min_size=k, max_size=k))))
def test_relaxed_parse_is_always_one_of_the_precedence_free_parses(case):
    """For `atom op atom op ...` the relaxed parser returns exactly one of the Catalan(k) readings: precedence selects, never invents."""
    atoms, ops = case
    text = atoms[0] + "".join(f" {o} {x}" for o, x in zip(ops, atoms[1:]))
    options = all_parses(text)
    assert len(options) == CATALAN[len(ops)]
    assert parse_formula(text, relaxed=True) in options


# ------------------------------------------------------------------ properties: round-trips
@given(formulas())
def test_strict_parse_inverts_to_str(f):
    """parse_formula(to_str(f)) == f for every Formula: nothing is lost or reassociated by printing and reading."""
    assert parse_formula(to_str(f)) == f


@given(formulas())
def test_to_str_inverts_strict_parse_on_canonical_strings(f):
    """to_str(parse_formula(s)) == s for canonical s (the other half of the round trip)."""
    s = to_str(f)
    assert to_str(parse_formula(s)) == s


@given(formulas())
def test_relaxed_agrees_with_strict_on_canonical_text(f):
    """Relaxed mode is a conservative extension of strict mode."""
    assert parse_formula(to_str(f), relaxed=True) == f


@given(formulas(max_leaves=10), st.lists(st.sampled_from(["", " ", "  ", "\t", "\n", " \r\n "]), min_size=1, max_size=4))
def test_minimal_parenthesis_text_with_random_whitespace_parses_back(f, spacing):
    """An independent minimal-parenthesis printer (using the documented precedences) plus arbitrary whitespace parses back to the same tree in relaxed mode."""
    text = relaxed_text(f, spacing)
    assert parse_formula(text, relaxed=True) == f, f"{text!r}"


@given(formulas(max_leaves=10))
def test_strict_rejects_everything_that_is_not_canonical(f):
    """Minimal-parenthesis text that differs from to_str(f) must be rejected by strict mode (only canonical text is accepted)."""
    text = relaxed_text(f, [" "])
    if text != to_str(f):
        with pytest.raises(ParseError):
            parse_formula(text)


@given(formulas(max_leaves=10))
def test_relaxed_parse_preserves_meaning_of_logic_semantics(f):
    """Parsing the canonical text of f and evaluating agrees with evaluating f itself on all-true and all-false assignments (smoke link to dsdk.logic)."""
    g = parse_formula(to_str(f), relaxed=True)
    for v in (True, False):
        env = {"a": v, "b": v, "c": v}
        assert evaluate(g, env) is evaluate(f, env)


# ------------------------------------------------------------------ depth
def test_deep_nesting_does_not_hit_the_recursion_limit():
    """200 levels of ~, parentheses, left chains and right chains parse in both modes under the default recursion limit."""
    deep_not = Var("a")
    deep_and = Var("a")
    for _ in range(200):
        deep_not = Not(deep_not)
        deep_and = And(deep_and, Var("a"))
    assert parse_formula(to_str(deep_not)) == deep_not
    assert parse_formula(to_str(deep_and)) == deep_and
    assert parse_formula("~" * 200 + "a", relaxed=True) == deep_not
    assert parse_formula("(" * 200 + "a" + ")" * 200, relaxed=True) == a
    assert parse_formula(" & ".join(["a"] * 201), relaxed=True) == deep_and
    chain = a
    for _ in range(200):
        chain = Implies(a, chain)
    assert parse_formula(" -> ".join(["a"] * 201), relaxed=True) == chain
    assert parse_formula(to_str(chain)) == chain
