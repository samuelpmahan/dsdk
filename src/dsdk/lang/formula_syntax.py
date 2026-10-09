"""Parsing :class:`dsdk.logic.Formula` from text: a STRICT mode that is the exact inverse of ``dsdk.logic.to_str``, and a
RELAXED mode for humans (whitespace, omitted parentheses, operator precedence).

Both modes tokenize first with ``tokenize(text, FORMULA_KEYWORDS, keep_whitespace=True)`` and parse the token list. LEXING
HAPPENS BEFORE PARSING: an illegal character anywhere in the input raises ``LexError`` even if a ``ParseError`` would
have occurred earlier in the text. (``parse_formula("a a @")`` is a LexError at offset 4, not a ParseError at 2.)

Token kinds used (see :mod:`dsdk.lang.lexer`): NAME TRUE FALSE LPAREN RPAREN TILDE AMP BAR ARROW IFF WS. Any other kind
(INT PLUS STAR MINUS LT EQ EQEQ and every Calc keyword is just a NAME here) is a ``ParseError`` at that token.
In RELAXED mode WS tokens are dropped before parsing; in STRICT mode they are part of the grammar.

STRICT grammar (a restatement of the ``dsdk.logic.formula`` docstring over tokens; ``WS`` must have text exactly ``" "``)::

    formula := atom
             | LPAREN TILDE formula RPAREN
             | LPAREN formula WS op WS formula RPAREN
    op      := AMP | BAR | ARROW | IFF            atom := NAME | TRUE | FALSE

``parse_formula(to_str(f)) == f`` for every Formula ``f`` and ``to_str(parse_formula(s)) == s`` for every canonical ``s``.
Anything else is a ParseError: ``a & b``, ``(a)``, ``~a``, ``(a&b)``, ``(a  & b)``, ``( a & b)``, ``(a & b) `` (trailing space).

RELAXED grammar (lowest to highest precedence; every level is listed with its associativity)::

    iff  := imp ( IFF imp )*          '<->' LEFT-associative:  a <-> b <-> c  ==  Iff(Iff(a, b), c)
    imp  := or  ( ARROW imp )?        '->'  RIGHT-associative: a -> b -> c    ==  Implies(a, Implies(b, c))
    or   := and ( BAR and )*          '|'   LEFT-associative:  a | b | c      ==  Or(Or(a, b), c)
    and  := not ( AMP not )*          '&'   LEFT-associative:  a & b & c      ==  And(And(a, b), c)
    not  := TILDE not | atom          '~' binds tightest:      ~a & b == And(Not(a), b);  ~~a == Not(Not(a))
    atom := NAME | TRUE | FALSE | LPAREN iff RPAREN

(``&``, ``|`` and ``<->`` are associative as TRUTH FUNCTIONS, so the choice of left is a convention that matches the
shape ``to_str`` prints for ``And(And(a, b), c)``; ``->`` is NOT associative, so its right-associativity matters.)
Every canonical string is also accepted in relaxed mode and gives the same Formula. Redundant parentheses are fine.

``ParseError`` details (``offset`` = start offset of the first offending token, or ``len(text)`` if the input ended;
``expected`` = frozenset of kind names acceptable there, ``"END"`` meaning end of input):

    RELAXED:  wanting an operand (start, after '(', after '~', after a binary operator):
                  {"LPAREN", "TILDE", "NAME", "TRUE", "FALSE"}
              after a complete operand, when no '(' is open:   {"AMP", "BAR", "ARROW", "IFF", "END"}
              after a complete operand, inside an open '(':    {"AMP", "BAR", "ARROW", "IFF", "RPAREN"}
    STRICT:   wanting a formula (start of the input, right after '(~', right after the WS that follows an operator):
                  {"LPAREN", "NAME", "TRUE", "FALSE"}          (a bare '~' is NOT canonical, so no TILDE)
              immediately after a '(' :  {"TILDE", "LPAREN", "NAME", "TRUE", "FALSE"}
              after a complete formula, which depends on what encloses it:
                  nothing (top level)              {"END"}
                  it is the operand of '(~'        {"RPAREN"}
                  it is the LEFT operand of '(x'   {"WS"}      and after that WS:  {"AMP", "BAR", "ARROW", "IFF"}
                  it is the RIGHT operand          {"RPAREN"}
              after the operator token : {"WS"}      (then, after that WS, a formula is wanted as above)
              A WS token whose text is not exactly " " (two spaces, a tab, a newline) where a WS is wanted: offset = that
              token's start, expected {"WS"}.
              A WS token anywhere else is unexpected: its start offset and the set that applies there.
"""
from __future__ import annotations

from dsdk.logic import And, Const, Formula, Iff, Implies, Not, Or, Var

from .errors import LexError, ParseError  # noqa: F401  (raised here)
from .lexer import FORMULA_KEYWORDS, tokenize  # noqa: F401  (used by the implementation)


def parse_formula(text: str, *, relaxed: bool = False) -> Formula:
    """Parse ``text`` into a ``dsdk.logic.Formula``. ``relaxed=False`` (the default) is STRICT mode.

    * A non-``str`` is a ``TypeError``. ``""`` is a ``ParseError`` (offset 0).
    * ``LexError`` for an illegal character (checked for the whole text first); ``ParseError`` otherwise.
    * Variable names are validated by ``dsdk.logic.Var`` itself; a NAME token can never be invalid there.
    * Nesting depth 200 (parentheses, ``~`` chains, ``->`` chains, left chains of ``&``) must NOT raise ``RecursionError``
      under Python's default recursion limit: loop for left-associative chains and use at most 3 Python frames per
      nesting level, or use an explicit stack.
    """
    toks = tokenize(text, FORMULA_KEYWORDS, keep_whitespace=True)
    if relaxed:
        return _parse_relaxed(text, [t for t in toks if t.kind != "WS"])
    return _parse_strict(text, toks)


def all_parses(text: str) -> list[Formula]:
    """Every parse tree of a PRECEDENCE-FREE grammar, to show why precedence exists.

    Grammar ``E := E op E | atom`` with ``op`` any of ``& | -> <->`` and NO precedence, NO associativity, no parentheses, no
    ``~``. For a text with ``k`` operators it has Catalan(k) parse trees (1, 1, 2, 5, 14, 42 for k = 0..5). Tokenize like
    ``parse_formula`` (WS dropped). Return the trees as Formulas in this exact order: for the root operator at operator
    index ``i`` = 0, 1, ..., k-1 (left to right) and, for each ``i``, every left tree (in this same order) crossed with
    every right tree (outer loop over left trees, inner loop over right trees). So
    ``all_parses("a | b & c") == [Or(a, And(b, c)), And(Or(a, b), c)]`` (root ``|`` first) -- two readings with
    DIFFERENT truth tables, which is exactly the ambiguity precedence removes.

    ``LexError`` for an illegal character. ``ParseError`` if the tokens are not ``atom (op atom)*`` (atoms are NAME, TRUE,
    FALSE) -- e.g. ``"a &"``, ``"~a"``, ``"(a)"``, ``""``.
    """
    toks = tokenize(text, FORMULA_KEYWORDS)
    atoms: list[Formula] = []
    ops: list[type] = []
    want_atom = True
    for j, tok in enumerate(toks):
        if want_atom:
            if tok.kind not in _ATOM_KINDS:
                raise _error(text, toks, j, _ATOM_KINDS)
            atoms.append(_atom(tok))
        else:
            if tok.kind not in _OP_CLS:
                raise _error(text, toks, j, _OP_KINDS)
            ops.append(_OP_CLS[tok.kind])
        want_atom = not want_atom
    if want_atom:
        raise _error(text, toks, len(toks), _ATOM_KINDS)

    memo: dict[tuple[int, int], list[Formula]] = {}

    def go(lo: int, hi: int) -> list[Formula]:
        key = (lo, hi)
        if key in memo:
            return memo[key]
        if lo == hi:
            result = [atoms[lo]]
        else:
            result = []
            for i in range(lo, hi):
                cls = ops[i]
                for left in go(lo, i):
                    for right in go(i + 1, hi):
                        result.append(cls(left, right))
        memo[key] = result
        return result

    return list(go(0, len(atoms) - 1))


# ---------------------------------------------------------------------------------------------- private helpers
_ATOM_KINDS = frozenset({"NAME", "TRUE", "FALSE"})
_OP_KINDS = frozenset({"AMP", "BAR", "ARROW", "IFF"})
_OP_CLS: dict[str, type] = {"AMP": And, "BAR": Or, "ARROW": Implies, "IFF": Iff}
_BIN_PREC = {"IFF": 1, "ARROW": 2, "BAR": 3, "AMP": 4}
_RELAXED_OPERAND = frozenset({"LPAREN", "TILDE", "NAME", "TRUE", "FALSE"})
_STRICT_F = frozenset({"LPAREN", "NAME", "TRUE", "FALSE"})
_STRICT_L = _STRICT_F | {"TILDE"}


def _atom(tok) -> Formula:
    if tok.kind == "TRUE":
        return Const(True)
    if tok.kind == "FALSE":
        return Const(False)
    return Var(tok.text)


def _error(text: str, toks: list, j: int, expected) -> ParseError:
    """ParseError for token ``j`` (or end of input when ``j`` is past the last token)."""
    if j < len(toks):
        return ParseError(f"unexpected {toks[j].text!r}", toks[j].start, expected)
    return ParseError("unexpected end of input", len(text), expected)


def _parse_relaxed(text: str, toks: list) -> Formula:
    parser = _RelaxedParser(text, toks)
    formula = parser.expr(0)
    if parser.pos < len(toks):
        raise _error(text, toks, parser.pos, parser.after_set())
    return formula


class _RelaxedParser:
    """Precedence climbing over WS-free tokens. Recursion is at most two Python frames per nesting level."""

    def __init__(self, text: str, toks: list) -> None:
        self.text = text
        self.toks = toks
        self.pos = 0
        self.depth = 0  # number of currently open parentheses

    def _kind(self) -> str | None:
        return self.toks[self.pos].kind if self.pos < len(self.toks) else None

    def after_set(self) -> frozenset[str]:
        return _OP_KINDS | (frozenset({"RPAREN"}) if self.depth else frozenset({"END"}))

    def prefix(self) -> Formula:
        kind = self._kind()
        if kind in _ATOM_KINDS:
            tok = self.toks[self.pos]
            self.pos += 1
            return _atom(tok)
        if kind == "TILDE":
            self.pos += 1
            return Not(self.expr(5))
        if kind == "LPAREN":
            self.pos += 1
            self.depth += 1
            inner = self.expr(0)
            if self._kind() != "RPAREN":
                raise _error(self.text, self.toks, self.pos, self.after_set())
            self.pos += 1
            self.depth -= 1
            return inner
        raise _error(self.text, self.toks, self.pos, _RELAXED_OPERAND)

    def expr(self, min_prec: int) -> Formula:
        left = self.prefix()
        while True:
            kind = self._kind()
            prec = _BIN_PREC.get(kind) if kind is not None else None
            if prec is None or prec < min_prec:
                return left
            self.pos += 1
            right = self.expr(prec if kind == "ARROW" else prec + 1)
            left = _OP_CLS[kind](left, right)


def _parse_strict(text: str, toks: list) -> Formula:
    """Explicit stack machine over the WS-including tokens (no recursion).

    Frames: ``("not",)`` inside ``(~ ...)``; ``("left",)`` waiting for the left operand of ``(x op y)``;
    ``("right", left, op_kind)`` waiting for the right operand.
    """
    n = len(toks)
    stack: list[tuple] = []
    i = 0
    after_lparen = False
    while True:
        # ---- want a formula at toks[i]
        lparen_ctx = after_lparen
        after_lparen = False
        kind = toks[i].kind if i < n else None
        if kind in _ATOM_KINDS:
            value = _atom(toks[i])
            i += 1
        elif kind == "LPAREN":
            if i + 1 < n and toks[i + 1].kind == "TILDE":
                stack.append(("not",))
                i += 2
            else:
                stack.append(("left",))
                i += 1
                after_lparen = True
            continue
        else:
            raise _error(text, toks, i, _STRICT_L if lparen_ctx else _STRICT_F)

        # ---- a complete formula `value` is at hand
        while True:
            if not stack:
                if i < n:
                    raise _error(text, toks, i, frozenset({"END"}))
                return value
            top = stack[-1]
            if top[0] == "left":
                if i >= n or toks[i].kind != "WS" or toks[i].text != " ":
                    raise _error(text, toks, i, frozenset({"WS"}))
                if i + 1 >= n or toks[i + 1].kind not in _OP_KINDS:
                    raise _error(text, toks, i + 1, _OP_KINDS)
                op = toks[i + 1].kind
                if i + 2 >= n or toks[i + 2].kind != "WS" or toks[i + 2].text != " ":
                    raise _error(text, toks, i + 2, frozenset({"WS"}))
                stack[-1] = ("right", value, op)
                i += 3
                break
            if i >= n or toks[i].kind != "RPAREN":
                raise _error(text, toks, i, frozenset({"RPAREN"}))
            i += 1
            stack.pop()
            if top[0] == "not":
                value = Not(value)
            else:
                value = _OP_CLS[top[2]](top[1], value)
