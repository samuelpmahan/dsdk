"""Record a checked proof in the kernel store, and replay it from the store's lineage (tracks A1 x A0).

A proof is a DAG: step ``i`` cites earlier steps. The kernel's lineage is a DAG too: a composed Part has the Parts it was computed from. This module makes
them the SAME object. :func:`record_proof` binds one Part per step, in ONE tick; :func:`replay_proof` rebuilds the proof from the Parts alone and re-checks it.

Layout (``prefix`` is an identifier, ``i`` the 0-based step index, decimal, no padding)::

    px.<prefix>.<i>      the Part of step i; its VALUE is the step's formula (a ``Formula``)

Every step, premises included, is a COMPOSED Part: ``store`` tick ``"proof.<prefix>"`` runs ``tx.compose("px.<prefix>.<i>", calc_i, inputs_i)`` for ``i = 0, 1, ...``
where ``calc_i`` is a fresh ``Part`` holding a :class:`StepCalculation` (a callable that remembers the step's rule, formula and the proof's premises) and ``inputs_i`` is
EXACTLY the cited Parts, named ``"c0"``, ``"c1"`` ... in the order of the step's ``cites`` (a premise step has no inputs). So the lineage graph of the store is the proof's citation graph,
plus one calculation node per step. The calculation re-derives the step: it runs ``dsdk.logic.check`` on a two-line mini proof (the cited formulas as premises, then the step) and raises
:class:`ProofStepError` unless it is valid; a premise step is checked against the proof's premises. Nothing is bound unless EVERY step passes (core tick semantics).

This module calls only ``dsdk.core`` (layer rule: logic builds on core). Graph-level checks of the lineage live in tests/integration.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, Sequence

from dsdk.core import Judgment, Part, PxC, Status

from .formula import Formula
from .proof import Rule, Step, check

_PREFIX = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


class ProofStepError(Exception):
    """A step was rejected while being recorded. ``str(error)`` is the reason, the same text ``dsdk.logic.check`` reports for that step."""


class StepCalculation:
    """The behaviour of one recorded step: callable ``inputs -> formula``; remembers ``rule``, ``formula`` and ``premises`` so a replay can read them back from the lineage.

    ``inputs`` is a dict ``{"c0": formula, "c1": formula, ...}`` of the cited steps' values in cite order. The call builds the mini proof
    ``[Step(f, Rule.PREMISE) for f in cited] + [Step(self.formula, self.rule, (0, 1, ..., k-1))]`` and checks it with ``dsdk.logic.check`` against the premises
    ``list(cited) + list(self.premises)``. Invalid -> raise :class:`ProofStepError` with the check's reason. Valid -> return ``self.formula``.
    """

    def __init__(self, rule: Rule, formula: Formula, premises: tuple[Formula, ...]) -> None:
        self.rule = rule
        self.formula = formula
        self.premises = premises

    def __call__(self, inputs: dict) -> Formula:
        cited = [inputs[f"c{j}"] for j in range(len(inputs))]
        mini = [Step(f, Rule.PREMISE, ()) for f in cited] + [Step(self.formula, self.rule, tuple(range(len(cited))))]
        result = check(mini, list(cited) + list(self.premises))
        if not result.ok:
            raise ProofStepError(result.reason)
        return self.formula


@dataclass(frozen=True)
class RecordedProof:
    """The result of :func:`record_proof`: ``prefix`` and ``parts``, the step Parts in step order (``parts[i]`` is bound at ``px.<prefix>.<i>``). ``conclusion`` is the last one."""

    prefix: str
    parts: tuple[Part, ...]

    @property
    def conclusion(self) -> Part:
        return self.parts[-1]


def _check_args(store: object, prefix: object) -> None:
    if not isinstance(store, PxC):
        raise TypeError(f"store must be a PxC, not {type(store).__name__}")
    if not isinstance(prefix, str):
        raise TypeError(f"prefix must be a str, not {type(prefix).__name__}")
    if _PREFIX.fullmatch(prefix) is None:
        raise ValueError(f"prefix {prefix!r} is not an identifier ([A-Za-z_][A-Za-z0-9_]*)")


def record_proof(store: PxC, prefix: str, proof: Sequence[Step], premises: Iterable[Formula]) -> Judgment:
    """Record ``proof`` (checked against ``premises``) in ``store`` as one Part per step, inside ONE tick named ``"proof.<prefix>"``.

    * ``TypeError`` for a non-PxC store, a non-str prefix, a ``proof`` that is not a sequence of ``Step``, or premises that are not all ``Formula``;
      ``ValueError`` if ``prefix`` does not fullmatch ``[A-Za-z_][A-Za-z0-9_]*``. (``premises`` may be any iterable, consumed once.)
    * An EMPTY proof is ``INVALID`` with a reason starting ``"empty proof"`` (nothing could be replayed); the store is untouched.
    * Otherwise run ``result = dsdk.logic.check(proof, premises)`` first. Then, inside the tick, compose the steps in order as described in the module docstring. If
      ``result`` is not ok, composing reaches step ``result.bad_step`` and raises :class:`ProofStepError` carrying ``result.reason`` THERE (inside the tick), so the tick rolls
      back: no address is bound, and the receipts of the steps already attempted are FAILED. The function catches the error and returns
      ``INVALID`` with the reason ``result.reason`` exactly (``"step 2 (modus_ponens): ..."``) and ``value None``.
    * Success: ``KNOWN`` with a :class:`RecordedProof`. The store then holds ``len(proof)`` new bindings ``px.<prefix>.0 ...`` and ``len(proof)`` PRODUCED receipts, all with
      ``tick == "proof.<prefix>"``.
    * Other exceptions of the store propagate unchanged and roll the tick back: ``AddressOccupiedError`` if ``px.<prefix>.<i>`` is taken, ``TickInProgressError`` if a tick is open.
    """
    _check_args(store, prefix)
    if not isinstance(proof, Sequence) or isinstance(proof, (str, bytes)):
        raise TypeError(f"proof must be a sequence of Step, not {type(proof).__name__}")
    steps = list(proof)
    if not all(isinstance(s, Step) for s in steps):
        raise TypeError("proof must be a sequence of Step objects")
    prem = tuple(premises)
    if not all(isinstance(f, Formula) for f in prem):
        raise TypeError("premises must all be Formula objects")
    if not steps:
        return Judgment(Status.INVALID, None, "empty proof: there is nothing to record")
    result = check(steps, prem)
    parts: list[Part] = []
    try:
        with store.tick(f"proof.{prefix}") as tx:
            for i, step in enumerate(steps):
                if not result.ok and i == result.bad_step:
                    raise ProofStepError(result.reason)
                inputs = {f"c{j}": parts[c] for j, c in enumerate(step.cites)}
                parts.append(tx.compose(f"px.{prefix}.{i}", Part(StepCalculation(step.rule, step.formula, prem)), inputs))
    except ProofStepError as exc:
        return Judgment(Status.INVALID, None, str(exc))
    return Judgment(Status.KNOWN, RecordedProof(prefix, tuple(parts)), "")


def replay_proof(store: PxC, prefix: str) -> Judgment:
    """Rebuild the proof recorded under ``prefix`` from the store's lineage ALONE and re-check it.

    ``TypeError`` / ``ValueError`` for the arguments as in :func:`record_proof`. Then read ``px.<prefix>.0, .1, ...`` while bound:

    * none bound -> ``NOT_OBSERVED`` (reason names the prefix);
    * for each step Part ``p``: it must be a composed Part whose calculation holds a :class:`StepCalculation` and whose inputs are named ``c0, c1, ...`` (in that order) and are each
      one of the EARLIER step Parts (compared by identity), else ``INVALID`` with a reason starting ``f"step {i} was not produced by a proof step"`` (raw Parts, other
      calculations) or ``f"step {i} cites a Part that is not an earlier step of this proof"``; all steps must share the same premises tuple (else ``INVALID``, reason starting ``"steps disagree about the premises"``);
    * the Step is ``Step(p.value, calc.rule, cites)`` with ``cites`` the indices of the input Parts, in input order;
    * finally ``dsdk.logic.check(steps, premises)``: ``KNOWN`` with the tuple of rebuilt ``Step`` objects when valid, ``INVALID`` with ``check``'s reason otherwise.
    For a proof recorded by ``record_proof`` the rebuilt steps EQUAL the original ones.
    """
    _check_args(store, prefix)
    parts: list[Part] = []
    while store.has(f"px.{prefix}.{len(parts)}"):
        parts.append(store.get(f"px.{prefix}.{len(parts)}"))
    if not parts:
        return Judgment(Status.NOT_OBSERVED, None, f"no proof is recorded under {prefix!r}")
    steps: list[Step] = []
    premises: tuple[Formula, ...] | None = None
    for i, p in enumerate(parts):
        comp = p.composition
        calc = comp.calculation.value if comp is not None else None
        names = list(comp.inputs.keys()) if comp is not None else None
        if not isinstance(calc, StepCalculation) or names != [f"c{j}" for j in range(len(names))]:
            return Judgment(Status.INVALID, None, f"step {i} was not produced by a proof step")
        cites: list[int] = []
        for inp in comp.inputs.values():
            j = next((j for j in range(i) if parts[j] is inp), None)
            if j is None:
                return Judgment(Status.INVALID, None, f"step {i} cites a Part that is not an earlier step of this proof")
            cites.append(j)
        if premises is None:
            premises = calc.premises
        elif calc.premises != premises:
            return Judgment(Status.INVALID, None, "steps disagree about the premises")
        steps.append(Step(p.value, calc.rule, tuple(cites)))
    result = check(steps, premises)
    if not result.ok:
        return Judgment(Status.INVALID, None, result.reason)
    return Judgment(Status.KNOWN, tuple(steps), "")
