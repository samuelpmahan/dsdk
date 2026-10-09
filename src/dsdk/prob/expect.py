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
    raise NotImplementedError


def _value_in_world(expr: calc.Expr, names: tuple[str, ...], world: dict[str, bool]) -> int:
    raise NotImplementedError


def expectation(belief: Belief, calc_text: str, given_text: str | None = None) -> Judgment:
    """Exact expected value of the Int-typed Calc expression ``calc_text`` under the belief (optionally given evidence text). Verdicts as in the module docstring.

    ``TypeError`` for a non-Belief or for texts that are not ``str`` (``given_text`` may be ``None``).
    """
    raise NotImplementedError


def sample_expectation(belief: Belief, calc_text: str, n: int, seed: int) -> Judgment:
    """Monte Carlo estimate of ``expectation(belief, calc_text)``: draw ``n`` worlds with :func:`dsdk.prob.sampling.sample_worlds` (same ``n``, ``seed``), evaluate the expression in
    each with the same pipeline, and return ``KNOWN`` :class:`MeanEstimate`.

    Verdict order: argument errors raise (``TypeError`` for a non-Belief / non-str text, and ``n``/``seed`` rules of ``sample_worlds``, even for an INVALID belief); text failures as in
    :func:`expectation` (unparseable, unmodelled, ill-typed, not integer); ``INVALID`` for a belief of zero total weight (``sample_worlds``'s verdict, unchanged); ``UNKNOWN``
    (reason says there are no draws) for ``n == 0``. ``mean`` is ``sum / n`` as a float; ``stderr`` uses the sample variance with ``n - 1`` in the denominator.
    """
    raise NotImplementedError
