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

from .formula import And, Formula, Implies, Not, Or


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
        if not isinstance(self.formula, Formula):
            raise TypeError(f"Step.formula must be a Formula, got {type(self.formula).__name__}")
        if not isinstance(self.rule, Rule):
            raise TypeError(f"Step.rule must be a Rule member, got {self.rule!r}")
        if type(self.cites) is not tuple:
            raise TypeError(f"Step.cites must be a tuple, got {type(self.cites).__name__}")
        for c in self.cites:
            if type(c) is not int:
                raise TypeError(f"Step.cites entries must be int, got {c!r}")


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
    premise_list = list(premises)
    arity = {
        Rule.PREMISE: 0,
        Rule.MODUS_PONENS: 2,
        Rule.MODUS_TOLLENS: 2,
        Rule.AND_INTRO: 2,
        Rule.AND_ELIM_LEFT: 1,
        Rule.AND_ELIM_RIGHT: 1,
        Rule.OR_INTRO_LEFT: 1,
        Rule.OR_INTRO_RIGHT: 1,
        Rule.DOUBLE_NEGATION_ELIM: 1,
    }
    formulas: list[Formula] = []

    for i, step in enumerate(proof):
        rule = step.rule
        cites = step.cites

        def fail(detail: str) -> CheckResult:
            return CheckResult(False, i, f"step {i} ({rule.value}): {detail}")

        # 1. arity first
        if len(cites) != arity[rule]:
            return fail(f"rule takes {arity[rule]} cites, got {len(cites)}")
        # 2. citations must be strictly earlier steps
        for c in cites:
            if not (0 <= c < i):
                return fail(f"cites step {c}, which is not an earlier step (must satisfy 0 <= c < {i})")
        cited = [formulas[c] for c in cites]
        f = step.formula

        # 3. the rule itself
        if rule is Rule.PREMISE:
            if f not in premise_list:
                return fail("formula is not one of the premises")
        elif rule is Rule.MODUS_PONENS:
            imp, ante = cited
            if not (isinstance(imp, Implies) and ante == imp.left and f == imp.right):
                return fail("requires Implies(p, q) and p, concluding q")
        elif rule is Rule.MODUS_TOLLENS:
            imp, neg = cited
            if not (isinstance(imp, Implies) and isinstance(neg, Not) and neg.operand == imp.right
                    and f == Not(imp.left)):
                return fail("requires Implies(p, q) and Not(q), concluding Not(p)")
        elif rule is Rule.AND_INTRO:
            left, right = cited
            if f != And(left, right):
                return fail("conclusion must be And(cited[0], cited[1])")
        elif rule is Rule.AND_ELIM_LEFT:
            (src,) = cited
            if not (isinstance(src, And) and f == src.left):
                return fail("requires And(l, r), concluding l")
        elif rule is Rule.AND_ELIM_RIGHT:
            (src,) = cited
            if not (isinstance(src, And) and f == src.right):
                return fail("requires And(l, r), concluding r")
        elif rule is Rule.OR_INTRO_LEFT:
            (src,) = cited
            if not (isinstance(f, Or) and f.left == src):
                return fail("conclusion must be Or(cited formula, X)")
        elif rule is Rule.OR_INTRO_RIGHT:
            (src,) = cited
            if not (isinstance(f, Or) and f.right == src):
                return fail("conclusion must be Or(X, cited formula)")
        elif rule is Rule.DOUBLE_NEGATION_ELIM:
            (src,) = cited
            if not (isinstance(src, Not) and isinstance(src.operand, Not) and f == src.operand.operand):
                return fail("requires Not(Not(p)), concluding p")
        else:  # pragma: no cover - all Rule members are handled above
            return fail("unknown rule")

        formulas.append(f)

    return CheckResult(True, None, "")
