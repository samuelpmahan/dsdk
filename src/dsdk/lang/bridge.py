"""Two genuine cross-track links: A1 (propositional logic) -> A2 (Calc), and A2 (Calc evaluation) -> A0 (PxC lineage).

1. :func:`from_formula` embeds ``dsdk.logic`` formulas into Calc's Bool fragment, and :func:`bind_assignment` encodes an
   assignment as nested ``let``s, so that  ``calc.evaluate(bind_assignment(from_formula(f), a)) == logic.evaluate(f, a)``.
2. :func:`trace_into_pxc` records a Calc evaluation as a chain of ``dsdk.core`` Parts: one Part per small step, each Part's
   ``composition.inputs["prev"]`` being the Part of the previous step. Track A5 (graphs) traverses this chain.
"""
from __future__ import annotations

from typing import Mapping

from dsdk import logic
from dsdk.core import Part, PxC

from . import calc


def from_formula(f: logic.Formula) -> calc.Expr:
    """Translate a logic Formula to a Calc Expr (structure-directed, EXACT shapes)::

        Const(b)      -> BoolLit(b)              Var(n)        -> calc.Var(n)
        Not(x)        -> Not(T(x))               And(x, y)     -> BinOp("and", T(x), T(y))
        Or(x, y)      -> BinOp("or",  T(x), T(y))
        Implies(x, y) -> BinOp("or", Not(T(x)), T(y))          (material implication)
        Iff(x, y)     -> BinOp("==", T(x), T(y))               (== on two Bools)

    ``ValueError`` if a variable name is a Calc keyword (``Var("not")`` is a legal logic variable but not a legal Calc
    variable). ``TypeError`` if ``f`` is not a ``logic.Formula``. Must work on formulas nested 200 levels deep
    (see the depth convention in dsdk.logic.formula / dsdk.lang.calc).
    """
    raise NotImplementedError


def bind_assignment(e: calc.Expr, assignment: Mapping[str, bool]) -> calc.Expr:
    """Wrap ``e`` in one ``Let`` per assignment entry: names in ASCENDING ``sorted()`` order, the FIRST (smallest) name
    OUTERMOST, each bound to ``BoolLit(value)``. ``{"a": True, "b": False}`` ->
    ``Let("a", BoolLit(True), Let("b", BoolLit(False), e))``; an empty assignment returns ``e`` itself.
    A value that is not exactly a ``bool`` is a ``TypeError`` (like ``logic.evaluate``). Extra names are bound too (harmless).
    """
    raise NotImplementedError


def trace_into_pxc(expr: calc.Expr, store: PxC, prefix: str) -> Part:
    """Record ``calc.trace(expr)`` in ``store`` as a lineage chain, atomically, and return the LAST step's Part.

    Let ``steps = calc.trace(expr)`` (``n + 1`` terms). Inside ONE ``store.tick(prefix)`` block, ``tx.compose`` the Parts

        ``px.<prefix>.0``, ``px.<prefix>.1``, ..., ``px.<prefix>.<n>``      (decimal index, no padding)

    in that order. The store is touched in no other way (nothing at ``fn.*``/``sc.*``; no ``store.set``). Each Part's VALUE is
    the dict ``{"index": i, "source": calc.to_source(steps[i]), "outcome": calc.classify(steps[i]).value}``.

    The calculations are real, not replays of precomputed data:
      * step 0: ``tx.compose("px.<prefix>.0", Part(load), {"program": Part(calc.to_source(expr))})`` where ``load`` is a
        callable ``inputs -> record`` that does ``parse_calc`` on ``inputs["program"]`` and builds the record for it.
      * step i >= 1: ``tx.compose("px.<prefix>.<i>", step_part, {"prev": <the Part returned by the previous compose>})``
        where ``step_part`` is ONE ``Part(fn)`` shared by all of these composes and ``fn(inputs)`` parses
        ``inputs["prev"]["source"]``, applies ``calc.step`` to it and builds the record of the result.
    Hence for the returned head Part ``h``: ``h.composition.inputs["prev"]`` is (identical to) the Part at
    ``px.<prefix>.<n-1>``, and so on down to the Part at ``px.<prefix>.0`` whose composition has only the input ``"program"``
    (a Part with ``composition is None`` and value ``calc.to_source(expr)``). A value program (``n == 0``) returns the Part
    at ``px.<prefix>.0``. The returned Part IS the one bound at ``px.<prefix>.<n>`` (same object).

    Atomicity: all Parts become visible together when the tick exits normally. If any compose raises (e.g. an address
    ``px.<prefix>.<k>`` is already occupied), nothing is bound, the exception propagates unchanged, and the store's
    receipts show every attempted compose of this tick as FAILED (that is dsdk.core's tick semantics -- do not reimplement it).
    On success the store records ``n + 1`` PRODUCED receipts, all with ``tick == prefix``.

    ``prefix`` must be a non-empty ``str`` (``TypeError`` / ``ValueError``; checked BEFORE the store is touched).
    ``store`` must be a ``PxC`` (``TypeError``) and ``expr`` a ``calc.Expr`` (``TypeError``).
    A stuck program is traced too: the last record's outcome is ``"stuck"``.
    """
    raise NotImplementedError
