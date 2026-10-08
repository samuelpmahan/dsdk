"""Propositional formulas as an immutable, hashable AST.

Node classes (all frozen dataclasses, all subclasses of :class:`Formula`):

    Const(value: bool)         Var(name: str)          Not(operand)
    And(left, right)           Or(left, right)
    Implies(left, right)       Iff(left, right)

Construction rules (checked in ``Formula.__post_init__``; exception types are
part of the contract):

* ``Const.value`` must be exactly a ``bool`` (``Const(1)`` is a ``TypeError``).
* ``Var.name`` must be a ``str`` (else ``TypeError``) matching the ASCII regex
  ``[A-Za-z_][A-Za-z0-9_]*`` and not equal to ``"true"`` or ``"false"``
  (else ``ValueError``). ``"P12"``, ``"_x"``, ``"True"`` are fine; ``""``,
  ``"1a"``, ``"a b"``, ``"é"``, ``"true"`` are not.
* Every operand/left/right must be a :class:`Formula` (else ``TypeError``).

Equality is STRUCTURAL and class-sensitive; equal formulas hash equal, and
formulas are usable as dict keys / set members. ``And(a, b) != And(b, a)`` and
``And(And(a, b), c) != And(a, And(b, c))`` -- no normalisation is performed.

Depth: every function in this package must work on formulas nested 200 levels
deep under Python's DEFAULT recursion limit. Recursion is therefore allowed
only if it fits; iterative (explicit stack) implementations are recommended.

Canonical string grammar (what :func:`to_str` emits; track A2 will write a
parser that must round-trip it). Fully parenthesised, ASCII, exactly one space
around binary operators, none after ``~``::

    formula := atom
             | "(" "~" formula ")"
             | "(" formula " & "   formula ")"
             | "(" formula " | "   formula ")"
             | "(" formula " -> "  formula ")"
             | "(" formula " <-> " formula ")"
    atom    := "true" | "false" | NAME
    NAME    := [A-Za-z_][A-Za-z0-9_]*   (but not "true" / "false")

Examples::

    Var("a")                                  -> a
    Const(True)                               -> true
    Not(Var("a"))                             -> (~a)
    Not(Not(Var("a")))                        -> (~(~a))
    And(Var("a"), Or(Var("b"), Const(False))) -> (a & (b | false))
    Implies(And(Var("a"), Var("b")), Var("c"))-> ((a & b) -> c)
    And(And(Var("a"), Var("b")), Var("c"))    -> ((a & b) & c)
    Iff(Var("B11"), Or(Var("P12"), Var("P21")))-> (B11 <-> (P12 | P21))
"""
from __future__ import annotations

from dataclasses import dataclass


class Formula:
    """Base class of all formula nodes. Never instantiate directly."""

    def __post_init__(self) -> None:
        raise NotImplementedError


@dataclass(frozen=True)
class Const(Formula):
    value: bool


@dataclass(frozen=True)
class Var(Formula):
    name: str


@dataclass(frozen=True)
class Not(Formula):
    operand: Formula


@dataclass(frozen=True)
class And(Formula):
    left: Formula
    right: Formula


@dataclass(frozen=True)
class Or(Formula):
    left: Formula
    right: Formula


@dataclass(frozen=True)
class Implies(Formula):
    left: Formula
    right: Formula


@dataclass(frozen=True)
class Iff(Formula):
    left: Formula
    right: Formula


def variables(f: Formula) -> frozenset[str]:
    """Names of all :class:`Var` nodes in ``f`` (``Const``-only -> empty set).

    ``TypeError`` if ``f`` is not a :class:`Formula`.
    """
    raise NotImplementedError


def size(f: Formula) -> int:
    """Number of AST nodes, counting every occurrence (it is a TREE size).

    ``size(Var("a")) == size(Const(True)) == 1``; ``size(Not(x)) == 1 + size(x)``;
    ``size(And(x, y)) == 1 + size(x) + size(y)`` (same for Or/Implies/Iff).
    Repeated sub-formulas are counted each time: ``size(And(a, a)) == 3``.
    """
    raise NotImplementedError


def to_str(f: Formula) -> str:
    """Canonical string per the grammar in the module docstring."""
    raise NotImplementedError
