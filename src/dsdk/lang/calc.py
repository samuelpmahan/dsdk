"""Calc: a tiny typed expression language, with a parser, a type checker, and two semantics (big-step, small-step).

ABSTRACT SYNTAX -- immutable, hashable, structurally comparable (frozen dataclasses, all subclasses of :class:`Expr`)::

    IntLit(value: int)            Python int, any sign, arbitrary size. ``bool`` is NOT accepted (TypeError).
    BoolLit(value: bool)          exactly a bool (``BoolLit(1)`` is a TypeError)
    Var(name: str)                ``[A-Za-z_][A-Za-z0-9_]*`` ASCII, and not a Calc keyword (TypeError if not a str,
                                  ValueError otherwise). Keywords: true false let in if then else and or not
    BinOp(op: str, left, right)   ``op`` is one of ``OPS = ("+", "-", "*", "<", "==", "and", "or")`` (else ValueError)
    Not(operand)
    If(cond, then, orelse)
    Let(name: str, bound, body)   ``let name = bound in body``; ``name`` is validated like ``Var.name``

Every child must be an :class:`Expr` (else TypeError). Validation lives in ``Expr.__post_init__``. Equality is structural.
``IntLit(1) != BoolLit(True)`` and ``BinOp("+", a, b) != BinOp("+", b, a)``. VALUES are exactly ``IntLit`` and ``BoolLit``.

CONCRETE SYNTAX (parsed by :func:`parse_calc`, tokens from :mod:`dsdk.lang.lexer` with ``CALC_KEYWORDS``, whitespace free)::

    expr   := LET NAME EQ expr IN expr            ``let x = e1 in e2``  (body extends as far right as possible)
            | IF expr THEN expr ELSE expr         (else-branch extends as far right as possible)
            | or_e
    or_e   := and_e ( OR and_e )*                 left-associative
    and_e  := not_e ( AND not_e )*                left-associative
    not_e  := NOT not_e | cmp                     ``not`` binds LOOSER than ``<`` ``==``: ``not 1 < 2`` is ``not (1 < 2)``,
                                                  and TIGHTER than ``and``: ``not a and b`` is ``(not a) and b``
    cmp    := add ( (LT | EQEQ) add )?            NON-associative: ``1 < 2 < 3`` is a ParseError at the second ``<``
    add    := mul ( (PLUS | MINUS) mul )*         left-associative
    mul    := atom ( STAR atom )*                 left-associative
    atom   := INT | MINUS INT | TRUE | FALSE | NAME | LPAREN expr RPAREN

``MINUS INT`` in OPERAND position is a negative literal ``IntLit(-n)`` (``-0`` is ``IntLit(0)``); a ``-`` after a complete
operand is subtraction, so ``1 -2`` is ``1 - 2`` and ``1 - -2`` is ``BinOp("-", 1, IntLit(-2))``. ``-x`` and ``--2`` are
ParseErrors (expected ``{"INT"}``). ``let`` / ``if`` are only allowed where an ``expr`` is, not as an operand of an operator:
``1 + let x = 2 in x`` is a ParseError (wrap it in parentheses). ``INT`` followed by ``NAME`` (``12ab``) is simply two
tokens, hence a ParseError. Integer literals are exact (``int(text)``); ``007`` is ``IntLit(7)``.

CANONICAL SOURCE (:func:`to_source`), fully parenthesised, single spaces, parseable by ``parse_calc``::

    IntLit(3) -> 3    IntLit(-3) -> -3    BoolLit(True) -> true    Var("x") -> x
    BinOp(op, l, r) -> (<l> <op> <r>)            e.g. (1 + 2)   (a and b)   (x == 3)
    Not(e) -> (not <e>)     If(c, t, e) -> (if <c> then <t> else <e>)     Let(x, b, e) -> (let x = <b> in <e>)

``parse_calc(to_source(e)) == e`` for EVERY Expr ``e`` (this is why negative literals exist).

TYPES. ``Type.INT`` / ``Type.BOOL``. Typing rules (``Γ`` = environment name -> Type)::

    IntLit: Int      BoolLit: Bool      Var x: Γ(x)  (unbound -> error)
    l, r : Int   =>  l + r, l - r, l * r : Int        l, r : Int  =>  l < r : Bool
    l, r : T (the SAME T, Int or Bool)  =>  l == r : Bool
    l, r : Bool  =>  l and r, l or r : Bool           e : Bool  =>  not e : Bool
    c : Bool, t : T, e : T  =>  if c then t else e : T        e1 : T1, e2 : T2 under Γ[x:=T1]  =>  let x = e1 in e2 : T2

``typecheck`` visits children in source order (If: cond, then, orelse; Let: bound, then body in the extended environment)
and reports the FIRST failure in that post-order, so an error inside a child beats an error of its parent. Reasons are
exactly ``f"{tag}: {to_source(node)}"`` where ``node`` is the offending node and ``tag`` is

    "unbound variable"        node is the ``Var`` (reason ``unbound variable: x``)
    "operand type mismatch"   node is the BinOp / Not whose operand types do not fit its rule (including ``==`` with an Int
                              on one side and a Bool on the other)
    "condition not Bool"      node is the ``If`` whose cond is not Bool (checked BEFORE the branches)
    "branch type mismatch"    node is the ``If`` whose branches have different types

SMALL-STEP SEMANTICS (:func:`step`), call-by-value, left-to-right, leftmost-innermost. ``e -> e'`` means ``step(e) == e'``.
A term that is a value, or to which no rule applies, has ``step(e) is None``. EXACT rules (``v`` stands for a value):

    BinOp(op, l, r), op in + - * < ==:
      B1  l is not a value and l -> l'                       =>  BinOp(op, l', r)
      B2  l = v is a value, r is not a value and r -> r'     =>  BinOp(op, v, r')
      B3  l, r both values: IntLit/IntLit for + - * <  => IntLit(a+b | a-b | a*b) / BoolLit(a < b);
          == on IntLit/IntLit or on BoolLit/BoolLit => BoolLit(a == b). Any other pair of values (``1 + true``, ``true < 2``,
          ``1 == true``) has NO rule: STUCK.   (Never use Python's ``True == 1``: ``1 == true`` must be stuck.)
    BinOp("and", l, r):
      A1  l is not a value and l -> l'                 =>  BinOp("and", l', r)
      A2  l = BoolLit(False)                           =>  BoolLit(False)      (r is discarded UNEXAMINED, even if ill-typed)
      A3  l = BoolLit(True)                            =>  r
      (l = IntLit: no rule, stuck.)   ``or`` mirrors it: O1 congruence on l; BoolLit(True) or r => BoolLit(True);
      BoolLit(False) or r => r.   There is no rule that steps into r while l is still a non-value, nor into r under A2.
    Not(e):   N1 e -> e' => Not(e');   Not(BoolLit(b)) => BoolLit(not b);   Not(IntLit) stuck.
    If(c, t, e):  I1 c -> c' => If(c', t, e);   If(BoolLit(True), t, e) => t;   If(BoolLit(False), t, e) => e;
                  If(IntLit, ...) stuck. The branch not taken is discarded unexamined.
    Let(x, b, e): L1 b -> b' => Let(x, b', e);    Let(x, v, e) with v a value => substitute(e, x, v)
    IntLit, BoolLit: values, no rule.     Var: no rule (a free variable is STUCK, it is not a value).
    If a sub-term in an evaluation position is stuck, so is the whole term (no rule can skip over it): the evaluation
    positions are BinOp's l (then r, but for and/or only l), Not's operand, If's cond, Let's bound.

THREE DIFFERENT OUTCOMES (:func:`classify`): ``Outcome.VALUE`` (the term is IntLit/BoolLit), ``Outcome.STEP`` (a rule
applies), ``Outcome.STUCK`` (not a value, no rule applies). A STATIC type error (``typecheck`` INVALID) is a third,
independent thing: ``if true then 1 else (1 + true)`` is ill-typed yet evaluates to ``1`` and never gets stuck, while
``(1 + true)`` is both ill-typed and stuck.

BIG-STEP :func:`evaluate` is an independent reference implementation of the same semantics (it must not call ``step``):
it returns a Python ``int`` or ``bool`` or raises :class:`StuckError`. Same evaluation order and same short-circuiting as
the small-step rules (so ``evaluate(e)`` equals the value at the end of ``trace(e)`` for EVERY e, well-typed or not, and
raises StuckError exactly when the trace ends in a stuck term).

TERMINATION. ``size(step(e)) < size(e)`` for every e that steps (see tracks/A2/PROOFS.md), hence
``len(trace(e)) - 1 <= size(e) - 1`` and every trace is finite.

DEPTH. Every function here must handle terms nested 200 levels deep under Python's default recursion limit (A1 convention):
recursion is fine only if it uses at most about 2 Python frames per nesting level; iterative implementations are fine too.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Mapping

from dsdk.core import Judgment, Status  # noqa: F401  (typecheck returns a Judgment)

from .errors import ParseError  # noqa: F401  (raised by parse_calc)
from .lexer import CALC_KEYWORDS, tokenize  # noqa: F401  (used by parse_calc)

OPS = ("+", "-", "*", "<", "==", "and", "or")


class Type(Enum):
    INT = "Int"
    BOOL = "Bool"


class Outcome(Enum):
    VALUE = "value"
    STEP = "step"
    STUCK = "stuck"


class StuckError(Exception):
    """``evaluate`` got stuck. ``.term`` is the Expr that was passed to ``evaluate``. Raise as ``StuckError(term)``."""

    def __init__(self, term: "Expr") -> None:
        super().__init__("evaluation got stuck")
        self.term = term


class Expr:
    """Base class of all Calc nodes. Never instantiate directly."""

    def __post_init__(self) -> None:
        # Validation rules are in the module docstring. Implemented once here for all subclasses (see task T09).
        t = type(self)
        if t is IntLit:
            if type(self.value) is not int:
                raise TypeError(f"IntLit.value must be an int, not {type(self.value).__name__}")
        elif t is BoolLit:
            if type(self.value) is not bool:
                raise TypeError(f"BoolLit.value must be a bool, not {type(self.value).__name__}")
        elif t is Var or t is Let:
            if not isinstance(self.name, str):
                raise TypeError(f"{t.__name__} name must be a str, not {type(self.name).__name__}")
            if not re.fullmatch(_NAME_PATTERN, self.name, re.ASCII) or self.name in CALC_KEYWORDS:
                raise ValueError(f"invalid {t.__name__} name: {self.name!r}")
        elif t is BinOp:
            if self.op not in OPS:
                raise ValueError(f"unknown BinOp operator: {self.op!r}")
        for field_name in _CHILD_FIELDS.get(t, ()):
            child = getattr(self, field_name)
            if not isinstance(child, Expr):
                raise TypeError(f"{t.__name__}.{field_name} must be an Expr, not {type(child).__name__}")


@dataclass(frozen=True)
class IntLit(Expr):
    value: int


@dataclass(frozen=True)
class BoolLit(Expr):
    value: bool


@dataclass(frozen=True)
class Var(Expr):
    name: str


@dataclass(frozen=True)
class BinOp(Expr):
    op: str
    left: Expr
    right: Expr


@dataclass(frozen=True)
class Not(Expr):
    operand: Expr


@dataclass(frozen=True)
class If(Expr):
    cond: Expr
    then: Expr
    orelse: Expr


@dataclass(frozen=True)
class Let(Expr):
    name: str
    bound: Expr
    body: Expr


# ----------------------------------------------------------------------------- structure
_NAME_PATTERN = r"[A-Za-z_][A-Za-z0-9_]*"

_CHILD_FIELDS = {
    BinOp: ("left", "right"),
    Not: ("operand",),
    If: ("cond", "then", "orelse"),
    Let: ("bound", "body"),
}


def _require_expr(x: object) -> None:
    if not isinstance(x, Expr):
        raise TypeError(f"expected a Calc Expr, not {type(x).__name__}")


def _children(e: Expr) -> tuple[Expr, ...]:
    if isinstance(e, BinOp):
        return (e.left, e.right)
    if isinstance(e, Not):
        return (e.operand,)
    if isinstance(e, If):
        return (e.cond, e.then, e.orelse)
    if isinstance(e, Let):
        return (e.bound, e.body)
    return ()


def size(e: Expr) -> int:
    """Tree size: number of Expr nodes counting every occurrence. Literals and Var are 1; ``BinOp``/``Let`` are
    ``1 + size(l) + size(r)`` (the binder NAME is not a node); ``Not`` is ``1 + size(operand)``; ``If`` is
    ``1 + size(cond) + size(then) + size(orelse)``. ``TypeError`` if ``e`` is not an Expr."""
    _require_expr(e)
    count = 0
    stack: list[Expr] = [e]
    while stack:
        node = stack.pop()
        count += 1
        stack.extend(_children(node))
    return count


def free_vars(e: Expr) -> frozenset[str]:
    """Names occurring free. ``Let(x, b, body)``: free(b) | (free(body) - {x}) -- note ``x`` stays free in ``b``:
    ``free_vars(parse_calc("let x = x in x")) == {"x"}``. ``TypeError`` if ``e`` is not an Expr."""
    _require_expr(e)
    return _free(e)


def _free(e: Expr) -> frozenset[str]:
    if isinstance(e, Var):
        return frozenset({e.name})
    if isinstance(e, Let):
        return _free(e.bound) | (_free(e.body) - {e.name})
    out: frozenset[str] = frozenset()
    for child in _children(e):
        out |= _free(child)
    return out


def substitute(e: Expr, name: str, value: Expr) -> Expr:
    """``e[name := value]``: replace every FREE occurrence of ``Var(name)`` by ``value``.

    ``value`` must be an ``IntLit`` or ``BoolLit`` (anything else: ``TypeError``) -- only closed values are ever substituted,
    so variable capture cannot happen. Shadowing: for ``Let(y, b, body)`` substitute into ``b`` ALWAYS, and into ``body``
    ONLY IF ``y != name``. ``substitute(parse_calc("let x = x in x"), "x", IntLit(1))`` is
    ``Let("x", IntLit(1), Var("x"))``. Returns an equal Expr when ``name`` is not free. ``TypeError`` if ``e`` is not an Expr
    or ``name`` is not a str.
    """
    _require_expr(e)
    if not isinstance(name, str):
        raise TypeError(f"name must be a str, not {type(name).__name__}")
    if not isinstance(value, (IntLit, BoolLit)):
        raise TypeError(f"value must be an IntLit or BoolLit, not {type(value).__name__}")
    return _subst(e, name, value)


def _subst(e: Expr, name: str, value: Expr) -> Expr:
    if isinstance(e, Var):
        return value if e.name == name else e
    if isinstance(e, (IntLit, BoolLit)):
        return e
    if isinstance(e, BinOp):
        return BinOp(e.op, _subst(e.left, name, value), _subst(e.right, name, value))
    if isinstance(e, Not):
        return Not(_subst(e.operand, name, value))
    if isinstance(e, If):
        return If(_subst(e.cond, name, value), _subst(e.then, name, value), _subst(e.orelse, name, value))
    # Let: the bound expression is always searched; the body only when the binder does not shadow `name`.
    bound = _subst(e.bound, name, value)
    body = _subst(e.body, name, value) if e.name != name else e.body
    return Let(e.name, bound, body)


def is_value(e: Expr) -> bool:
    """True exactly for ``IntLit`` and ``BoolLit``. ``TypeError`` for a non-Expr."""
    _require_expr(e)
    return isinstance(e, (IntLit, BoolLit))


def to_python(v: Expr) -> int | bool:
    """The Python value of a value node: ``IntLit(3) -> 3`` (an ``int``), ``BoolLit(True) -> True`` (a ``bool``).
    ``ValueError`` if ``v`` is an Expr but not a value; ``TypeError`` if it is not an Expr."""
    _require_expr(v)
    if not is_value(v):
        raise ValueError(f"not a value: {to_source(v)}")
    return v.value


def from_python(x: int | bool) -> Expr:
    """Inverse of ``to_python``. CHECK ``bool`` FIRST (``isinstance(True, int)`` is true): ``from_python(True)`` is
    ``BoolLit(True)``, ``from_python(1)`` is ``IntLit(1)``. Anything else: ``TypeError``."""
    if isinstance(x, bool):
        return BoolLit(x)
    if isinstance(x, int):
        return IntLit(x)
    raise TypeError(f"not a Calc value: {type(x).__name__}")


# ----------------------------------------------------------------------------- syntax
def to_source(e: Expr) -> str:
    """Canonical fully-parenthesised source (module docstring). ``TypeError`` if ``e`` is not an Expr."""
    _require_expr(e)
    return _src(e)


def _src(e: Expr) -> str:
    if isinstance(e, IntLit):
        return str(e.value)
    if isinstance(e, BoolLit):
        return "true" if e.value else "false"
    if isinstance(e, Var):
        return e.name
    if isinstance(e, BinOp):
        return f"({_src(e.left)} {e.op} {_src(e.right)})"
    if isinstance(e, Not):
        return f"(not {_src(e.operand)})"
    if isinstance(e, If):
        return f"(if {_src(e.cond)} then {_src(e.then)} else {_src(e.orelse)})"
    return f"(let {e.name} = {_src(e.bound)} in {_src(e.body)})"


def parse_calc(text: str) -> Expr:
    """Parse concrete syntax (module docstring) with ``tokenize(text, CALC_KEYWORDS)``.

    * LEXING FIRST: an illegal character anywhere is a ``LexError`` even if a ParseError comes earlier in the text.
    * ``ParseError`` with ``offset`` = start of the first token that cannot continue a valid program (or ``len(text)`` if the
      input ends too early) and non-empty ``expected``. ``expected`` must contain the kind that the grammar REQUIRES at that
      point when exactly one construct is possible, and may also contain operator kinds. Required kinds: after the
      condition of ``if`` -> ``"THEN"``; after the then-branch -> ``"ELSE"``; after ``let`` -> ``"NAME"``; after
      ``let x`` -> ``"EQ"``; after the bound expression of ``let`` -> ``"IN"``; an unclosed ``(`` at end of input or at a
      token that cannot continue -> ``"RPAREN"``; a negative sign followed by a non-INT -> exactly ``{"INT"}``;
      wanting an operand -> contains ``{"INT", "MINUS", "TRUE", "FALSE", "NAME", "LPAREN"}``; a finished program followed
      by extra tokens -> contains ``"END"``.
    * ``""`` and whitespace-only input are a ParseError at offset ``len(text)``.
    * Nesting depth 200 of ``(``, of ``not``, of ``let ... in`` bodies and of left chains ``1 + 1 + ... + 1`` must not raise
      ``RecursionError`` (loop for left-associative chains; at most 3 Python frames per nesting level otherwise).
    """
    tokens = tokenize(text, CALC_KEYWORDS)
    pos = 0
    # token kind -> (precedence, operator string); all left-associative (see ``expr``).
    binops = {
        "OR": (1, "or"), "AND": (2, "and"), "LT": (4, "<"), "EQEQ": (4, "=="),
        "PLUS": (5, "+"), "MINUS": (5, "-"), "STAR": (6, "*"),
    }

    def peek_kind():
        return tokens[pos].kind if pos < len(tokens) else None

    def take():
        nonlocal pos
        tok = tokens[pos]
        pos += 1
        return tok

    def fail(expected):
        if pos < len(tokens):
            tok = tokens[pos]
            return ParseError(f"unexpected {tok.text!r}", tok.start, expected)
        return ParseError("unexpected end of input", len(text), expected)

    def eat(kind):
        if peek_kind() != kind:
            raise fail({kind})
        return take()

    def prefix(min_prec):
        # The start of an operand. let/if/not are only legal where the grammar allows them (see module docstring).
        kind = peek_kind()
        if kind == "LET" and min_prec == 0:
            take()
            name = eat("NAME").text
            eat("EQ")
            bound = expr(0)
            eat("IN")
            return Let(name, bound, expr(0))
        if kind == "IF" and min_prec == 0:
            take()
            cond = expr(0)
            eat("THEN")
            then = expr(0)
            eat("ELSE")
            return If(cond, then, expr(0))
        if kind == "NOT" and min_prec <= 3:
            take()
            return Not(expr(3))
        if kind == "INT":
            return IntLit(int(take().text))
        if kind == "MINUS":
            take()
            if peek_kind() != "INT":
                raise fail({"INT"})
            return IntLit(-int(take().text))
        if kind == "TRUE":
            take()
            return BoolLit(True)
        if kind == "FALSE":
            take()
            return BoolLit(False)
        if kind == "NAME":
            return Var(take().text)
        if kind == "LPAREN":
            take()
            inner = expr(0)
            eat("RPAREN")
            return inner
        expected = {"INT", "MINUS", "TRUE", "FALSE", "NAME", "LPAREN"}
        if min_prec <= 3:
            expected.add("NOT")
        if min_prec == 0:
            expected.update(("LET", "IF"))
        raise fail(expected)

    def expr(min_prec):
        # Precedence climbing. ``chained`` is true when the left operand is a comparison, or a ``not`` whose operand
        # stopped at a comparison; a further comparison operator then ends this loop (comparisons do not chain).
        chained = peek_kind() == "NOT"
        left = prefix(min_prec)
        while True:
            op = binops.get(peek_kind())
            if op is None or op[0] < min_prec or (op[0] == 4 and chained):
                return left
            take()
            prec, name = op
            left = BinOp(name, left, expr(prec + 1))
            chained = prec == 4

    result = expr(0)
    if pos < len(tokens):
        raise fail({"END"})
    return result


# ----------------------------------------------------------------------------- typing
class _IllTyped(Exception):
    """Internal: carries the INVALID reason out of :func:`_check`."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


def _fail(tag: str, node: Expr) -> _IllTyped:
    return _IllTyped(f"{tag}: {to_source(node)}")


def _check(e: Expr, env: dict[str, Type]) -> Type:
    """Type of ``e`` in ``env`` (never mutated). Children are typed first, left to right; then the node's own rule."""
    if isinstance(e, IntLit):
        return Type.INT
    if isinstance(e, BoolLit):
        return Type.BOOL
    if isinstance(e, Var):
        if e.name not in env:
            raise _fail("unbound variable", e)
        return env[e.name]
    if isinstance(e, BinOp):
        lt = _check(e.left, env)
        rt = _check(e.right, env)
        if e.op in ("+", "-", "*", "<"):
            if lt is not Type.INT or rt is not Type.INT:
                raise _fail("operand type mismatch", e)
            return Type.BOOL if e.op == "<" else Type.INT
        if e.op == "==":
            if lt is not rt:
                raise _fail("operand type mismatch", e)
            return Type.BOOL
        # and / or
        if lt is not Type.BOOL or rt is not Type.BOOL:
            raise _fail("operand type mismatch", e)
        return Type.BOOL
    if isinstance(e, Not):
        if _check(e.operand, env) is not Type.BOOL:
            raise _fail("operand type mismatch", e)
        return Type.BOOL
    if isinstance(e, If):
        ct = _check(e.cond, env)
        tt = _check(e.then, env)
        et = _check(e.orelse, env)
        if ct is not Type.BOOL:
            raise _fail("condition not Bool", e)
        if tt is not et:
            raise _fail("branch type mismatch", e)
        return tt
    # Let: the body sees the binder in a fresh copy of the environment (no leak to siblings or the caller).
    bt = _check(e.bound, env)
    return _check(e.body, {**env, e.name: bt})


def typecheck(e: Expr, env: Mapping[str, Type] | None = None) -> Judgment:
    """Static type of ``e`` under ``env`` (``None`` = empty; never mutated).

    ``Judgment(Status.KNOWN, Type.X)`` when well-typed (reason ``""``); otherwise ``Judgment(Status.INVALID, None, reason)``
    with ``reason == f"{tag}: {to_source(node)}"`` as specified in the module docstring. Never raises for an ill-typed
    program (that is what INVALID is for); ``TypeError`` only if ``e`` is not an Expr.
    """
    _require_expr(e)
    try:
        ty = _check(e, dict(env) if env is not None else {})
    except _IllTyped as exc:
        return Judgment(Status.INVALID, None, exc.reason)
    return Judgment(Status.KNOWN, ty)


# ----------------------------------------------------------------------------- semantics
def step(e: Expr) -> Expr | None:
    """One small-step reduction per the exact rules in the module docstring, or ``None`` if ``e`` is a value or stuck.
    ``TypeError`` for a non-Expr."""
    _require_expr(e)
    if isinstance(e, BinOp):
        if e.op in ("and", "or"):
            if not is_value(e.left):
                nl = step(e.left)
                return None if nl is None else BinOp(e.op, nl, e.right)
            if not isinstance(e.left, BoolLit):
                return None
            if e.op == "and":
                return e.right if e.left.value else BoolLit(False)
            return BoolLit(True) if e.left.value else e.right
        if not is_value(e.left):
            nl = step(e.left)
            return None if nl is None else BinOp(e.op, nl, e.right)
        if not is_value(e.right):
            nr = step(e.right)
            return None if nr is None else BinOp(e.op, e.left, nr)
        l, r = e.left, e.right
        if isinstance(l, IntLit) and isinstance(r, IntLit):
            if e.op == "+":
                return IntLit(l.value + r.value)
            if e.op == "-":
                return IntLit(l.value - r.value)
            if e.op == "*":
                return IntLit(l.value * r.value)
            if e.op == "<":
                return BoolLit(l.value < r.value)
            if e.op == "==":
                return BoolLit(l.value == r.value)
            return None
        if isinstance(l, BoolLit) and isinstance(r, BoolLit) and e.op == "==":
            return BoolLit(l.value == r.value)
        return None
    if isinstance(e, Not):
        if not is_value(e.operand):
            no = step(e.operand)
            return None if no is None else Not(no)
        if isinstance(e.operand, BoolLit):
            return BoolLit(not e.operand.value)
        return None
    if isinstance(e, If):
        if not is_value(e.cond):
            nc = step(e.cond)
            return None if nc is None else If(nc, e.then, e.orelse)
        if isinstance(e.cond, BoolLit):
            return e.then if e.cond.value else e.orelse
        return None
    if isinstance(e, Let):
        if not is_value(e.bound):
            nb = step(e.bound)
            return None if nb is None else Let(e.name, nb, e.body)
        return substitute(e.body, e.name, e.bound)
    return None


def classify(e: Expr) -> Outcome:
    """``Outcome.VALUE`` if ``is_value(e)``; else ``Outcome.STEP`` if ``step(e) is not None``; else ``Outcome.STUCK``."""
    if is_value(e):
        return Outcome.VALUE
    return Outcome.STEP if step(e) is not None else Outcome.STUCK


def trace(e: Expr) -> list[Expr]:
    """``[e0, e1, ..., en]`` with ``e0 == e``, ``e(i+1) == step(e(i))`` and ``step(en) is None``. So ``len(trace(e)) - 1`` is
    the number of steps; the last element is a value or a stuck term (use :func:`classify`); a value gives ``[e]``.
    Never raises StuckError. ``TypeError`` for a non-Expr."""
    _require_expr(e)
    out = [e]
    while True:
        nxt = step(out[-1])
        if nxt is None:
            return out
        out.append(nxt)


class _Stuck(Exception):
    """Internal: raised by :func:`_go` when evaluation gets stuck; converted to StuckError by :func:`evaluate`."""


def _go(e: Expr, env: dict[str, int | bool]) -> int | bool:
    """Environment-based evaluation of ``e``; same order and short-circuiting as the small-step rules."""
    if isinstance(e, (IntLit, BoolLit)):
        return e.value
    if isinstance(e, Var):
        if e.name not in env:
            raise _Stuck()
        return env[e.name]
    if isinstance(e, Not):
        v = _go(e.operand, env)
        if type(v) is not bool:
            raise _Stuck()
        return not v
    if isinstance(e, If):
        c = _go(e.cond, env)
        if type(c) is not bool:
            raise _Stuck()
        return _go(e.then if c else e.orelse, env)
    if isinstance(e, Let):
        v = _go(e.bound, env)
        return _go(e.body, {**env, e.name: v})
    if e.op in ("and", "or"):
        left = _go(e.left, env)
        if type(left) is not bool:
            raise _Stuck()
        if e.op == "and":
            return _go(e.right, env) if left else False
        return True if left else _go(e.right, env)
    lv = _go(e.left, env)
    rv = _go(e.right, env)
    if type(lv) is int and type(rv) is int:
        if e.op == "+":
            return lv + rv
        if e.op == "-":
            return lv - rv
        if e.op == "*":
            return lv * rv
        if e.op == "<":
            return lv < rv
        return lv == rv  # "=="
    if e.op == "==" and type(lv) is bool and type(rv) is bool:
        return lv == rv
    raise _Stuck()


def evaluate(e: Expr) -> int | bool:
    """Big-step reference evaluator (module docstring). Returns a Python ``int`` (for Int results) or ``bool`` (for Bool
    results; use ``type(x) is bool`` to tell them apart, never ``== 1``). Arithmetic is exact Python int arithmetic.
    Raises :class:`StuckError` (with ``.term`` = ``e``) when evaluation gets stuck, including for free variables.
    MUST NOT call ``step``/``trace`` (it is the independent oracle the tests compare them against)."""
    _require_expr(e)
    try:
        return _go(e, {})
    except _Stuck:
        raise StuckError(e) from None
