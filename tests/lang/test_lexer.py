"""Contract tests for dsdk.lang.lexer: a DFA-table tokenizer with maximal munch, exact offsets and offset-carrying errors."""
import dataclasses

import pytest
from hypothesis import given
from hypothesis import strategies as st

from dsdk.lang import LexError, Token, tokenize
from dsdk.lang.lexer import CALC_KEYWORDS, CHAR_CLASS_NAMES, FORMULA_KEYWORDS, char_class, default_dfa

ALL_KINDS = {"NAME", "INT", "WS", "LPAREN", "RPAREN", "TILDE", "AMP", "BAR", "ARROW", "IFF", "PLUS", "MINUS", "STAR", "LT", "EQEQ", "EQ"}

EXPECTED_TRANSITIONS = {
    ("start", "alpha"): "name", ("start", "digit"): "int", ("start", "space"): "ws",
    ("start", "("): "lparen", ("start", ")"): "rparen", ("start", "~"): "tilde", ("start", "&"): "amp",
    ("start", "|"): "bar", ("start", "+"): "plus", ("start", "*"): "star", ("start", "-"): "minus",
    ("start", "<"): "lt", ("start", "="): "eq",
    ("name", "alpha"): "name", ("name", "digit"): "name",
    ("int", "digit"): "int",
    ("ws", "space"): "ws",
    ("minus", ">"): "arrow",
    ("lt", "-"): "lt_minus",
    ("lt_minus", ">"): "iff",
    ("eq", "="): "eqeq",
}
EXPECTED_ACCEPTING = {
    "name": "NAME", "int": "INT", "ws": "WS", "lparen": "LPAREN", "rparen": "RPAREN", "tilde": "TILDE", "amp": "AMP",
    "bar": "BAR", "plus": "PLUS", "star": "STAR", "minus": "MINUS", "arrow": "ARROW", "lt": "LT", "iff": "IFF",
    "eq": "EQ", "eqeq": "EQEQ",
}


def kinds(text, **kw):
    return [t.kind for t in tokenize(text, **kw)]


def texts(text, **kw):
    return [t.text for t in tokenize(text, **kw)]


# ------------------------------------------------------------------ single tokens
@pytest.mark.parametrize(
    "text,kind",
    [("abc", "NAME"), ("_", "NAME"), ("x1_y2", "NAME"), ("Z", "NAME"), ("0", "INT"), ("007", "INT"), ("12345678901234567890", "INT"),
     ("(", "LPAREN"), (")", "RPAREN"), ("~", "TILDE"), ("&", "AMP"), ("|", "BAR"), ("->", "ARROW"), ("<->", "IFF"),
     ("+", "PLUS"), ("*", "STAR"), ("-", "MINUS"), ("<", "LT"), ("==", "EQEQ"), ("=", "EQ")],
)
def test_every_token_kind_is_recognised(text, kind):
    """Each token kind in the module table lexes from its canonical text as ONE token covering the whole input."""
    toks = tokenize(text)
    assert toks == [Token(kind, text, 0, len(text))], f"{text!r} should be exactly one {kind} token, got {toks}"


def test_offsets_are_start_inclusive_end_exclusive():
    """start/end index the source string so that text == source[start:end]; later passes report errors with these offsets."""
    src = "ab + 12"
    toks = tokenize(src)
    assert [(t.kind, t.text, t.start, t.end) for t in toks] == [("NAME", "ab", 0, 2), ("PLUS", "+", 3, 4), ("INT", "12", 5, 7)]
    assert all(src[t.start:t.end] == t.text for t in toks)


# ------------------------------------------------------------------ maximal munch
@pytest.mark.parametrize(
    "text,expected",
    [
        ("<->", ["<->"]),
        ("<-b", ["<", "-", "b"]),
        ("<-", ["<", "-"]),
        ("<--", ["<", "-", "-"]),
        ("<-1", ["<", "-", "1"]),
        ("a<->b", ["a", "<->", "b"]),
        ("a<-b", ["a", "<", "-", "b"]),
        ("a<-", ["a", "<", "-"]),
        ("<->->", ["<->", "->"]),
        ("->", ["->"]),
        ("-->", ["-", "->"]),
        ("1-2", ["1", "-", "2"]),
        ("1->2", ["1", "->", "2"]),
        ("===", ["==", "="]),
        ("====", ["==", "=="]),
        ("a==b", ["a", "==", "b"]),
        ("<<", ["<", "<"]),
        ("<=", ["<", "="]),
        ("12ab", ["12", "ab"]),
        ("ab12", ["ab12"]),
        ("1_", ["1", "_"]),
    ],
)
def test_maximal_munch_with_backtracking(text, expected):
    """The longest accepting prefix wins, and a failed longer attempt (`<-` not followed by `>`) falls back: `<->` is one IFF, `<-b` is LT MINUS NAME."""
    assert texts(text) == expected, f"{text!r} must split as {expected}"


def test_iff_versus_lt_minus_gt_kinds():
    """`<->` is the single kind IFF while `<-b` is LT, MINUS, NAME: the ambiguity a regex-free DFA must resolve by backtracking."""
    assert kinds("<->") == ["IFF"]
    assert kinds("<-b") == ["LT", "MINUS", "NAME"]


@pytest.mark.parametrize("text,offset", [("<->>", 3), ("->>", 2), ("a->>b", 3)])
def test_leftover_after_a_maximal_token_is_judged_on_its_own(text, offset):
    """After `<->` or `->` is consumed a stray `>` is an illegal start: the error offset is that character, not the start of the operator."""
    with pytest.raises(LexError) as ei:
        tokenize(text)
    assert ei.value.offset == offset, f"{text!r}: the illegal '>' is at {offset}, got {ei.value.offset}"


# ------------------------------------------------------------------ keywords
def test_keywords_are_recognised_only_as_whole_names():
    """`true` is TRUE but `trueish`, `true1`, `True` and `_true` are NAMEs: keywords are looked up after the DFA reads the whole identifier."""
    assert kinds("true false", keywords=FORMULA_KEYWORDS) == ["TRUE", "FALSE"]
    for word in ["trueish", "true1", "True", "_true", "falsey", "TRUE"]:
        assert kinds(word, keywords=FORMULA_KEYWORDS) == ["NAME"], f"{word!r} is a plain NAME"


def test_keyword_kind_is_uppercased_text_and_text_is_unchanged():
    """The keyword kind is text.upper() and Token.text keeps the source spelling."""
    toks = tokenize("let x in", keywords=CALC_KEYWORDS)
    assert [(t.kind, t.text) for t in toks] == [("LET", "let"), ("NAME", "x"), ("IN", "in")]


def test_without_keywords_every_word_is_a_name():
    """The default keyword set is empty, so `let`, `true`, `in` are NAMEs (formulas allow variables called `if`)."""
    assert kinds("let true in if") == ["NAME"] * 4
    assert kinds("if then else and or not", keywords=FORMULA_KEYWORDS) == ["NAME"] * 6


def test_calc_keywords_cover_the_calc_grammar():
    """CALC_KEYWORDS is exactly the ten reserved words of Calc (the parser and Var validation rely on it)."""
    assert CALC_KEYWORDS == {"true", "false", "let", "in", "if", "then", "else", "and", "or", "not"}
    assert FORMULA_KEYWORDS == {"true", "false"}
    assert kinds("trueish iff", keywords=CALC_KEYWORDS) == ["NAME", "NAME"], "`iff` is not a keyword, `if` is"


# ------------------------------------------------------------------ whitespace
def test_whitespace_dropped_by_default():
    """Whitespace separates tokens but is not emitted unless asked for."""
    assert texts("  a \t\n b\r\n") == ["a", "b"]


def test_whitespace_kept_as_maximal_runs():
    """With keep_whitespace a run of spaces/tabs/newlines is ONE WS token (so the strict parser can see `a  &` has two spaces)."""
    toks = tokenize("a  \t&\nb", keep_whitespace=True)
    assert [(t.kind, t.text) for t in toks] == [("NAME", "a"), ("WS", "  \t"), ("AMP", "&"), ("WS", "\n"), ("NAME", "b")]


def test_empty_and_blank_inputs():
    """Empty input is no tokens; blank input is no tokens (or one WS token when kept). Parsers rely on this to report 'unexpected end'."""
    assert tokenize("") == []
    assert tokenize(" \t\n") == []
    assert tokenize("", keep_whitespace=True) == []
    assert [(t.kind, t.start, t.end) for t in tokenize(" \t\n", keep_whitespace=True)] == [("WS", 0, 3)]


# ------------------------------------------------------------------ errors
@pytest.mark.parametrize(
    "text,offset",
    [
        ("@", 0), ("a @", 2), ("a>b", 1), (">", 0), ("!", 0), ("1.5", 1), ("a\x00", 1), ("\x0c", 0), ("a\x0b", 1),
        ("é", 0), ("a é", 2), ("naïve", 2), ("λ", 0), ("a ∧ b", 2), ("a → b", 2),
        ("٣", 0), ("1٣", 1),
        ("a b", 1),
        ("ａ", 0), ("＿", 0),
        ("ab😀", 2), ("😀 a", 0),
        ("@é", 0),
        ("{", 0), ("a;", 1), ("a,b", 1), ("'x'", 0), ('"', 0), ("a#", 1),
    ],
)
def test_illegal_characters_raise_lexerror_at_their_index(text, offset):
    """Unicode look-alikes (Arabic-Indic digits, fullwidth letters, NBSP, arrows, emoji) are NOT letters/digits/spaces here: LexError with the code-point index of the FIRST bad character."""
    with pytest.raises(LexError) as ei:
        tokenize(text)
    assert ei.value.offset == offset, f"{text!r}: expected offset {offset}, got {ei.value.offset}"
    assert isinstance(ei.value.offset, int)


@pytest.mark.parametrize("bad", [None, 5, b"abc", ["a"]])
def test_non_string_input_is_a_typeerror(bad):
    """Only str is tokenizable; bytes must not be silently accepted."""
    with pytest.raises(TypeError):
        tokenize(bad)


# ------------------------------------------------------------------ char_class
@pytest.mark.parametrize(
    "ch,cls",
    [("a", "alpha"), ("Z", "alpha"), ("_", "alpha"), ("0", "digit"), ("9", "digit"), (" ", "space"), ("\t", "space"), ("\n", "space"),
     ("\r", "space"), ("(", "("), (")", ")"), ("~", "~"), ("&", "&"), ("|", "|"), ("+", "+"), ("*", "*"), ("-", "-"), ("<", "<"),
     (">", ">"), ("=", "="), ("é", "other"), ("٣", "other"), (" ", "other"), ("\x0c", "other"), ("!", "other"), ("ａ", "other")],
)
def test_char_class_is_ascii_only(ch, cls):
    """char_class must not use str.isalpha/isdigit/isspace (they accept é, ٣ and NBSP); it is a fixed ASCII classification."""
    assert char_class(ch) == cls


def test_char_class_names_constant_covers_all_results():
    """CHAR_CLASS_NAMES is the closed set of class names char_class can return."""
    results = {char_class(chr(i)) for i in range(0, 300)}
    assert results == CHAR_CLASS_NAMES


@pytest.mark.parametrize("bad", ["", "ab"])
def test_char_class_wants_exactly_one_character(bad):
    """A str of length != 1 is a ValueError."""
    with pytest.raises(ValueError):
        char_class(bad)


def test_char_class_non_str_is_typeerror():
    """A non-str is a TypeError."""
    with pytest.raises(TypeError):
        char_class(5)


# ------------------------------------------------------------------ the DFA table is inspectable data
def test_default_dfa_table_is_exactly_the_documented_one():
    """The transition table and accepting map are plain data that equal the module docstring entry by entry (a JS port can copy them)."""
    d = default_dfa()
    assert d.start == "start"
    assert dict(d.transitions) == EXPECTED_TRANSITIONS
    assert dict(d.accepting) == EXPECTED_ACCEPTING


def test_default_dfa_is_structurally_sound():
    """Sanity of the machine: start is not accepting, all targets are real states, every state is reachable, class names are known, and no state except `start` and `lt_minus` is non-accepting."""
    d = default_dfa()
    states = {d.start} | {s for s, _ in d.transitions} | set(d.transitions.values()) | set(d.accepting)
    assert d.start not in d.accepting, "an accepting start state would allow empty tokens"
    assert set(d.accepting) <= states
    assert {c for _, c in d.transitions} <= CHAR_CLASS_NAMES - {"other"}, "no transitions on 'other'"
    assert set(d.accepting.values()) == ALL_KINDS
    reachable, todo = {d.start}, [d.start]
    while todo:
        s = todo.pop()
        for (src, _), dst in d.transitions.items():
            if src == s and dst not in reachable:
                reachable.add(dst)
                todo.append(dst)
    assert reachable == states, f"unreachable states: {states - reachable}"
    assert states - set(d.accepting) == {"start", "lt_minus"}


def test_default_dfa_cannot_be_corrupted_through_a_previous_result():
    """Mutating a returned table (if it even allows it) must not change what the next default_dfa() returns."""
    d = default_dfa()
    try:
        d.transitions[("start", "alpha")] = "int"  # may raise TypeError for a read-only mapping: both designs are fine
    except TypeError:
        pass
    assert dict(default_dfa().transitions) == EXPECTED_TRANSITIONS
    assert kinds("abc") == ["NAME"]


def walk(dfa, text):
    """Run the table by hand over `text`; returns the final state or None if it gets stuck."""
    state = dfa.start
    for ch in text:
        state = dfa.transitions.get((state, char_class(ch)))
        if state is None:
            return None
    return state


def test_walking_the_table_by_hand_agrees_with_the_story():
    """`<-` ends in a NON-accepting state (so the lexer must backtrack), `<->` in the IFF state, `<-x` in no state."""
    d = default_dfa()
    assert walk(d, "<-") not in d.accepting and walk(d, "<-") is not None
    assert d.accepting[walk(d, "<->")] == "IFF"
    assert walk(d, "<-x") is None
    assert d.accepting[walk(d, "abc123")] == "NAME"
    assert walk(d, "1a") is None


def test_tokenizer_follows_the_table_it_is_given():
    """The table is the single source of truth: delete `->` from it and `->` stops lexing; add letter-after-minus and `a-b` becomes one NAME."""
    d = default_dfa()
    no_arrow = dataclasses.replace(d, transitions={k: v for k, v in d.transitions.items() if k != ("minus", ">")})
    assert kinds("->") == ["ARROW"]
    with pytest.raises(LexError) as ei:
        tokenize("->", dfa=no_arrow)
    assert ei.value.offset == 1, "with the minus->arrow edge removed `-` lexes alone and `>` is illegal"
    sticky = dataclasses.replace(d, transitions={**d.transitions, ("name", "-"): "name"})
    assert texts("a-b c", dfa=sticky) == ["a-b", "c"]
    assert texts("a-b c") == ["a", "-", "b", "c"]


# ------------------------------------------------------------------ scale and properties
def test_long_inputs_are_handled_without_recursion():
    """100000 characters of one identifier, and 50000 tokens, lex fine (iteration, not recursion; linear time)."""
    assert len(tokenize("a" * 100000)) == 1
    assert len(tokenize("a " * 50000)) == 50000
    assert len(tokenize("<-" * 20000)) == 40000


_ALPHABET = list("ab_019 \t\n()~&|+*-<>=")


@given(st.text(alphabet=_ALPHABET, max_size=40))
def test_tokens_cover_the_input_exactly_and_are_maximal(text):
    """With whitespace kept the tokens tile the input (contiguous, texts concatenate to the input), each token re-lexes to itself, and no two ADJACENT tokens could have been one longer token (maximal munch)."""
    try:
        toks = tokenize(text, keep_whitespace=True)
    except LexError as e:
        # only a stray '>' can be illegal in this alphabet; the reported offset must point at one
        assert text[e.offset] == ">"
        return
    assert "".join(t.text for t in toks) == text
    assert [t.start for t in toks] == [sum(len(u.text) for u in toks[:i]) for i in range(len(toks))]
    for t in toks:
        assert t.end == t.start + len(t.text) and text[t.start:t.end] == t.text
        assert tokenize(t.text, keep_whitespace=True) == [Token(t.kind, t.text, 0, len(t.text))]
    for a, b in zip(toks, toks[1:]):
        merged = tokenize(a.text + b.text, keep_whitespace=True)
        assert merged[0].text == a.text, f"{a.text!r}+{b.text!r} would lex as a longer token {merged[0].text!r}: not maximal munch"
