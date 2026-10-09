"""The build-ledger world: dsdk studying its own construction.

``ops/ledger.jsonl`` has one JSON object per line, one line per agent attempt (written by ``ops/ledger.py``).
This module loads it as typed records and answers one question the Lab asks about it -- "how often does a model
pass on its FIRST try?" -- with a :class:`dsdk.core.Judgment`, so "no data", "too little data" and "bad question"
stay different answers.

Line format (the schema is STRICT so drift in the writer is noticed)
--------------------------------------------------------------------
Required keys: ``ts`` (int, unix seconds), ``task`` (non-empty str), ``model`` (non-empty str), ``attempt`` (int >= 1),
``outcome`` (one of :data:`OUTCOMES`), ``wall_s`` (finite int or float >= 0; stored as ``float``).
Optional keys (default in brackets): ``tests_passed`` / ``tests_total`` (``None`` or int >= 0, and
``tests_passed <= tests_total`` when both are ints) [``None``], ``round`` (``None`` or int) [``None``], ``note``
(str) [``""``]. ``None`` in ``tests_passed`` means "tests were not run for this attempt" (NOT zero passes). Any
other key is an error. ``bool`` is never accepted where an int is expected.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from dsdk.core import Judgment, Status

from .lostlands import WorldError

LEDGER_PATH = Path(__file__).resolve().parents[3] / "ops" / "ledger.jsonl"
OUTCOMES = ("pass", "partial", "fail", "error")
_REQUIRED = ("ts", "task", "model", "attempt", "outcome", "wall_s")
_OPTIONAL = ("tests_passed", "tests_total", "round", "note")


class LedgerError(WorldError):
    """A ledger line is malformed. The message starts with ``"line N:"`` (N counts physical lines from 1)."""


@dataclass(frozen=True)
class LedgerEntry:
    line: int
    ts: int
    task: str
    model: str
    attempt: int
    outcome: str
    wall_s: float
    tests_passed: int | None
    tests_total: int | None
    round: int | None
    note: str



def parse_ledger(lines: Iterable[str]) -> tuple[LedgerEntry, ...]:
    """Parse ledger text, one string per physical line, into entries in file order.

    Blank (or whitespace-only) lines are skipped but still count toward line numbers. Every other line must be a
    JSON object satisfying the format in the module docstring; the first violation raises :class:`LedgerError`
    whose message starts ``f"line {n}:"`` and names the key (``"invalid JSON"``, ``"not an object"``,
    ``"missing key 'x'"``, ``"unknown key 'x'"``, ``"outcome must be one of ..."``, ``"... must be ..."``).
    ``LedgerEntry.line`` is the 1-based physical line number.
    """
    raise NotImplementedError


def load_ledger(path: str | Path | None = None) -> tuple[LedgerEntry, ...]:
    """``parse_ledger`` of the file's lines (UTF-8). ``path=None`` means :data:`LEDGER_PATH`. A missing file raises
    ``FileNotFoundError``; an empty file gives ``()``."""
    raise NotImplementedError


def models(entries: Iterable[LedgerEntry]) -> tuple[str, ...]:
    """The distinct model names, sorted alphabetically."""
    raise NotImplementedError


def first_try_rate(entries: Iterable[LedgerEntry], model: str, *, min_n: int = 1) -> Judgment:
    """Fraction of ``model``'s FIRST attempts (``attempt == 1``) whose outcome is ``"pass"``. Decision table:

    1. ``model`` not a non-empty ``str``, or ``min_n`` not an ``int`` >= 1 (``bool`` is not an int):
       ``Judgment(Status.INVALID, None, reason)`` with a non-blank reason (``"model must be a non-empty string"`` /
       ``"min_n must be an integer >= 1"``). Never raises.
    2. No attempt-1 entry for ``model`` at all: ``Judgment(Status.NOT_OBSERVED, None, f"no attempt-1 entries for
       {model!r}")``. (Nothing was measured; that is not a rate of 0.)
    3. Some, but fewer than ``min_n``: ``Judgment(Status.UNKNOWN, None, f"only {n} attempt-1 entries for {model!r},
       need {min_n}")``.
    4. Otherwise ``Judgment(Status.KNOWN, passes / n, f"{passes}/{n} attempt-1 runs passed")`` where ``passes`` counts
       ``outcome == "pass"`` (``partial``, ``fail`` and ``error`` do not count). The value is a ``float`` (0.0 is a
       legitimate KNOWN value).
    ``entries`` may be any iterable (consumed once).
    """
    raise NotImplementedError
