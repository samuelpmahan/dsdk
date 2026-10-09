"""The build-ledger world: ops/ledger.jsonl as typed records, and first_try_rate as a Judgment.

fixtures/worlds/ledger_sample.jsonl is a frozen copy of the first 12 ledger lines, so the numbers below are stable
while the live ledger grows. Hand count over those 12 lines:
  haiku attempt-1 rows: lines 1,2,3,6,7,8,9,10,11,12 = 10 rows, 9 "pass" (line 2 is "partial")  -> 0.9
  haiku attempt-2: line 4 (pass), not counted.  sonnet attempt-1: line 5 only, "pass".  opus: none.
"""
import json
from pathlib import Path

import pytest

from dsdk.core import Status
from dsdk.worlds import LEDGER_PATH, OUTCOMES, LedgerEntry, LedgerError, WorldError, first_try_rate, load_ledger, models, parse_ledger

SAMPLE = Path(__file__).resolve().parents[2] / "fixtures" / "worlds" / "ledger_sample.jsonl"


def line(**over):
    base = {"ts": 1, "task": "T1", "model": "haiku", "attempt": 1, "outcome": "pass", "wall_s": 5}
    base.update(over)
    return json.dumps({k: v for k, v in base.items() if v is not ...})


# ==== Loading the ledger as typed records ====
def test_sample_loads_as_typed_records():
    """The frozen 12-line ledger sample loads as 12 typed records whose fields (task, model, attempt, outcome, wall seconds, tests, round, note) carry the values on those lines, with seconds as floats and missing test counts as None."""
    entries = load_ledger(SAMPLE)
    assert len(entries) == 12 and all(isinstance(e, LedgerEntry) for e in entries)
    e = entries[1]
    assert (e.line, e.task, e.model, e.attempt, e.outcome, e.wall_s, e.round) == (2, "inv-misc", "haiku", 1, "partial", 212.0, 0)
    assert isinstance(e.wall_s, float) and e.tests_passed is None and e.tests_total is None
    assert e.note.startswith("15 files ok")
    t = entries[5]
    assert (t.task, t.tests_passed, t.tests_total, t.round) == ("T01", 41, 41, 1)
    assert entries[4].model == "sonnet" and entries[4].round is None
    assert [x.line for x in entries] == list(range(1, 13))


def test_models_are_sorted_and_distinct():
    """models() lists each model name once, alphabetically, and gives an empty tuple for no entries."""
    assert models(load_ledger(SAMPLE)) == ("haiku", "sonnet")
    assert models(()) == ()


# ==== First-try rate as a Judgment (known, unknown, not observed, invalid) ====
def test_first_try_rate_known():
    """On the sample, Haiku passed 9 of its 10 first attempts, so first_try_rate says KNOWN 0.9 with the reason '9/10 attempt-1 runs passed'."""
    j = first_try_rate(load_ledger(SAMPLE), "haiku")
    assert (j.status, j.value, j.reason) == (Status.KNOWN, 0.9, "9/10 attempt-1 runs passed")


def test_first_try_rate_ignores_retries_and_counts_only_pass():
    """Second attempts and other models are not counted, and 'partial', 'fail' and 'error' outcomes do not count as passes: 1 pass in 4 first attempts is 0.25."""
    es = parse_ledger([line(outcome="fail"), line(attempt=2, outcome="pass"), line(outcome="partial"), line(outcome="error"),
                       line(model="sonnet"), line(outcome="pass")])
    j = first_try_rate(es, "haiku")
    assert j.value == 0.25 and j.reason == "1/4 attempt-1 runs passed"


def test_zero_percent_is_a_known_value_not_a_missing_one():
    """A model that failed every first attempt gets KNOWN 0.0, not 'unknown': zero is a measured value."""
    j = first_try_rate(parse_ledger([line(outcome="fail")]), "haiku")
    assert j.status is Status.KNOWN and j.value == 0.0


def test_not_observed_unknown_and_invalid_stay_distinct():
    """No data for a model is NOT_OBSERVED, too little data (fewer than min_n) is UNKNOWN, a nonsense question (empty model, min_n of 0, a bool) is INVALID, and enough data is KNOWN: four different answers, never merged."""
    es = load_ledger(SAMPLE)
    no_data = first_try_rate(es, "opus")
    assert (no_data.status, no_data.value, no_data.reason) == (Status.NOT_OBSERVED, None, "no attempt-1 entries for 'opus'")
    thin = first_try_rate(es, "sonnet", min_n=2)
    assert (thin.status, thin.value, thin.reason) == (Status.UNKNOWN, None, "only 1 attempt-1 entries for 'sonnet', need 2")
    assert first_try_rate(es, "sonnet", min_n=1).value == 1.0
    for model, min_n in (("", 1), (None, 1), (3, 1), ("haiku", 0), ("haiku", -1), ("haiku", True), ("haiku", 1.0)):
        j = first_try_rate(es, model, min_n=min_n)
        assert j.status is Status.INVALID and j.reason.strip(), (model, min_n)
    assert first_try_rate(es, "haiku", min_n=10).status is Status.KNOWN
    assert first_try_rate(es, "haiku", min_n=11).status is Status.UNKNOWN


def test_a_model_with_only_retries_is_not_observed_for_first_tries():
    """A model that only appears as a second attempt has no first-try data, so its first-try rate is NOT_OBSERVED."""
    j = first_try_rate(parse_ledger([line(attempt=2)]), "haiku")
    assert j.status is Status.NOT_OBSERVED


def test_first_try_rate_accepts_a_one_shot_iterator():
    """first_try_rate works when given a one-shot iterator rather than a tuple, consuming it once."""
    assert first_try_rate(iter(parse_ledger([line()])), "haiku").value == 1.0


# ==== Reading ledger lines and rejecting malformed ones ====
def test_blank_lines_are_skipped_but_counted():
    """Blank lines produce no entry but still count toward line numbers, so a record on physical line 4 reports line 4."""
    es = parse_ledger(["", line(), "   ", line(task="T2")])
    assert [e.line for e in es] == [2, 4]
    assert parse_ledger([]) == () and parse_ledger(["", " "]) == ()


def test_optional_fields_default():
    """Omitted tests_passed, tests_total, round and note default to None, None, None and an empty string, a zero test count is kept as 0, and wall seconds may be a float."""
    e = parse_ledger([line()])[0]
    assert (e.tests_passed, e.tests_total, e.round, e.note) == (None, None, None, "")
    assert parse_ledger([line(tests_passed=0, tests_total=0)])[0].tests_passed == 0
    assert parse_ledger([line(wall_s=1.5)])[0].wall_s == 1.5


BAD = {
    "invalid json": ("{not json", "line 1: invalid JSON"),
    "array": ("[1]", "line 1: not an object"),
    "missing ts": (line(ts=...), "line 1: missing key 'ts'"),
    "missing wall_s": (line(wall_s=...), "line 1: missing key 'wall_s'"),
    "unknown key": (line(extra=1), "line 1: unknown key 'extra'"),
    "ts bool": (line(ts=True), "ts"),
    "ts float": (line(ts=1.5), "ts"),
    "empty task": (line(task=""), "task"),
    "model not str": (line(model=3), "model"),
    "attempt zero": (line(attempt=0), "attempt"),
    "attempt bool": (line(attempt=True), "attempt"),
    "bad outcome": (line(outcome="passed"), "outcome"),
    "negative wall": (line(wall_s=-1), "wall_s"),
    "wall bool": (line(wall_s=True), "wall_s"),
    "wall string": (line(wall_s="5"), "wall_s"),
    "tests_passed negative": (line(tests_passed=-1, tests_total=3), "tests_passed"),
    "tests_passed bool": (line(tests_passed=True, tests_total=3), "tests_passed"),
    "passed exceeds total": (line(tests_passed=5, tests_total=4), "tests_passed"),
    "round float": (line(round=1.5), "round"),
    "note not str": (line(note=3), "note"),
}


@pytest.mark.parametrize("name", BAD)
def test_malformed_lines_raise_ledger_error_with_the_line_number(name):
    """Each kind of malformed ledger line (bad JSON, wrong types, unknown key, impossible values) raises LedgerError starting with 'line 1:' and naming the offending field."""
    text, expect = BAD[name]
    with pytest.raises(LedgerError) as err:
        parse_ledger([text])
    assert expect in str(err.value) and str(err.value).startswith("line 1:")
    assert isinstance(err.value, WorldError)


def test_the_error_names_the_physical_line():
    """When the third physical line is bad, the error message starts with 'line 3:' even though blank lines come before it."""
    with pytest.raises(LedgerError) as err:
        parse_ledger([line(), "", line(outcome="nope")])
    assert str(err.value).startswith("line 3:")


def test_non_finite_wall_time_is_rejected():
    """NaN and Infinity wall times (which Python's JSON parser accepts) are rejected as ledger errors."""
    with pytest.raises(LedgerError):
        parse_ledger(['{"ts":1,"task":"a","model":"m","attempt":1,"outcome":"pass","wall_s":NaN}'])
    with pytest.raises(LedgerError):
        parse_ledger(['{"ts":1,"task":"a","model":"m","attempt":1,"outcome":"pass","wall_s":Infinity}'])


def test_outcomes_and_default_path():
    """The accepted outcomes are exactly pass, partial, fail and error, and the default ledger path is ops/ledger.jsonl."""
    assert OUTCOMES == ("pass", "partial", "fail", "error")
    assert LEDGER_PATH.name == "ledger.jsonl" and LEDGER_PATH.parent.name == "ops"


def test_load_ledger_edge_cases(tmp_path):
    """An empty ledger file loads as no entries, a missing file raises FileNotFoundError, and non-ASCII notes survive UTF-8 reading."""
    empty = tmp_path / "e.jsonl"
    empty.write_text("")
    assert load_ledger(empty) == () and load_ledger(str(empty)) == ()
    with pytest.raises(FileNotFoundError):
        load_ledger(tmp_path / "missing.jsonl")
    uni = tmp_path / "u.jsonl"
    uni.write_text(line(note="café ✓") + "\n", encoding="utf-8")
    assert load_ledger(uni)[0].note == "café ✓"


def test_the_live_ledger_still_satisfies_the_schema():
    """Schema guard: if ops/ledger.py ever writes a field or outcome this module does not know, this fails loudly."""
    if not LEDGER_PATH.exists():
        pytest.skip("no live ledger")
    entries = load_ledger()
    assert len(entries) >= 12 and all(e.outcome in OUTCOMES for e in entries)
    assert entries[:12] == load_ledger(SAMPLE)
