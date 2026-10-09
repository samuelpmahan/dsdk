"""Belief updates as ``dsdk.core`` ticks, so every update leaves lineage (track A3 x A0).

A *belief series* named ``name`` lives in a ``dsdk.core.PxC`` store at these addresses (decimal indices, no padding)::

    px.<name>.belief.0        the starting belief (a raw Part, bound by start_series)
    px.<name>.evidence.<k>    the k-th observed formula (k >= 1), a composed Part
    px.<name>.belief.<k>      the belief after the k-th observation, a composed Part

Update ``k`` runs inside ONE tick ``"<name>.observe.<k>"`` with two composes, in this order:

1. ``px.<name>.evidence.<k>``  composed by a shared calculation Part ``_RECORD_EVIDENCE`` from inputs ``{"formula": Part(evidence)}``;
   its value is the evidence Formula.
2. ``px.<name>.belief.<k>``    composed by a shared calculation Part ``_CONDITION`` from inputs
   ``{"prev": <Part at px.<name>.belief.<k-1>>, "evidence": <the Part returned by compose 1>}``; its value is
   ``condition(prev belief, evidence formula)``.

So ``belief.k.composition.inputs["prev"] is belief.(k-1)`` (identity) and the lineage DAG (``dsdk.graph.lineage_graph``) of the
newest belief contains every earlier belief and every piece of evidence. Both calculation Parts are module-level
``Part(function)`` objects shared by all updates (a calculation is behaviour, kept by reference).

Impossible evidence never touches the store: :func:`observe` checks the evidence probability FIRST (nothing is composed, no
receipt is recorded) and returns an INVALID Judgment.
"""
from __future__ import annotations

import re

from dsdk.core import Judgment, Part, PxC, Status
from dsdk.logic import Formula, variables

from .worlds import Belief, condition, probability

_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


def _record_evidence(inputs: dict) -> Formula:
    return inputs["formula"]


def _apply_condition(inputs: dict) -> Belief:
    return condition(inputs["prev"], inputs["evidence"])


_RECORD_EVIDENCE = Part(_record_evidence)
_CONDITION = Part(_apply_condition)


def _check_series(store: object, name: object) -> None:
    if not isinstance(store, PxC):
        raise TypeError("store must be a PxC")
    if not isinstance(name, str):
        raise TypeError("name must be a str")
    if _NAME.fullmatch(name) is None:
        raise ValueError(f"series name {name!r} must match [A-Za-z_][A-Za-z0-9_]*")


def start_series(store: PxC, name: str, belief: Belief) -> Part:
    """Bind ``Part(belief)`` at ``px.<name>.belief.0`` with ``store.set`` and return it. ``TypeError`` for a non-PxC store,
    non-str name or non-Belief; ``ValueError`` if ``name`` does not fullmatch ``[A-Za-z_][A-Za-z0-9_]*``;
    ``AddressOccupiedError`` if the series already exists (a series cannot be restarted: write-once)."""
    _check_series(store, name)
    if not isinstance(belief, Belief):
        raise TypeError(f"belief must be a Belief, not {type(belief).__name__}")
    part = Part(belief)
    store.set(f"px.{name}.belief.0", part)
    return part


def belief_history(store: PxC, name: str) -> tuple[Part, ...]:
    """The belief Parts ``px.<name>.belief.0``, ``.1``, ... that are bound, in order, up to the first index that is not bound.
    ``MissingPartError`` if ``px.<name>.belief.0`` is not bound. Type/name checks as in :func:`start_series`."""
    _check_series(store, name)
    parts = [store.get(f"px.{name}.belief.0")]
    while store.has(f"px.{name}.belief.{len(parts)}"):
        parts.append(store.get(f"px.{name}.belief.{len(parts)}"))
    return tuple(parts)


def current_belief(store: PxC, name: str) -> Part:
    """The newest belief Part of the series (the last of :func:`belief_history`)."""
    return belief_history(store, name)[-1]


def observe(store: PxC, name: str, evidence: Formula) -> Judgment:
    """Condition the series' newest belief on ``evidence`` and record the update as a tick.

    Argument errors raise: ``TypeError`` (store/name/evidence of the wrong type), ``ValueError`` (bad name),
    ``MissingPartError`` (series not started). ``dsdk.core.TickInProgressError`` propagates if a tick is already open.
    Then, with ``prev`` = newest belief Part, ``k = len(belief_history(store, name))`` and ``b = prev.value``:

    * evidence mentions a variable that ``b`` does not model -> ``UNKNOWN`` (reason lists them like ``probability``);
    * ``probability(b, evidence)`` is not KNOWN or is 0 -> ``INVALID`` (reason mentions the impossible evidence);
      in both cases the store is NOT touched (no Part, no receipt);
    * otherwise run the tick described in the module docstring and return ``KNOWN`` with the NEW belief Part as its value.

    If a compose inside the tick raises (e.g. ``px.<name>.evidence.<k>`` was bound by someone else) the tick rolls back: nothing is
    bound and the exception propagates unchanged (``dsdk.core`` semantics; do not re-implement them).
    Receipts of a successful update: 2 PRODUCED receipts, both with ``tick == "<name>.observe.<k>"``.
    """
    _check_series(store, name)
    if not isinstance(evidence, Formula):
        raise TypeError(f"evidence must be a Formula, not {type(evidence).__name__}")
    history = belief_history(store, name)
    prev = history[-1]
    k = len(history)
    b = prev.value
    missing = set(variables(evidence)) - set(b.variables)
    if missing:
        return Judgment(Status.UNKNOWN, None, "unmodelled variables: " + ", ".join(sorted(missing)))
    p = probability(b, evidence)
    if p.status is not Status.KNOWN or p.value == 0:
        return Judgment(Status.INVALID, None, "impossible evidence: " + (p.reason or "probability is zero"))
    with store.tick(f"{name}.observe.{k}") as tx:
        ev_part = tx.compose(f"px.{name}.evidence.{k}", _RECORD_EVIDENCE, {"formula": Part(evidence)})
        new_part = tx.compose(f"px.{name}.belief.{k}", _CONDITION, {"prev": prev, "evidence": ev_part})
    return Judgment(Status.KNOWN, new_part, "")
