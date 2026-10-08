"""A tiny explicit natural-deduction proof checker.

A proof is a sequence of :class:`Step`; a step is (formula, rule, cites).
Step indices are 0-based. ``cites`` is a tuple of indices of EARLIER steps:
every cited index ``c`` of step ``i`` must satisfy ``0 <= c < i`` (so citing
the step itself, a later step, a negative index or an out-of-range index is
invalid). Formulas are compared with ``==`` (structural equality).

Rules (``cites`` order matters and is part of the contract; "implication first"):

  premise              cites ()        formula must be == one of the ``premises``
  modus_ponens         cites (i, j)    f[i] == Implies(p, q), f[j] == p   =>  q
  modus_tollens        cites (i, j)    f[i] == Implies(p, q), f[j] == Not(q) => Not(p)
  and_intro            cites (i, j)    =>  And(f[i], f[j])    (i == j is allowed)
  and_elim_left        cites (i,)      f[i] == And(l, r)  =>  l
  and_elim_right       cites (i,)      f[i] == And(l, r)  =>  r
  or_intro_left        cites (i,)      =>  Or(f[i], X)   for ANY formula X
  or_intro_right       cites (i,)      =>  Or(X, f[i])   for ANY formula X
  double_negation_elim cites (i,)      f[i] == Not(Not(p)) =>  p

A wrong number of cites for the rule is invalid. Note what is NOT a rule:
affirming the consequent (from ``p -> q`` and ``q`` conclude ``p``) and denying
the antecedent (from ``p -> q`` and ``~p`` conclude ``~q``) must be rejected.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Iterable, Sequence

from .formula import Formula


class Rule(StrEnum):
    PREMISE = "premise"
    MODUS_PONENS = "modus_ponens"
    MODUS_TOLLENS = "modus_tollens"
    AND_INTRO = "and_intro"
    AND_ELIM_LEFT = "and_elim_left"
    AND_ELIM_RIGHT = "and_elim_right"
    OR_INTRO_LEFT = "or_intro_left"
    OR_INTRO_RIGHT = "or_intro_right"
    DOUBLE_NEGATION_ELIM = "double_negation_elim"


@dataclass(frozen=True)
class Step:
    """One line of a proof.

    Construction rules (``__post_init__``): ``formula`` must be a
    :class:`Formula` and ``rule`` a :class:`Rule` member (the bare string
    ``"premise"`` is rejected) -- else ``TypeError``; ``cites`` must be a
    ``tuple`` of ``int`` (``bool`` and ``list`` rejected) -- else ``TypeError``.
    Range/arity of the cites is NOT checked here; ``check`` does that.
    """

    formula: Formula
    rule: Rule
    cites: tuple[int, ...] = ()

    def __post_init__(self) -> None:
        raise NotImplementedError


Proof = Sequence[Step]


@dataclass(frozen=True)
class CheckResult:
    """Outcome of :func:`check`.

    * valid proof:   ``ok=True,  bad_step=None, reason=""``
    * invalid proof: ``ok=False, bad_step=<index of the FIRST invalid step>,
      reason=f"step {i} ({rule}): {detail}"`` where ``rule`` is the rule's
      string value (e.g. ``modus_ponens``) and ``detail`` is non-empty human
      text. If the failure is a citation that is not strictly earlier / out of
      range / negative, ``detail`` must contain the word ``earlier``. If the
      failure is a wrong number of cites, ``detail`` must contain ``cites``.
    """

    ok: bool
    bad_step: int | None
    reason: str


def check(proof: Proof, premises: Iterable[Formula]) -> CheckResult:
    """Check every step in order and report the first invalid one.

    The empty proof is valid (``ok=True``). Validity means "every step is
    justified", not "the proof proves any particular goal". Checking stops at
    the first invalid step, so later invalid steps are never reported.
    ``premises`` may be any iterable of formulas (consumed once).
    """
    raise NotImplementedError
