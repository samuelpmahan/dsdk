"""Contract tests for parse_calc: precedence, associativity, negative literals, errors with offsets, round-trip, depth."""
import pytest
from hypothesis import given

from dsdk.lang import LangError, LexError, ParseError
from dsdk.lang.calc import BinOp, BoolLit, If, IntLit, Let, Not, Var, parse_calc, to_source

from lang_helpers import T, any_exprs, show

# (relaxed source, canonical source of the intended tree)
PARSE_OK = [
    ("1", "1"), ("  7  ", "7"), ("true", "true"), ("x", "x"), ("(((1)))", "1"), ("007", "7"),
    ("123456789012345678901234567890", "123456789012345678901234567890"),
    ("1 + 2", "(1 + 2)"), ("1+2", "(1 + 2)"), ("1 + 2 * 3", "(1 + (2 * 3))"), ("1 * 2 + 3", "((1 * 2) + 3)"),
    ("1 - 2 - 3", "((1 - 2) - 3)"), ("1 - 2 + 3", "((1 - 2) + 3)"), ("2 * 3 * 4", "((2 * 3) * 4)"),
    ("(1 + 2) * 3", "((1 + 2) * 3)"), ("1 + 2 < 3 + 4", "((1 + 2) < (3 + 4))"), ("1 + 2 == 3", "((1 + 2) == 3)"),
    ("a < b and c < d", "((a < b) and (c < d))"), ("a == b or c", "((a == b) or c)"),
    ("a or b and c", "(a or (b and c))"), ("a and b or c", "((a and b) or c)"),
    ("a or b or c", "((a or b) or c)"), ("a and b and c", "((a and b) and c)"),
    ("not a", "(not a)"), ("not not a", "(not (not a))"), ("not a and b", "((not a) and b)"),
    ("not a or b", "((not a) or b)"), ("not 1 < 2", "(not (1 < 2))"), ("not a == b", "(not (a == b))"),
    ("a and not b", "(a and (not b))"), ("(not a) and b", "((not a) and b)"), ("not (a and b)", "(not (a and b))"),
    ("-3", "-3"), ("- 3", "-3"), ("-0", "0"), ("1 - -2", "(1 - -2)"), ("1 -2", "(1 - 2)"), ("1--2", "(1 - -2)"),
    ("-1 + -2", "(-1 + -2)"), ("-2 * -3", "(-2 * -3)"), ("(-5)", "-5"), ("- 5 - - 5", "(-5 - -5)"),
    ("if a then b else c", "(if a then b else c)"),
    ("if a then b else c + 1", "(if a then b else (c + 1))"),
    ("if a then b + 1 else c", "(if a then (b + 1) else c)"),
    ("if a then if b then 1 else 2 else 3", "(if a then (if b then 1 else 2) else 3)"),
    ("if a then 1 else if b then 2 else 3", "(if a then 1 else (if b then 2 else 3))"),
    ("if x < 1 then 2 else 3", "(if (x < 1) then 2 else 3)"),
    ("(if a then 1 else 2) + 3", "((if a then 1 else 2) + 3)"),
    ("let x = 1 in x", "(let x = 1 in x)"),
    ("let x = 1 in x + 1", "(let x = 1 in (x + 1))"),
    ("let x = 1 + 2 in x * x", "(let x = (1 + 2) in (x * x))"),
    ("let x = 1 in let y = 2 in x + y", "(let x = 1 in (let y = 2 in (x + y)))"),
    ("let x = let y = 1 in y in x", "(let x = (let y = 1 in y) in x)"),
    ("(let x = 1 in x) + x", "((let x = 1 in x) + x)"),
    ("let x = if a then 1 else 2 in x", "(let x = (if a then 1 else 2) in x)"),
    ("let x = 1 in if x < 2 then 3 else 4", "(let x = 1 in (if (x < 2) then 3 else 4))"),
    ("letx", "letx"), ("iff", "iff"), ("android", "android"), ("Not", "Not"), ("True", "True"), ("trueish", "trueish"), ("_", "_"),
    ("true == false", "(true == false)"),
    ("\n\t1\r\n+\n2 ", "(1 + 2)"),
    ("(1 < 2) == true", "((1 < 2) == true)"),
    ("let x = 5 in let x = x + 1 in x", "(let x = 5 in (let x = (x + 1) in x))"),
]


@pytest.mark.parametrize("src,canonical", PARSE_OK, ids=[s for s, _ in PARSE_OK])
def test_parse_builds_the_intended_tree(src, canonical):
    """Precedence (or < and < not < comparison < + - < *) and left-associativity decide the tree; compared with an independently read canonical form."""
    assert parse_calc(src) == T(canonical), f"{src!r} should read as {canonical}"


def test_not_binds_looser_than_comparison_and_tighter_than_and():
    """`not true and false` is (not true) and false = false, while not (true and false) = true: a precedence slip changes the answer."""
    assert parse_calc("not true and false") == BinOp("and", Not(BoolLit(True)), BoolLit(False))
    assert parse_calc("not true and false") != Not(BinOp("and", BoolLit(True), BoolLit(False)))
    assert parse_calc("not 1 < 2") == Not(BinOp("<", IntLit(1), IntLit(2)))


def test_comparison_is_non_associative():
    """`1 < 2 < 3` and `1 == 2 == 3` and `1 < 2 == true` are rejected (compare results are not chained)."""
    for src in ["1 < 2 < 3", "1 == 2 == 3", "1 < 2 == true", "a == b < c"]:
        with pytest.raises(ParseError):
            parse_calc(src)
    assert parse_calc("(1 < 2) < 3") == BinOp("<", BinOp("<", IntLit(1), IntLit(2)), IntLit(3)), "parse accepts it; the type checker will not"


def test_negative_literals_only_in_operand_position():
    """`-3` after an operator is a literal, after an operand it is subtraction: `1 -2` is 1 - 2, `1 - -2` has a negative literal."""
    assert parse_calc("1 -2") == BinOp("-", IntLit(1), IntLit(2))
    assert parse_calc("1 - -2") == BinOp("-", IntLit(1), IntLit(-2))
    assert parse_calc("-1 -2") == BinOp("-", IntLit(-1), IntLit(2))
    assert parse_calc("-0") == IntLit(0)


def test_big_integers_are_exact():
    """Integer literals are parsed with int(): no float rounding for 30 digits."""
    assert parse_calc("123456789012345678901234567890") == IntLit(123456789012345678901234567890)


# ------------------------------------------------------------------ errors
OPERAND = {"INT", "MINUS", "TRUE", "FALSE", "NAME", "LPAREN"}
PARSE_BAD = [
    # (source, offset, kinds that MUST be in `expected`)
    ("", 0, OPERAND), ("   ", 3, OPERAND), ("1 +", 3, OPERAND), ("1 + * 2", 4, OPERAND), ("(", 1, OPERAND), ("()", 1, OPERAND),
    ("not", 3, OPERAND), ("-", 1, {"INT"}), ("1 -", 3, OPERAND),
    ("(1 + 2", 6, {"RPAREN"}), ("((1)", 4, {"RPAREN"}), ("(1 2)", 3, {"RPAREN"}), ("1 + 2)", 5, {"END"}), ("1 2", 2, {"END"}),
    ("true false", 5, {"END"}), ("x y", 2, {"END"}), ("12ab", 2, {"END"}), ("1 < 2 < 3", 6, {"END"}), ("1 < 2 == true", 6, {"END"}),
    ("if true 1 else 2", 8, {"THEN"}), ("if true then 1", 14, {"ELSE"}), ("if true then 1 2 else 3", 15, {"ELSE"}),
    ("if true then 1 else", 19, OPERAND), ("if then 1 else 2", 3, OPERAND), ("if true then else 2", 13, OPERAND),
    ("let = 1 in 2", 4, {"NAME"}), ("let", 3, {"NAME"}), ("let x 1 in x", 6, {"EQ"}), ("let x == 1 in x", 6, {"EQ"}),
    ("let x = 1 x", 10, {"IN"}), ("let x = 1", 9, {"IN"}), ("let x = 1 in", 12, OPERAND), ("let if = 1 in 2", 4, {"NAME"}),
    ("let 1 = 1 in 2", 4, {"NAME"}), ("let true = 1 in 2", 4, {"NAME"}),
    ("1 + let x = 2 in x", 4, OPERAND), ("not let x = 1 in x", 4, OPERAND), ("1 + if a then 1 else 2", 4, OPERAND),
    ("a & b", 2, {"END"}), ("a | b", 2, {"END"}), ("a -> b", 2, {"END"}), ("a <-> b", 2, {"END"}), ("~a", 0, OPERAND),
    ("x = 1", 2, {"END"}), ("1 <= 2", 3, OPERAND), ("then", 0, OPERAND), ("else", 0, OPERAND), ("in", 0, OPERAND),
    ("a and", 5, OPERAND), ("and a", 0, OPERAND),
]


@pytest.mark.parametrize("src,offset,must", PARSE_BAD, ids=[repr(s) for s, _, _ in PARSE_BAD])
def test_parse_errors_have_offset_and_expected(src, offset, must):
    """Each ParseError points at the start of the first offending token (or the end of input) and its expected-set contains the kinds the grammar requires there."""
    with pytest.raises(ParseError) as ei:
        parse_calc(src)
    assert ei.value.offset == offset, f"{src!r}: offset {ei.value.offset}, expected {offset}"
    assert ei.value.expected, "expected must never be empty"
    assert must <= ei.value.expected, f"{src!r}: expected {sorted(ei.value.expected)} should include {sorted(must)}"
    assert all(isinstance(k, str) for k in ei.value.expected)


def test_minus_not_followed_by_int_expects_exactly_int():
    """`-x` and `--2` fail at the token after the sign, and the only acceptable thing there is INT."""
    for src, offset in [("-x", 1), ("--2", 1), ("1 - -x", 5), ("- true", 2)]:
        with pytest.raises(ParseError) as ei:
            parse_calc(src)
        assert (ei.value.offset, ei.value.expected) == (offset, frozenset({"INT"})), src


@pytest.mark.parametrize("src,offset", [("1 + @", 4), ("1 ! 2", 2), ("a > b", 2), ("1.5", 1), ("٣", 0), ("é", 0), ("x λ", 2), ("1 ＋ 2", 2), ("let x = 1 in x ", 14)])
def test_lex_errors_surface_with_offset(src, offset):
    """Illegal characters are LexErrors (a LangError, not a ParseError) with the index of the character."""
    with pytest.raises(LexError) as ei:
        parse_calc(src)
    assert ei.value.offset == offset and isinstance(ei.value, LangError)


def test_lexing_happens_before_parsing():
    """`1 2 @` has a parse error at 2 and a lex error at 4: the whole text is tokenized first so the LexError wins."""
    with pytest.raises(LexError) as ei:
        parse_calc("1 2 @")
    assert ei.value.offset == 4


@pytest.mark.parametrize("bad", [None, 5, b"1", ["1"]])
def test_parse_calc_requires_str(bad):
    """Only str is parsed."""
    with pytest.raises(TypeError):
        parse_calc(bad)


# ------------------------------------------------------------------ round trips
@pytest.mark.parametrize(
    "e",
    [lambda: IntLit(-5), lambda: BinOp("-", IntLit(1), IntLit(-2)), lambda: BinOp("*", IntLit(-1), IntLit(-1)),
     lambda: If(BoolLit(True), IntLit(-1), IntLit(0)), lambda: Let("x", IntLit(-3), Var("x")), lambda: Not(Var("letx"))],
)
def test_negative_literals_round_trip(e):
    """to_source prints a negative literal as `-n`, and parse_calc reads it back to the same node."""
    node = e()
    assert parse_calc(to_source(node)) == node


@given(any_exprs(max_leaves=14))
def test_parse_inverts_to_source(e):
    """parse_calc(to_source(e)) == e for EVERY Expr (well-typed or not): printing loses nothing."""
    assert parse_calc(to_source(e)) == e, to_source(e)


@given(any_exprs(max_leaves=14))
def test_canonical_text_is_a_fixed_point(e):
    """to_source(parse_calc(s)) == s for canonical s, and the independent printer agrees with to_source."""
    s = to_source(e)
    assert to_source(parse_calc(s)) == s and s == show(e)


# ------------------------------------------------------------------ depth
def test_deep_nesting_does_not_hit_the_recursion_limit():
    """200 levels of parentheses, `not`, let-bodies, else-branches and a 200-term left chain parse under the default recursion limit."""
    assert parse_calc("(" * 200 + "1" + ")" * 200) == IntLit(1)
    deep_not = parse_calc("not " * 200 + "true")
    for _ in range(200):
        assert isinstance(deep_not, Not)
        deep_not = deep_not.operand
    assert deep_not == BoolLit(True)
    e = parse_calc("let x = 1 in " * 200 + "x")
    for _ in range(200):
        assert isinstance(e, Let)
        e = e.body
    assert e == Var("x")
    e = parse_calc("if true then 1 else " * 200 + "2")
    for _ in range(200):
        assert isinstance(e, If)
        e = e.orelse
    assert e == IntLit(2)
    chain = parse_calc(" + ".join(["1"] * 201))
    for _ in range(200):
        assert isinstance(chain, BinOp)
        chain = chain.left
    assert chain == IntLit(1)
    mixed = parse_calc("(1 + " * 200 + "1" + ")" * 200)
    assert to_source(mixed).count("(") == 200
