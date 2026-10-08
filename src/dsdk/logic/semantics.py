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

import itertools
from typing import Iterable, Iterator, Mapping

from dsdk.core import Judgment, Status  # noqa: F401  (A1 builds on A0's kernel)

from .formula import And, Const, Formula, Iff, Implies, Not, Or, Var, variables


class UnassignedVariableError(KeyError):
    """``evaluate`` met a variable with no entry in the assignment.

    Raise it as ``UnassignedVariableError(name)`` (single positional argument,
    the variable name). ``e.name`` is that name; when several variables are
    missing it is the alphabetically first one.
    """

    @property
    def name(self) -> str:
        return self.args[0]


def _check_values(names: frozenset[str], assignment: Mapping[str, bool]) -> None:
    """Raise TypeError if a value for a variable of the formula is not a real bool."""
    for name in names:
        if name in assignment and type(assignment[name]) is not bool:
            raise TypeError(
                f"value for {name!r} must be bool, got {type(assignment[name]).__name__}"
            )


def _not3(a: bool | None) -> bool | None:
    return None if a is None else (not a)


def _and3(a: bool | None, b: bool | None) -> bool | None:
    if a is False or b is False:
        return False
    if a is None or b is None:
        return None
    return True


def _or3(a: bool | None, b: bool | None) -> bool | None:
    if a is True or b is True:
        return True
    if a is None or b is None:
        return None
    return False


def _kleene(f: Formula, values: Mapping[str, bool]) -> bool | None:
    """Strong Kleene value of ``f``; variables absent from ``values`` are UNKNOWN (None).

    Iterative post-order traversal with an explicit stack and a result stack.
    Each node's result is computed from its children's results only
    (truth-functional); no cache is kept, so repeated sub-objects are evaluated
    at each occurrence.
    """
    results: list[bool | None] = []
    todo: list[tuple[Formula, bool]] = [(f, False)]
    while todo:
        node, expanded = todo.pop()
        if isinstance(node, Const):
            results.append(node.value)
        elif isinstance(node, Var):
            results.append(values.get(node.name))
        elif not expanded:
            todo.append((node, True))
            if isinstance(node, Not):
                todo.append((node.operand, False))
            elif isinstance(node, (And, Or, Implies, Iff)):
                todo.append((node.right, False))
                todo.append((node.left, False))
            else:
                raise TypeError(f"unknown formula node: {type(node).__name__}")
        elif isinstance(node, Not):
            results.append(_not3(results.pop()))
        else:
            right = results.pop()
            left = results.pop()
            if isinstance(node, And):
                results.append(_and3(left, right))
            elif isinstance(node, Or):
                results.append(_or3(left, right))
            elif isinstance(node, Implies):
                results.append(_or3(_not3(left), right))
            else:  # Iff
                results.append(None if (left is None or right is None) else (left == right))
    return results[0]


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
    names = variables(f)
    _check_values(names, assignment)
    missing = [n for n in names if n not in assignment]
    if missing:
        raise UnassignedVariableError(min(missing))
    result = _kleene(f, assignment)
    assert result is not None
    return result


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
    names = variables(f)
    _check_values(names, assignment)
    missing = [n for n in names if n not in assignment]
    value = _kleene(f, assignment)
    if value is None:
        return Judgment(Status.UNKNOWN, None, "unassigned: " + ", ".join(sorted(missing)))
    return Judgment(Status.KNOWN, value, "")


def _assignments(names: list[str]) -> Iterator[dict[str, bool]]:
    """Yield every assignment over ``names`` (already sorted) in module enumeration order, each a fresh dict."""
    for combo in itertools.product([False, True], repeat=len(names)):
        yield dict(zip(names, combo))


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
    if over is None:
        names = sorted(variables(f))
    else:
        names = sorted(set(over))
        missing = variables(f) - set(names)
        if missing:
            raise ValueError(f"'over' is missing variables of the formula: {', '.join(sorted(missing))}")

    def _gen() -> Iterator[dict[str, bool]]:
        for assignment in _assignments(names):
            if evaluate(f, assignment):
                yield assignment

    return _gen()


def truth_table(f: Formula) -> list[tuple[dict[str, bool], bool]]:
    """All ``2**n`` rows ``(assignment, value)`` over ``sorted(variables(f))``,
    in the module's enumeration order, including falsifying rows.
    A ``Const``-only formula has exactly one row: ``({}, value)``."""
    names = sorted(variables(f))
    return [(assignment, evaluate(f, assignment)) for assignment in _assignments(names)]


def is_satisfiable(f: Formula) -> bool:
    """True iff some assignment over ``variables(f)`` makes ``f`` true."""
    return any(True for _ in models(f))


def is_valid(f: Formula) -> bool:
    """True iff EVERY assignment makes ``f`` true (a tautology).
    Always equals ``not is_satisfiable(Not(f))``."""
    return not is_satisfiable(Not(f))


def entails(premises: Iterable[Formula], conclusion: Formula) -> bool:
    """Semantic entailment: every assignment (over the union of the variables of
    all premises and the conclusion) satisfying ALL premises satisfies the
    conclusion.

    * Empty ``premises``: entails iff ``conclusion`` is valid.
    * Contradictory premises entail everything (vacuously true).
    * ``premises`` may be any iterable (including a one-shot generator);
      a lone ``Formula`` instead of an iterable of them is a ``TypeError``.
    """
    return countermodel(premises, conclusion) is None


def countermodel(premises: Iterable[Formula], conclusion: Formula) -> dict[str, bool] | None:
    """The FIRST assignment (module enumeration order, over the union of the
    variables of all premises and the conclusion) that satisfies every premise
    and falsifies ``conclusion``; ``None`` if there is none.
    ``countermodel(p, c) is None`` iff ``entails(p, c)``. The returned dict has
    one key per variable in the union (not only those that matter)."""
    premises = list(premises)
    names = sorted(set().union(variables(conclusion), *(variables(p) for p in premises)))
    for assignment in _assignments(names):
        if all(evaluate(p, assignment) for p in premises) and not evaluate(conclusion, assignment):
            return assignment
    return None
