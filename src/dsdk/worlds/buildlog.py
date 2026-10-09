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
from dsdk.prob import exact_interval  # noqa: F401  (used by first_try_summary)

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
    entries = []
    for number, text in enumerate(lines, start=1):
        if text.strip() == "":
            continue
        entries.append(_parse_line(number, text))
    return tuple(entries)


def _is_int(x: object) -> bool:
    return isinstance(x, int) and not isinstance(x, bool)


def _error(number: int, message: str) -> LedgerError:
    return LedgerError(f"line {number}: {message}")


def _finite_seconds(x: object) -> float | None:
    """The value as a float if it is a real, finite number >= 0; otherwise None."""
    if isinstance(x, bool) or not isinstance(x, (int, float)):
        return None
    try:
        value = float(x)
    except OverflowError:
        return None
    if not math.isfinite(value) or value < 0:
        return None
    return value


def _optional_count(obj: dict, key: str, number: int) -> int | None:
    value = obj.get(key)
    if value is None:
        return None
    if not _is_int(value) or value < 0:
        raise _error(number, f"{key} must be None or an int >= 0")
    return value


def _parse_line(number: int, text: str) -> LedgerEntry:
    try:
        obj = json.loads(text)
    except json.JSONDecodeError:
        raise _error(number, "invalid JSON") from None
    if not isinstance(obj, dict):
        raise _error(number, "not an object")
    for key in _REQUIRED:
        if key not in obj:
            raise _error(number, f"missing key {key!r}")
    for key in obj:
        if key not in _REQUIRED and key not in _OPTIONAL:
            raise _error(number, f"unknown key {key!r}")

    ts = obj["ts"]
    if not _is_int(ts):
        raise _error(number, "ts must be an int")
    task = obj["task"]
    if not isinstance(task, str) or task == "":
        raise _error(number, "task must be a non-empty string")
    model = obj["model"]
    if not isinstance(model, str) or model == "":
        raise _error(number, "model must be a non-empty string")
    attempt = obj["attempt"]
    if not _is_int(attempt) or attempt < 1:
        raise _error(number, "attempt must be an int >= 1")
    outcome = obj["outcome"]
    if outcome not in OUTCOMES:
        raise _error(number, f"outcome must be one of {', '.join(OUTCOMES)}")
    wall_s = _finite_seconds(obj["wall_s"])
    if wall_s is None:
        raise _error(number, "wall_s must be a finite number >= 0")

    tests_passed = _optional_count(obj, "tests_passed", number)
    tests_total = _optional_count(obj, "tests_total", number)
    if tests_passed is not None and tests_total is not None and tests_passed > tests_total:
        raise _error(number, "tests_passed must be <= tests_total")

    round_no = obj.get("round")
    if round_no is not None and not _is_int(round_no):
        raise _error(number, "round must be None or an int")
    note = obj.get("note", "")
    if not isinstance(note, str):
        raise _error(number, "note must be a string")

    return LedgerEntry(
        line=number,
        ts=ts,
        task=task,
        model=model,
        attempt=attempt,
        outcome=outcome,
        wall_s=wall_s,
        tests_passed=tests_passed,
        tests_total=tests_total,
        round=round_no,
        note=note,
    )


def load_ledger(path: str | Path | None = None) -> tuple[LedgerEntry, ...]:
    """``parse_ledger`` of the file's lines (UTF-8). ``path=None`` means :data:`LEDGER_PATH`. A missing file raises
    ``FileNotFoundError``; an empty file gives ``()``."""
    target = LEDGER_PATH if path is None else Path(path)
    return parse_ledger(target.read_text(encoding="utf-8").splitlines())


def models(entries: Iterable[LedgerEntry]) -> tuple[str, ...]:
    """The distinct model names, sorted alphabetically."""
    return tuple(sorted({e.model for e in entries}))


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
    if not isinstance(model, str) or model == "":
        return Judgment(Status.INVALID, None, "model must be a non-empty string")
    if not _is_int(min_n) or min_n < 1:
        return Judgment(Status.INVALID, None, "min_n must be an integer >= 1")

    seen = 0
    passes = 0
    for entry in entries:
        if entry.model == model and entry.attempt == 1:
            seen += 1
            if entry.outcome == "pass":
                passes += 1

    if seen == 0:
        return Judgment(Status.NOT_OBSERVED, None, f"no attempt-1 entries for {model!r}")
    if seen < min_n:
        return Judgment(Status.UNKNOWN, None, f"only {seen} attempt-1 entries for {model!r}, need {min_n}")
    return Judgment(Status.KNOWN, passes / seen, f"{passes}/{seen} attempt-1 runs passed")


# ==== first-try summary with an exact interval (dsdk.prob does the interval) and the per-round series ====


@dataclass(frozen=True)
class FirstTry:
    """First-try pass count with its exact confidence interval.

    ``passes`` first attempts passed out of ``attempts``; ``rate = passes / attempts`` (float); ``low`` / ``high`` are the ends of the
    exact (Clopper-Pearson) interval at ``confidence`` (a float strictly between 0 and 1), taken UNCHANGED from
    :func:`dsdk.prob.exact_interval`.
    """

    passes: int
    attempts: int
    rate: float
    low: float
    high: float
    confidence: float


def first_try_summary(entries: Iterable[LedgerEntry], model: str, *, confidence: object = 0.95) -> Judgment:
    """How often ``model`` passes on its FIRST attempt, with an exact interval from ``dsdk.prob``. Decision table:

    1. ``model`` not a non-empty ``str``: ``Judgment(Status.INVALID, None, "model must be a non-empty string")``.
       ``confidence`` not an ``int``/``float`` (``bool`` excluded), or not strictly between 0 and 1 (NaN included):
       ``Judgment(Status.INVALID, None, "confidence must be a number strictly between 0 and 1")``. The model is checked first.
       Never raises.
    2. No ``attempt == 1`` entry for ``model``: ``Judgment(Status.NOT_OBSERVED, None, f"no attempt-1 entries for {model!r}")``.
    3. Otherwise ``Judgment(Status.KNOWN, FirstTry(passes, attempts, passes / attempts, low, high, float(confidence)), reason)`` where
       ``passes`` counts ``outcome == "pass"`` among the attempt-1 entries, ``attempts`` counts those entries, and
       ``(low, high) = dsdk.prob.exact_interval(passes, attempts, confidence)``. This module does NO interval arithmetic of its own:
       it CALLS ``exact_interval`` and uses its numbers as they are. The reason is exactly
       ``f"{passes}/{attempts} attempt-1 runs passed; exact {pct}% interval {low:.3f} to {high:.3f}"`` with ``pct = f"{confidence * 100:g}"``
       (so ``0.95`` prints ``95``).

    There is no UNKNOWN case: one attempt gives a wide interval rather than a refusal, because the interval IS the statement of how
    little is known. ``entries`` may be a one-shot iterator (consumed once).
    """
    if not isinstance(model, str) or model == "":
        return Judgment(Status.INVALID, None, "model must be a non-empty string")
    if (
        isinstance(confidence, bool)
        or not isinstance(confidence, (int, float))
        or not (0 < confidence < 1)
    ):
        return Judgment(Status.INVALID, None, "confidence must be a number strictly between 0 and 1")

    passes = 0
    attempts = 0
    for entry in entries:
        if entry.model == model and entry.attempt == 1:
            attempts += 1
            if entry.outcome == "pass":
                passes += 1

    if attempts == 0:
        return Judgment(Status.NOT_OBSERVED, None, f"no attempt-1 entries for {model!r}")

    low, high = exact_interval(passes, attempts, confidence)
    pct = f"{float(confidence) * 100:g}"
    reason = f"{passes}/{attempts} attempt-1 runs passed; exact {pct}% interval {low:.3f} to {high:.3f}"
    value = FirstTry(passes, attempts, passes / attempts, low, high, float(confidence))
    return Judgment(Status.KNOWN, value, reason)


@dataclass(frozen=True)
class RoundStats:
    """What happened in one dispatch round (the ledger's ``round`` field).

    ``attempts`` / ``passes`` count every entry of the round and those with outcome ``pass``; ``first_try_attempts`` /
    ``first_try_passes`` count only ``attempt == 1`` entries. ``agent_seconds`` is the sum of ``wall_s``. ``tests_green`` is the sum of
    ``tests_passed`` over entries whose outcome is ``pass`` and whose ``tests_passed`` is not ``None``. ``started`` / ``finished`` are the
    smallest and largest ``ts``. ``models`` is the sorted tuple of distinct model names.
    """

    round: int
    attempts: int
    passes: int
    first_try_attempts: int
    first_try_passes: int
    agent_seconds: float
    tests_green: int
    started: int
    finished: int
    models: tuple[str, ...]


def round_throughput(entries: Iterable[LedgerEntry]) -> tuple[RoundStats, ...]:
    """One :class:`RoundStats` per round, in ASCENDING round number, for the Lab's throughput chart.

    Entries whose ``round`` is ``None`` (work that was not part of a dispatch round, such as a contract written by a manager) are
    left out. An empty input, or one with no round numbers, gives ``()``. Rounds with no entries do not appear (gaps stay gaps).
    ``entries`` may be a one-shot iterator.
    """
    groups: dict[int, list[LedgerEntry]] = {}
    for entry in entries:
        if entry.round is None:
            continue
        groups.setdefault(entry.round, []).append(entry)

    result = []
    for round_no in sorted(groups):
        group = groups[round_no]
        first_try = [e for e in group if e.attempt == 1]
        green = [e.tests_passed for e in group if e.outcome == "pass" and e.tests_passed is not None]
        result.append(
            RoundStats(
                round=round_no,
                attempts=len(group),
                passes=sum(1 for e in group if e.outcome == "pass"),
                first_try_attempts=len(first_try),
                first_try_passes=sum(1 for e in first_try if e.outcome == "pass"),
                agent_seconds=float(sum(e.wall_s for e in group)),
                tests_green=sum(green),
                started=min(e.ts for e in group),
                finished=max(e.ts for e in group),
                models=tuple(sorted({e.model for e in group})),
            )
        )
    return tuple(result)
