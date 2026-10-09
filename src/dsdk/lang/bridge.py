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
    if not isinstance(f, logic.Formula):
        raise TypeError(f"from_formula expects a logic.Formula, not {type(f).__name__}")
    if isinstance(f, logic.Const):
        return calc.BoolLit(f.value)
    if isinstance(f, logic.Var):
        return calc.Var(f.name)
    if isinstance(f, logic.Not):
        return calc.Not(from_formula(f.operand))
    if isinstance(f, logic.And):
        return calc.BinOp("and", from_formula(f.left), from_formula(f.right))
    if isinstance(f, logic.Or):
        return calc.BinOp("or", from_formula(f.left), from_formula(f.right))
    if isinstance(f, logic.Implies):
        return calc.BinOp("or", calc.Not(from_formula(f.left)), from_formula(f.right))
    if isinstance(f, logic.Iff):
        return calc.BinOp("==", from_formula(f.left), from_formula(f.right))
    raise TypeError(f"unsupported logic formula: {type(f).__name__}")


def bind_assignment(e: calc.Expr, assignment: Mapping[str, bool]) -> calc.Expr:
    """Wrap ``e`` in one ``Let`` per assignment entry: names in ASCENDING ``sorted()`` order, the FIRST (smallest) name
    OUTERMOST, each bound to ``BoolLit(value)``. ``{"a": True, "b": False}`` ->
    ``Let("a", BoolLit(True), Let("b", BoolLit(False), e))``; an empty assignment returns ``e`` itself.
    A value that is not exactly a ``bool`` is a ``TypeError`` (like ``logic.evaluate``). Extra names are bound too (harmless).
    """
    for name in assignment:
        if type(assignment[name]) is not bool:
            raise TypeError(f"assignment value for {name!r} must be a bool, not {type(assignment[name]).__name__}")
    out = e
    for name in sorted(assignment, reverse=True):
        out = calc.Let(name, calc.BoolLit(assignment[name]), out)
    return out


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
    if not isinstance(prefix, str):
        raise TypeError(f"prefix must be a str, not {type(prefix).__name__}")
    if not prefix:
        raise ValueError("prefix must be a non-empty str")
    if not isinstance(store, PxC):
        raise TypeError(f"store must be a PxC, not {type(store).__name__}")
    if not isinstance(expr, calc.Expr):
        raise TypeError(f"expr must be a calc.Expr, not {type(expr).__name__}")

    steps = calc.trace(expr)
    with store.tick(prefix) as tx:
        head = tx.compose(f"px.{prefix}.0", Part(_load), {"program": Part(calc.to_source(expr))})
        step_part = Part(_advance)
        for i in range(1, len(steps)):
            head = tx.compose(f"px.{prefix}.{i}", step_part, {"prev": head})
    return head


def _record(term: calc.Expr, index: int) -> dict:
    """The plain-dict record stored as a Part's value (strings and ints only, never AST objects)."""
    return {"index": index, "source": calc.to_source(term), "outcome": calc.classify(term).value}


def _load(inputs: Mapping[str, str]) -> dict:
    """Step 0: parse the program text and record the term it denotes."""
    return _record(calc.parse_calc(inputs["program"]), 0)


def _advance(inputs: Mapping[str, dict]) -> dict:
    """Step i >= 1: parse the previous record's source, apply one small step, record the result."""
    prev = inputs["prev"]
    term = calc.step(calc.parse_calc(prev["source"]))
    if term is None:
        raise ValueError(f"no step applies to {prev['source']!r}")
    return _record(term, prev["index"] + 1)
