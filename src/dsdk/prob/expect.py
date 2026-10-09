"""Expectations of typed Calc expressions over a belief (tracks A2 -> A3): the language package computes, the probability package weighs.

A question is written in the CALC language (``dsdk.lang.calc``), whose variables are the belief's Boolean variables::

    expectation(belief, "(if P22 then 1 else 0) + (if P31 then 1 else 0)")       # expected number of pits among P22, P31
    expectation(belief, "let k = 3 in (if A then k else 0 - k)", "A | B")        # E[...| A or B]; the second text is a FORMULA

Pipeline (each step is a real call into the lower layer, in this order):

1. ``dsdk.lang.calc.parse_calc(text)``                                   -> an ``Expr`` (or a ``LangError``)
2. ``dsdk.lang.calc.free_vars(expr)``                                    -> the variables the expression reads
3. ``dsdk.lang.calc.typecheck(expr, {v: Type.BOOL for each such v})``     -> must be ``Type.INT``
4. for every world of the belief: ``dsdk.lang.calc.evaluate(dsdk.lang.bridge.bind_assignment(expr, {v: world[v]}))``  -> an int
5. exact weighted average with ``Fraction`` (weights are the belief's weights; the optional evidence restricts the worlds).

Type safety makes step 4 total: a well-typed, closed term never gets stuck (tracks/A2/PROOFS.md, Proof 3), so ``evaluate`` cannot raise ``StuckError`` here.

Every function returns a ``dsdk.core.Judgment`` and never raises for a problem with the user's TEXT or its meaning; ``TypeError`` only for arguments of the wrong
Python type. Verdicts, checked in this order (the first that applies wins):

* ``INVALID``  reason ``"unparseable expression: " + str(error)`` -- the Calc text does not lex/parse; ``str(error)`` ends with ``(at offset N)``.
* ``UNKNOWN``  reason ``"unmodelled variables: x, y"`` (sorted) -- the expression reads variables the belief does not model.
* ``INVALID``  reason ``"ill-typed expression: " + <the type checker's own reason>`` -- e.g. ``"ill-typed expression: operand type mismatch: (1 + true)"``.
* ``INVALID``  reason ``"not an integer expression: " + source + " has type Bool"`` -- a well-typed Bool expression (use ``dsdk.prob.probability`` for those).
* the evidence text (``given_text``, relaxed FORMULA syntax as in ``dsdk.prob.ask``): ``INVALID`` ``"unparseable evidence text: ..."`` (same wording as ``ask``), ``UNKNOWN`` for
  unmodelled variables, ``INVALID`` with "probability zero" when the evidence has weight 0; without evidence, ``INVALID`` with "zero total weight" when the belief's total is 0.
* ``KNOWN``    the exact ``Fraction`` ``sum(weight * value) / total`` (or over the worlds satisfying the evidence).
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from fractions import Fraction

from dsdk.core import Judgment, Status
from dsdk.lang import LangError, calc
from dsdk.lang.bridge import bind_assignment
from dsdk.logic import evaluate as logic_evaluate
from dsdk.logic import variables as logic_variables

from .ask import parse_text
from .sampling import sample_worlds
from .worlds import Belief


@dataclass(frozen=True)
class MeanEstimate:
    """A Monte Carlo estimate of an expectation: ``n`` draws, sample ``mean`` and ``stderr = sqrt(sample variance / n)`` (0.0 when ``n == 1``)."""

    n: int
    mean: float
    stderr: float


def _prepare(belief: Belief, calc_text: str) -> tuple[calc.Expr | None, tuple[str, ...], Judgment | None]:
    """Steps 1 to 3 of the pipeline. Returns ``(expr, free variable names sorted, failure)`` where ``failure`` is the verdict Judgment (INVALID or UNKNOWN) or None."""
    try:
        expr = calc.parse_calc(calc_text)
    except LangError as exc:
        return None, (), Judgment(Status.INVALID, None, f"unparseable expression: {exc}")
    names = tuple(sorted(calc.free_vars(expr)))
    missing = [v for v in names if v not in belief.variables]
    if missing:
        return None, names, Judgment(Status.UNKNOWN, None, "unmodelled variables: " + ", ".join(missing))
    checked = calc.typecheck(expr, {v: calc.Type.BOOL for v in names})
    if checked.status is not Status.KNOWN:
        return None, names, Judgment(Status.INVALID, None, f"ill-typed expression: {checked.reason}")
    if checked.value is not calc.Type.INT:
        return None, names, Judgment(
            Status.INVALID, None, f"not an integer expression: {calc.to_source(expr)} has type {checked.value.value}"
        )
    return expr, names, None


def _value_in_world(expr: calc.Expr, names: tuple[str, ...], world: dict[str, bool]) -> int:
    value = calc.evaluate(bind_assignment(expr, {v: world[v] for v in names}))
    if type(value) is not int:
        raise AssertionError(f"expected an int value, got {value!r}")
    return value


def expectation(belief: Belief, calc_text: str, given_text: str | None = None) -> Judgment:
    """Exact expected value of the Int-typed Calc expression ``calc_text`` under the belief (optionally given evidence text). Verdicts as in the module docstring.

    ``TypeError`` for a non-Belief or for texts that are not ``str`` (``given_text`` may be ``None``).
    """
    if not isinstance(belief, Belief):
        raise TypeError(f"expectation needs a Belief, not {type(belief).__name__}")
    if not isinstance(calc_text, str):
        raise TypeError(f"calc_text must be str, not {type(calc_text).__name__}")
    if given_text is not None and not isinstance(given_text, str):
        raise TypeError(f"given_text must be str or None, not {type(given_text).__name__}")
    expr, names, failure = _prepare(belief, calc_text)
    if failure is not None:
        return failure
    given = None
    if given_text is not None:
        parsed = parse_text(given_text, "evidence text")
        if parsed.status is not Status.KNOWN:
            return parsed
        given = parsed.value
        missing = sorted(set(logic_variables(given)) - set(belief.variables))
        if missing:
            return Judgment(Status.UNKNOWN, None, "unmodelled variables: " + ", ".join(missing))
    total = Fraction(0)
    acc = Fraction(0)
    for w in belief.worlds:
        world = w.assignment()
        if given is not None and not logic_evaluate(given, world):
            continue
        total += w.weight
        if w.weight:
            acc += w.weight * _value_in_world(expr, names, world)
    if total == 0:
        if given_text is not None:
            return Judgment(Status.INVALID, None, "evidence has probability zero: the conditional expectation is undefined")
        return Judgment(Status.INVALID, None, "belief has zero total weight: no expectation is defined")
    return Judgment(Status.KNOWN, acc / total, "")


def sample_expectation(belief: Belief, calc_text: str, n: int, seed: int) -> Judgment:
    """Monte Carlo estimate of ``expectation(belief, calc_text)``: draw ``n`` worlds with :func:`dsdk.prob.sampling.sample_worlds` (same ``n``, ``seed``), evaluate the expression in
    each with the same pipeline, and return ``KNOWN`` :class:`MeanEstimate`.

    Verdict order: argument errors raise (``TypeError`` for a non-Belief / non-str text, and ``n``/``seed`` rules of ``sample_worlds``, even for an INVALID belief); text failures as in
    :func:`expectation` (unparseable, unmodelled, ill-typed, not integer); ``INVALID`` for a belief of zero total weight (``sample_worlds``'s verdict, unchanged); ``UNKNOWN``
    (reason says there are no draws) for ``n == 0``. ``mean`` is ``sum / n`` as a float; ``stderr`` uses the sample variance with ``n - 1`` in the denominator.
    """
    if not isinstance(belief, Belief):
        raise TypeError(f"sample_expectation needs a Belief, not {type(belief).__name__}")
    if not isinstance(calc_text, str):
        raise TypeError(f"calc_text must be str, not {type(calc_text).__name__}")
    drawn = sample_worlds(belief, n, seed)
    expr, names, failure = _prepare(belief, calc_text)
    if failure is not None:
        return failure
    if drawn.status is not Status.KNOWN:
        return drawn
    if n == 0:
        return Judgment(Status.UNKNOWN, None, "n is 0: no draws, no estimate")
    values = [_value_in_world(expr, names, dict(draw)) for draw in drawn.value]
    mean = sum(values) / n
    var = sum((x - mean) ** 2 for x in values) / (n - 1) if n > 1 else 0.0
    stderr = math.sqrt(var / n)
    return Judgment(Status.KNOWN, MeanEstimate(n, mean, stderr), "")
