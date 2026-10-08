"""Meaning of formulas: evaluation, three-valued evaluation, models, entailment.

Variable order and enumeration order (used by ``models``, ``truth_table``,
``countermodel``) -- the single most important convention in this module:

    Let ``names`` be the variable names in ASCENDING ``sorted()`` order
    (plain ``str`` comparison, so ``"P12" < "P2"``, uppercase before lowercase).
    Assignments are enumerated exactly like ``itertools.product([False, True],
    repeat=len(names))``: ``False`` before ``True``, the FIRST name is the
    slowest-changing (most significant) position, the LAST name changes fastest.
    For names ``[a, b]``: (a=F,b=F), (a=F,b=T), (a=T,b=F), (a=T,b=T).
    Zero names -> exactly one (empty) assignment.
    Every assignment dict is a FRESH ``dict`` whose keys are in ``names`` order.
"""
from __future__ import annotations

from typing import Iterable, Iterator, Mapping

from dsdk.core import Judgment, Status  # noqa: F401  (A1 builds on A0's kernel)

from .formula import Formula


class UnassignedVariableError(KeyError):
    """``evaluate`` met a variable with no entry in the assignment.

    Raise it as ``UnassignedVariableError(name)`` (single positional argument,
    the variable name). ``e.name`` is that name; when several variables are
    missing it is the alphabetically first one.
    """

    @property
    def name(self) -> str:
        return self.args[0]


def evaluate(f: Formula, assignment: Mapping[str, bool]) -> bool:
    """Two-valued truth value of ``f`` under a TOTAL assignment.

    * Raises :class:`UnassignedVariableError` if ANY variable occurring in
      ``f`` is missing from ``assignment`` -- even one that could not affect the
      result: ``evaluate(And(Const(False), Var("x")), {})`` RAISES (no
      short-circuit exemption). Use ``evaluate_partial`` for that case.
    * Extra keys in ``assignment`` are ignored.
    * A value (for a variable occurring in ``f``) that is not exactly a ``bool``
      raises ``TypeError`` (``1`` and ``None`` are rejected).
    * Implies(a, b) == (not a) or b;  Iff(a, b) == (a == b).
    """
    raise NotImplementedError


def evaluate_partial(f: Formula, assignment: Mapping[str, bool]) -> Judgment:
    """STRONG KLEENE three-valued evaluation under a possibly partial assignment.

    Returns a ``dsdk.core.Judgment``:
      * ``Judgment(Status.KNOWN, True|False)`` (reason ``""``) when the value is
        determined by the tables below, else
      * ``Judgment(Status.UNKNOWN, None, reason)`` with
        ``reason == "unassigned: " + ", ".join(sorted(U))`` where ``U`` is the
        set of ALL variables of ``f`` missing from ``assignment`` (not only the
        relevant ones), e.g. ``"unassigned: x, y"``.

    The semantics is TRUTH-FUNCTIONAL (it combines the three-valued results of
    the sub-formulas; it does NOT reason about which variable is which). With
    T/F/U = true/false/unknown:

        Not:  ¬T=F  ¬F=T  ¬U=U
        And:  F if either is F; else U if either is U; else T
        Or:   T if either is T; else U if either is U; else F
        Implies(a,b) = Or(Not a, b):  F→U = T, U→T = T, T→U = U, U→F = U, U→U = U
        Iff(a,b):  U if either operand is U; else T iff the operands are equal

    Consequences naive implementations get wrong (all are tested):
      * ``False ∧ x`` is KNOWN False and ``True ∨ x`` is KNOWN True, whatever ``x``;
      * ``x ∨ ¬x`` and ``x → x`` and ``x ↔ x`` are UNKNOWN when ``x`` is
        unassigned (Kleene logic does not know the two ``x`` are the same);
      * ``Const`` only formulas are always KNOWN.
    A fully assigned formula gives the same answer as ``evaluate``.
    Extra keys are ignored. A value (for a variable occurring in ``f``) that is
    not exactly a ``bool`` raises ``TypeError``.
    """
    raise NotImplementedError


def models(f: Formula, over: Iterable[str] | None = None) -> Iterator[dict[str, bool]]:
    """Lazily yield every assignment over ``over`` that makes ``f`` true.

    * ``over=None`` means the variables of ``f``. Otherwise ``over`` is an
      iterable of names; duplicates are collapsed; it must contain every
      variable of ``f`` or ``ValueError`` is raised (at the first ``next()`` --
      callers always consume the result, tests use ``list(...)``). Extra names
      in ``over`` are free: each doubles the number of models.
    * Order: see module docstring. Returns a real iterator (``iter(x) is x``).
    * Each yielded dict is a new object whose keys are exactly ``sorted(over)``.
    * ``models(Const(True))`` yields one empty dict ``{}``;
      ``models(Const(False))`` yields nothing.
    """
    raise NotImplementedError


def truth_table(f: Formula) -> list[tuple[dict[str, bool], bool]]:
    """All ``2**n`` rows ``(assignment, value)`` over ``sorted(variables(f))``,
    in the module's enumeration order, including falsifying rows.
    A ``Const``-only formula has exactly one row: ``({}, value)``."""
    raise NotImplementedError


def is_satisfiable(f: Formula) -> bool:
    """True iff some assignment over ``variables(f)`` makes ``f`` true."""
    raise NotImplementedError


def is_valid(f: Formula) -> bool:
    """True iff EVERY assignment makes ``f`` true (a tautology).
    Always equals ``not is_satisfiable(Not(f))``."""
    raise NotImplementedError


def entails(premises: Iterable[Formula], conclusion: Formula) -> bool:
    """Semantic entailment: every assignment (over the union of the variables of
    all premises and the conclusion) satisfying ALL premises satisfies the
    conclusion.

    * Empty ``premises``: entails iff ``conclusion`` is valid.
    * Contradictory premises entail everything (vacuously true).
    * ``premises`` may be any iterable (including a one-shot generator);
      a lone ``Formula`` instead of an iterable of them is a ``TypeError``.
    """
    raise NotImplementedError


def countermodel(premises: Iterable[Formula], conclusion: Formula) -> dict[str, bool] | None:
    """The FIRST assignment (module enumeration order, over the union of the
    variables of all premises and the conclusion) that satisfies every premise
    and falsifies ``conclusion``; ``None`` if there is none.
    ``countermodel(p, c) is None`` iff ``entails(p, c)``. The returned dict has
    one key per variable in the union (not only those that matter)."""
    raise NotImplementedError
