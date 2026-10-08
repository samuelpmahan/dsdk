"""Epistemic status: how much do we know about a value, and why not?

Every package from A1 on reports "I do not have a value" in one of several
different ways. Collapsing them into ``None`` loses information that later
tracks (belief, probability, constraints) need, so the kernel names them.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class Status(Enum):
    """Why a :class:`Judgment` does or does not carry a value.

    * ``KNOWN`` -- the value has been determined. ``Judgment.value`` holds it.
      The value may be falsy (``False``, ``0``, ``""``); it is merely not ``None``.
    * ``UNKNOWN`` -- the question was posed *with* its context observed, but the
      evidence is insufficient to determine the value. Example: the three-valued
      result of ``x AND y`` when ``x`` and ``y`` are both unassigned.
    * ``NOT_OBSERVED`` -- nothing has been measured or supplied for this at all.
      This is absence of data, not insufficiency of data. Example: a cell the
      agent has never perceived. (Contrast ``UNKNOWN``: there the inputs exist.)
    * ``INVALID`` -- the question or its inputs violate a contract, so no value
      could be meaningful. A reason is mandatory. Example: a probability of 1.7.
    * ``NOT_APPLICABLE`` -- the question does not make sense in this context.
      Example: "pit probability" of a cell that is a wall.
    """

    KNOWN = "known"
    UNKNOWN = "unknown"
    NOT_OBSERVED = "not_observed"
    INVALID = "invalid"
    NOT_APPLICABLE = "not_applicable"


@dataclass(frozen=True)
class Judgment:
    """An immutable (status, value, reason) triple.

    Construction rules (all checked in ``__post_init__``; the first violated
    rule raises, and the exception types below are part of the contract):

    1. ``status`` must be a :class:`Status` member, else ``TypeError``.
       (The plain string ``"known"`` is NOT accepted.)
    2. ``reason`` must be a ``str``, else ``TypeError``.
    3. ``status is Status.KNOWN``  =>  ``value is not None``, else ``ValueError``.
       ``None`` is the only forbidden value: ``False``, ``0``, ``""`` and ``[]``
       are legitimate known values.
    4. ``status is not Status.KNOWN``  =>  ``value is None``, else ``ValueError``.
    5. ``status is Status.INVALID``  =>  ``reason.strip() != ""``, else
       ``ValueError``. Other statuses may have an empty reason.

    Instances are frozen (assignment raises ``dataclasses.FrozenInstanceError``),
    compare by field equality, and are hashable iff ``value`` is hashable.
    """

    status: Status
    value: Any = None
    reason: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.status, Status):
            raise TypeError(f"status must be a Status member, got {self.status!r}")
        if not isinstance(self.reason, str):
            raise TypeError(f"reason must be a str, got {type(self.reason).__name__}")
        if self.status is Status.KNOWN:
            if self.value is None:
                raise ValueError("KNOWN judgment requires a non-None value")
        elif self.value is not None:
            raise ValueError(f"{self.status.name} judgment must not carry a value")
        if self.status is Status.INVALID and self.reason.strip() == "":
            raise ValueError("INVALID judgment requires a non-blank reason")
