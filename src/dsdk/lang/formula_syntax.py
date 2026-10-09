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

from dsdk.logic import Formula

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
    raise NotImplementedError


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
    raise NotImplementedError
