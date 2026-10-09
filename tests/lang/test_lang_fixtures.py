"""Fixture-driven tests: fixtures/lang/*.json are the language-neutral oracle shared with the future JS port.

They were produced by an independent throwaway script (own regex tokenizer, own parsers, tuple-term interpreter; well-typed
results cross-checked with Python eval), not by dsdk. A disagreement means the implementation (or the fixture) is wrong --
re-derive by hand before touching the fixture.
"""
import pytest

from dsdk.core import Status
from dsdk.lang import LexError, ParseError, parse_formula
from dsdk.lang.calc import StuckError, Type, evaluate, parse_calc, size, to_source, trace, typecheck
from dsdk.logic import to_str

from lang_helpers import decode_ast, encode_ast, load_fixture

FORMULAS = load_fixture("formulas_relaxed.json")
CALC = load_fixture("calc_programs.json")
PROGRAMS = CALC["valid"] + CALC["invalid"]


def render(v):
    return "true" if v is True else "false" if v is False else str(v)


# ------------------------------------------------------------------ formulas
@pytest.mark.parametrize("case", FORMULAS["relaxed_valid"], ids=[c["input"] for c in FORMULAS["relaxed_valid"]])
def test_relaxed_inputs_have_the_fixture_canonical_form(case):
    """Relaxed input -> logic.to_str of the parsed formula equals the fixture's canonical string, and that string is a fixed point of strict parsing."""
    f = parse_formula(case["input"], relaxed=True)
    assert to_str(f) == case["canonical"]
    assert parse_formula(case["canonical"]) == f


def _check_error(fn, case):
    with pytest.raises((LexError, ParseError)) as ei:
        fn(case["input"])
    got = ei.value
    assert isinstance(got, LexError) == (case["error"] == "lex"), f"{case['input']!r}: expected a {case['error']} error, got {type(got).__name__}"
    assert got.offset == case["offset"], f"{case['input']!r}: offset {got.offset} vs {case['offset']}"
    if case["error"] == "parse":
        assert got.expected == frozenset(case["expected"]), f"{case['input']!r}: {sorted(got.expected)} vs {case['expected']}"


@pytest.mark.parametrize("case", FORMULAS["relaxed_invalid"], ids=[repr(c["input"]) for c in FORMULAS["relaxed_invalid"]])
def test_relaxed_invalid_inputs_fail_like_the_fixture(case):
    """Each invalid relaxed string fails with the fixture's error kind, offset and expected-set."""
    _check_error(lambda t: parse_formula(t, relaxed=True), case)


@pytest.mark.parametrize("case", FORMULAS["strict_invalid"], ids=[repr(c["input"]) for c in FORMULAS["strict_invalid"]])
def test_strict_invalid_inputs_fail_like_the_fixture(case):
    """Each invalid strict string fails with the fixture's error kind, offset and expected-set."""
    _check_error(parse_formula, case)


# ------------------------------------------------------------------ calc
def test_fixture_is_large_enough_and_asts_decode():
    """At least 6 valid and 6 invalid programs, unique names, every AST decodes through the node constructors (and re-encodes to itself)."""
    assert len(CALC["valid"]) >= 6 and len(CALC["invalid"]) >= 6
    names = [c["name"] for c in PROGRAMS]
    assert len(set(names)) == len(names)
    for c in PROGRAMS:
        assert encode_ast(decode_ast(c["ast"])) == c["ast"], c["name"]


@pytest.mark.parametrize("case", PROGRAMS, ids=[c["name"] for c in PROGRAMS])
def test_source_parses_to_the_fixture_ast(case):
    """parse_calc(source) is the fixture AST (compared structurally and as encoded JSON) and prints back to the fixture canonical text."""
    e = parse_calc(case["source"])
    assert e == decode_ast(case["ast"])
    assert encode_ast(e) == case["ast"]
    assert to_source(e) == case["canonical"]
    assert size(e) == case["size"]


@pytest.mark.parametrize("case", PROGRAMS, ids=[c["name"] for c in PROGRAMS])
def test_static_typing_matches_the_fixture(case):
    """typecheck gives KNOWN with the fixture type, or INVALID with exactly the fixture reason (tag and offending node)."""
    j = typecheck(decode_ast(case["ast"]))
    if case["type"] is not None:
        assert j.status is Status.KNOWN and j.value is Type(case["type"]), f"{case['source']}: {j}"
    else:
        assert j.status is Status.INVALID and j.reason == case["type_error"]["reason"], f"{case['source']}: {j}"


@pytest.mark.parametrize("case", PROGRAMS, ids=[c["name"] for c in PROGRAMS])
def test_small_step_trace_matches_the_fixture(case):
    """The full small-step trace (every intermediate term), its length and the final outcome equal the fixture."""
    t = trace(decode_ast(case["ast"]))
    assert [to_source(x) for x in t] == case["trace"]
    assert len(t) - 1 == case["steps"]
    last = t[-1]
    assert (type(last).__name__ not in ("IntLit", "BoolLit")) == case["stuck"], "stuck means the final term is not a value"
    assert case["outcome"] == ("stuck" if case["stuck"] else "value")


@pytest.mark.parametrize("case", PROGRAMS, ids=[c["name"] for c in PROGRAMS])
def test_big_step_value_matches_the_fixture(case):
    """evaluate returns the fixture value (decimal text compared, so 30-digit results are exact) and its Python type, or raises StuckError exactly for stuck programs."""
    e = decode_ast(case["ast"])
    if case["stuck"]:
        assert case["value"] is None
        with pytest.raises(StuckError):
            evaluate(e)
    else:
        got = evaluate(e)
        assert render(got) == case["value"]
        assert (Type.BOOL if type(got) is bool else Type.INT) is Type(case["value_type"])


def test_well_typed_programs_in_the_fixture_never_get_stuck():
    """Type safety on the fixture: every `valid` program ends in a value whose type is the static type."""
    for c in CALC["valid"]:
        assert not c["stuck"] and c["value_type"] == c["type"], c["name"]


def test_ill_typed_does_not_mean_stuck_in_the_fixture():
    """The fixture holds ill-typed programs that still evaluate (`false and (1 + true)`), proving the static check is conservative."""
    runs = [c["name"] for c in CALC["invalid"] if not c["stuck"]]
    assert {"branch_not_taken_is_ill_typed", "short_circuit_hides_error", "branch_mismatch_but_runs"} <= set(runs)
    stuck = [c["name"] for c in CALC["invalid"] if c["stuck"]]
    assert {"int_plus_bool", "unbound_var", "stuck_left_blocks_right"} <= set(stuck)


@pytest.mark.parametrize("case", CALC["syntax_errors"], ids=[repr(c["source"]) for c in CALC["syntax_errors"]])
def test_syntax_errors_match_the_fixture(case):
    """Lex/parse errors carry the fixture offset; parse errors' expected-sets include the fixture's required kinds."""
    with pytest.raises((LexError, ParseError)) as ei:
        parse_calc(case["source"])
    got = ei.value
    assert isinstance(got, LexError) == (case["error"] == "lex")
    assert got.offset == case["offset"]
    if case["error"] == "parse":
        assert set(case["expected_includes"]) <= got.expected
