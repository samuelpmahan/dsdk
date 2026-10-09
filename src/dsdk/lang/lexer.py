"""A tokenizer written as an explicit DFA whose transition table is inspectable DATA (no regexes).

Used by both the formula parser and the Calc parser. Offsets are 0-based ``str`` indices.

Token kinds (``Token.kind`` is one of these plain ``str`` values)::

    NAME   [A-Za-z_][A-Za-z0-9_]*          INT    [0-9]+          WS   a maximal run of ' ' '\\t' '\\n' '\\r'
    LPAREN (    RPAREN )    TILDE ~    AMP &    BAR |    PLUS +    STAR *    MINUS -
    ARROW  ->   IFF  <->    LT    <    EQEQ ==   EQ    =

plus one KEYWORD kind per keyword, equal to the keyword's text UPPER-CASED (``"true"`` -> ``"TRUE"``, ``"let"`` ->
``"LET"``). Keywords are not in the DFA: the DFA reads a whole identifier as NAME, and only afterwards ``tokenize`` turns a
NAME whose full text is in the ``keywords`` argument into the keyword kind. So ``trueish`` is a NAME, never TRUE + NAME.
A character such as ``>``, ``!``, ``@``, ``é``, ``٣`` (Arabic-Indic digit), the non-breaking space ``\\u00a0`` or a
fullwidth letter belongs to no token and is a :class:`LexError`. ``char_class`` is deliberately ASCII-only:
``str.isalpha`` / ``str.isdigit`` / ``str.isspace`` accept far more and MUST NOT be used.

Character classes (``char_class(ch)``)::

    "alpha"  A-Z a-z _          "digit"  0-9          "space"  ' ' '\\t' '\\n' '\\r'
    "(" ")" "~" "&" "|" "+" "*" "-" "<" ">" "="   each of these characters is its own class (the class name IS the character)
    "other"  every other character (there are no transitions on "other")

The DFA (this exact table is :func:`default_dfa`; a test compares it entry by entry). States and what they accept::

    start (accepts nothing)     name->NAME   int->INT   ws->WS   lparen->LPAREN   rparen->RPAREN   tilde->TILDE
    amp->AMP   bar->BAR   plus->PLUS   star->STAR   minus->MINUS   arrow->ARROW   lt->LT   lt_minus (accepts nothing)
    iff->IFF   eq->EQ   eqeq->EQEQ

    transitions (state, class) -> state
    start:    alpha->name  digit->int  space->ws  (->lparen  )->rparen  ~->tilde  &->amp  |->bar  +->plus  *->star
              -->minus  <->lt  =->eq
    name:     alpha->name  digit->name
    int:      digit->int
    ws:       space->ws
    minus:    >->arrow
    lt:       -->lt_minus
    lt_minus: >->iff
    eq:       =->eqeq
    (no other transitions exist)

MAXIMAL MUNCH WITH BACKTRACKING (the rule ``tokenize`` implements): from position ``i`` run the DFA as far as it can go,
remembering the LAST position at which the state was accepting. Emit the token for that position and restart there.
``<->`` is one IFF token. But ``<-b`` is LT then MINUS then NAME: the run ``<-`` ends in the non-accepting state
``lt_minus``, so the lexer falls back to the last accepting position (after ``<``). ``<-`` at end of input is LT, MINUS.
``===`` is EQEQ, EQ. ``->>`` is ARROW followed by a LexError at the ``>``. If no accepting position was ever reached the
character at ``i`` is illegal: ``LexError`` with ``offset == i`` (every transition out of ``start`` leads to an accepting
state, so this only happens for a character with no transition out of ``start``).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from .errors import LexError  # noqa: F401  (raised by tokenize)

FORMULA_KEYWORDS = frozenset({"true", "false"})
CALC_KEYWORDS = frozenset({"true", "false", "let", "in", "if", "then", "else", "and", "or", "not"})
CHAR_CLASS_NAMES = frozenset({"alpha", "digit", "space", "(", ")", "~", "&", "|", "+", "*", "-", "<", ">", "=", "other"})


@dataclass(frozen=True)
class Token:
    """``kind`` (see module docstring), the exact source ``text``, and ``start``/``end`` offsets with
    ``end == start + len(text)`` and ``text == source[start:end]``."""

    kind: str
    text: str
    start: int
    end: int


@dataclass(frozen=True)
class DFA:
    """``start``: the start state name. ``transitions``: ``(state, char_class) -> state``. ``accepting``: ``state ->
    token kind`` (a state absent from it is not accepting)."""

    start: str
    transitions: Mapping[tuple[str, str], str]
    accepting: Mapping[str, str]


def char_class(ch: str) -> str:
    """Class name of ONE character per the table in the module docstring (ASCII only; anything else is ``"other"``).
    ``ch`` must be a ``str`` of length 1 (else ``ValueError``; a non-str is ``TypeError``)."""
    raise NotImplementedError


def default_dfa() -> DFA:
    """The DFA of the module docstring as a :class:`DFA` (fresh dicts or read-only mappings; callers must not be able
    to corrupt later calls by mutating the result)."""
    raise NotImplementedError


def tokenize(
    text: str,
    keywords: frozenset[str] = frozenset(),
    *,
    keep_whitespace: bool = False,
    dfa: DFA | None = None,
) -> list[Token]:
    """Split ``text`` into tokens by maximal munch (module docstring). ``dfa=None`` means ``default_dfa()``; a caller may
    pass a modified DFA and the result MUST follow that table (the table is the single source of truth).

    * WS tokens are dropped unless ``keep_whitespace`` is true.
    * A NAME whose whole text is in ``keywords`` gets the keyword kind (``text.upper()``); its ``text`` is unchanged.
    * The result covers the input exactly when ``keep_whitespace`` is true: consecutive tokens satisfy
      ``tokens[k].end == tokens[k+1].start`` and the concatenated texts equal ``text``.
    * ``""`` -> ``[]``. A non-``str`` ``text`` is a ``TypeError``.
    * Illegal character -> ``LexError`` whose ``offset`` is its index (the FIRST illegal character; nothing is returned).
    * Must be iterative and linear-time in ``len(text)`` apart from the bounded backtrack (at most 1 character).
    """
    raise NotImplementedError
