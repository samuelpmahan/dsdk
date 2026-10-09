"""Possible worlds, weights, conditioning and exact marginals (track A3).

A *possible world* is a MODEL from ``dsdk.logic``: a full truth assignment over the belief's variables that satisfies a
constraint formula. A :class:`Belief` is the list of those worlds together with a non-negative exact WEIGHT per world.

Weights are RELATIVE (unnormalised) masses; probabilities are weight ratios. Keeping masses unnormalised is what makes
conditioning honest: conditioning on evidence ``e`` keeps the masses of the worlds that satisfy ``e`` and zeroes the others,
so the belief's :attr:`Belief.total` becomes ``P(e)``. A belief with ``total == 0`` is *representable* (impossible evidence
happened) but every probability question about it returns an ``INVALID`` Judgment: ``0/0`` is never turned into a number.

Contract conventions used across dsdk.prob
------------------------------------------
* Functions that RETURN A BELIEF (or other data structure) raise ``TypeError`` (wrong type) / ``ValueError`` (bad value).
* Functions that ANSWER A PROBABILITY QUESTION return a ``dsdk.core.Judgment`` and never raise for a semantic problem
  (only ``TypeError`` for arguments of the wrong type):
    - ``KNOWN``    the exact answer (a ``Fraction`` unless stated otherwise);
    - ``INVALID``  the evidence/belief has probability zero: the conditional is undefined. The reason says so;
    - ``UNKNOWN``  the question mentions variables the belief does not model, so the belief cannot answer it.
* Variable names are ``str`` and are the names of ``dsdk.logic.Var``.

Enumeration order of ``Belief.worlds`` is ``dsdk.logic.models`` order over ``variables``: sorted names, ``False`` before
``True``, FIRST variable slowest.
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import Callable, Mapping

from dsdk.core import Judgment, Status
from dsdk.logic import And, Const, Formula, evaluate, models, variables

from .exact import to_prob, to_weight

MAX_VARIABLES = 16
"""Largest number of variables a belief may range over (2**16 = 65536 worlds). More is a ``ValueError``."""


class UnmodelledVariableError(ValueError):
    """A formula mentions variables that the belief does not range over. ``.names`` is the sorted tuple of the missing names."""

    def __init__(self, names: tuple[str, ...]) -> None:
        raise NotImplementedError


@dataclass(frozen=True)
class WeightedWorld:
    """One possible world and its weight.

    * ``values``  ``((name, bool), ...)`` with names strictly increasing (sorted, distinct). Hashable.
    * ``weight``  an exact ``Fraction`` >= 0 (a ``float`` or ``int`` here is a ``TypeError``: callers convert with ``to_weight``).

    Validation in ``__post_init__`` (first violated rule raises): ``values`` must be a tuple of 2-tuples ``(str, bool)``
    (``TypeError``; the value must be exactly a ``bool``, so ``1`` is rejected); names strictly increasing (``ValueError``);
    ``weight`` a ``Fraction`` (``TypeError``) that is >= 0 (``ValueError``).
    """

    values: tuple[tuple[str, bool], ...]
    weight: Fraction

    def __post_init__(self) -> None:
        raise NotImplementedError

    def assignment(self) -> dict[str, bool]:
        """The world as a fresh ``dict`` ``{name: bool}`` (what ``dsdk.logic.evaluate`` takes)."""
        raise NotImplementedError


@dataclass(frozen=True)
class Belief:
    """A weighted set of possible worlds over ``variables``.

    * ``variables``  strictly increasing tuple of ``str`` (sorted, distinct).
    * ``worlds``     tuple of :class:`WeightedWorld`, each over exactly ``variables``. Built by this package in
                     ``logic.models`` order; direct construction need not respect that order.

    ``__post_init__`` validation (first violated rule raises): ``variables`` a tuple of ``str`` (``TypeError``) strictly
    increasing (``ValueError``); ``worlds`` a tuple of ``WeightedWorld`` (``TypeError``) each whose names are exactly
    ``variables`` in order (``ValueError``).
    """

    variables: tuple[str, ...]
    worlds: tuple[WeightedWorld, ...]

    def __post_init__(self) -> None:
        raise NotImplementedError

    @property
    def total(self) -> Fraction:
        """Sum of all weights (``Fraction(0)`` for no worlds). After conditioning on ``e`` this is the mass of ``e``."""
        raise NotImplementedError

    def mass(self, f: Formula) -> Fraction:
        """Total weight of the worlds in which ``f`` is true. ``TypeError`` if ``f`` is not a Formula;
        :class:`UnmodelledVariableError` if ``f`` mentions a variable outside ``self.variables``."""
        raise NotImplementedError


def prior_belief(priors: Mapping[str, object], constraint: Formula | None = None) -> Belief:
    """Independent prior over variables, restricted to the models of ``constraint``.

    * ``priors``      mapping ``name -> P(name is true)`` (each converted with :func:`dsdk.prob.exact.to_prob`; so ``0.2`` is
                      exactly ``1/5``). Not a ``Mapping`` or a non-``str`` key: ``TypeError``. Bad probability: as ``to_prob``.
    * ``constraint``  ``None`` (= ``Const(True)``) or a Formula. Not a Formula: ``TypeError``.

    Variables of the belief: ``sorted(set(priors) | variables(constraint))``. More than :data:`MAX_VARIABLES`: ``ValueError``
    (checked BEFORE enumerating). Worlds: every ``dsdk.logic.models(constraint, over=variables)``, in that order (use
    ``models``; do not re-implement the enumeration). The weight of a world is the product over the variables that HAVE a prior
    of ``p`` (variable true) or ``1 - p`` (variable false). A variable with NO prior (e.g. a percept that the constraint
    determines) contributes the factor 1, so its value is whatever the constraint forces.

    Zero-weight worlds are KEPT (a prior of 0 or 1 does not remove worlds, it zeroes their weight): "possible" means
    logically possible; "probable" is the weight. An unsatisfiable constraint gives a belief with no worlds.
    Example: ``prior_belief({"A": 0.2, "B": 0.2}, Or(Var("A"), Var("B")))`` has 3 worlds with weights 4/25, 4/25, 1/25
    in the order (A=F,B=T), (A=T,B=F), (A=T,B=T), total 9/25.
    """
    raise NotImplementedError


def reweight(b: Belief, likelihood: Callable[[dict[str, bool]], object]) -> Belief:
    """Multiply every world's weight by ``likelihood(assignment)`` (a non-negative number, converted with ``to_weight``).

    ``likelihood`` is called exactly once per world, in world order, with a FRESH ``dict`` (mutating it cannot affect the
    belief). The result has the same variables and worlds (zero-weight ones included, nothing is dropped or renormalised).
    ``b`` is not changed. ``TypeError`` if ``b`` is not a Belief or ``likelihood`` is not callable; a bad return value raises
    as in ``to_weight``.
    """
    raise NotImplementedError


def condition(b: Belief, evidence: Formula) -> Belief:
    """Condition on a formula: weights of worlds where ``evidence`` is false become 0, others are unchanged.

    The result's ``total`` is ``P(evidence)`` (relative to ``b.total``). Impossible evidence does NOT raise: it returns a belief
    with ``total == 0`` that answers every probability question with ``INVALID``. ``TypeError`` for a non-Belief/non-Formula;
    :class:`UnmodelledVariableError` if ``evidence`` mentions a variable not in ``b.variables``.
    Implemented with :func:`reweight` (indicator likelihood), so conditioning twice is the same as conditioning on the ``And``.
    """
    raise NotImplementedError


def probability(b: Belief, query: Formula, given: Formula | None = None) -> Judgment:
    """Exact ``P(query)`` or ``P(query | given)`` as a Judgment.

    * ``TypeError`` for a non-Belief, a non-Formula query, or a ``given`` that is neither ``None`` nor a Formula.
    * ``UNKNOWN`` if ``query`` or ``given`` mentions variables outside ``b.variables``; the reason lists them sorted,
      comma-separated (``"unmodelled variables: x, y"``).
    * ``INVALID`` if the denominator is 0: with ``given is None`` the denominator is ``b.total`` (reason mentions
      "zero total weight"), otherwise ``mass(given)`` (reason mentions "evidence has probability zero"). The reason is
      never blank. NEVER ``KNOWN`` with a made-up value: ``P(q | impossible)`` is not 0, not 1, not anything.
    * Otherwise ``KNOWN`` with the ``Fraction`` ``mass(query & given) / mass(given)`` (or ``mass(query) / total``).
      The value ``Fraction(0)`` and ``Fraction(1)`` are legitimate KNOWN answers.
    """
    raise NotImplementedError


def marginals(b: Belief) -> Judgment:
    """``P(v is true)`` for every variable: ``KNOWN`` with a ``dict {name: Fraction}`` (keys in ``b.variables`` order),
    or ``INVALID`` (reason mentions "zero total weight") if ``b.total == 0``. A belief over no variables gives ``{}``
    when it has total > 0. ``TypeError`` for a non-Belief."""
    raise NotImplementedError


def normalise(b: Belief) -> Judgment:
    """``KNOWN`` with a new Belief whose weights are ``weight / total`` (so ``total == 1``, same worlds, same order),
    or ``INVALID`` (reason mentions "zero total weight") when ``b.total == 0``. ``TypeError`` for a non-Belief."""
    raise NotImplementedError
