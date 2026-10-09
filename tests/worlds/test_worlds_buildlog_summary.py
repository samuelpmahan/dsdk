"""Build-ledger summaries: first-try rate with an EXACT interval computed by dsdk.prob, and a per-round throughput series.

Hand counts over the frozen 12-line ledger sample (fixtures/worlds/ledger_sample.jsonl), read from its lines:
  Haiku first attempts: 10, of which 9 passed (line 2 is "partial")   Sonnet first attempts: 1 (pass)   Opus: none.
  Round 0 = lines 1-4 (4 attempts, 3 passes; 3 of its 4 attempts are first tries, 2 of those passed; wall 163+212+291+332 = 998 s)
  Round 1 = lines 6-7, round 2 = lines 8-9, round 3 = lines 10-12; line 5 (a Sonnet contract) has no round and is left out.
Textbook exact (Clopper-Pearson) 95% intervals used as the independent check:
  9 of 10 -> (0.5550, 0.9975)    1 of 1 -> (0.025, 1)    0 of 3 -> (0, 1 - 0.025**(1/3) = 0.7076)
"""
import ast
import inspect
import json
from pathlib import Path

import pytest

from dsdk.core import Status
from dsdk.prob import exact_interval
from dsdk.worlds import FirstTry, RoundStats, first_try_summary, load_ledger, parse_ledger, round_throughput
from dsdk.worlds import buildlog

SAMPLE = Path(__file__).resolve().parents[2] / "fixtures" / "worlds" / "ledger_sample.jsonl"


def line(**over):
    base = {"ts": 1, "task": "T1", "model": "haiku", "attempt": 1, "outcome": "pass", "wall_s": 5}
    base.update(over)
    return json.dumps(base)


# ==== The first-try summary carries the pass count and an exact interval ====


def test_haiku_first_try_summary_on_the_sample_is_nine_of_ten_with_the_textbook_exact_interval():
    """On the frozen sample Haiku passed 9 of its 10 first attempts, and the 95% interval is the textbook exact (Clopper-Pearson) interval 0.5550 to 0.9975, not a Wilson interval."""
    j = first_try_summary(load_ledger(SAMPLE), "haiku")
    assert j.status is Status.KNOWN and isinstance(j.value, FirstTry)
    v = j.value
    assert (v.passes, v.attempts, v.rate, v.confidence) == (9, 10, 0.9, 0.95)
    assert round(v.low, 4) == 0.5550 and round(v.high, 4) == 0.9975
    assert j.reason == "9/10 attempt-1 runs passed; exact 95% interval 0.555 to 0.997"


def test_the_interval_is_exactly_what_dsdk_prob_returns():
    """The interval in the summary equals dsdk.prob.exact_interval for the same counts, number for number, so worlds does no interval arithmetic of its own."""
    entries = load_ledger(SAMPLE)
    for model in ("haiku", "sonnet"):
        v = first_try_summary(entries, model).value
        assert (v.low, v.high) == exact_interval(v.passes, v.attempts, 0.95)


def test_a_single_pass_gives_a_wide_interval_not_a_refusal():
    """One pass in one first attempt is KNOWN with the exact interval 0.025 to 1, which says plainly how little one run shows."""
    v = first_try_summary(load_ledger(SAMPLE), "sonnet").value
    assert (v.passes, v.attempts, v.high) == (1, 1, 1.0)
    assert v.low == pytest.approx(0.025, abs=1e-12)


def test_zero_passes_keep_a_lower_end_of_exactly_zero_and_the_closed_form_upper_end():
    """Zero passes in three first attempts gives rate 0.0 as a KNOWN value, with interval 0 to 1 - 0.025^(1/3) = 0.7076."""
    es = parse_ledger([line(outcome="fail"), line(outcome="error"), line(outcome="partial")])
    v = first_try_summary(es, "haiku").value
    assert (v.passes, v.attempts, v.rate, v.low) == (0, 3, 0.0, 0.0)
    assert v.high == pytest.approx(1 - 0.025 ** (1 / 3), abs=1e-9)


def test_confidence_is_passed_through_to_the_interval_and_printed():
    """A different confidence level changes the interval (99% is wider than 95%) and the reason prints the level, for example 99%."""
    es = load_ledger(SAMPLE)
    narrow, wide = first_try_summary(es, "haiku").value, first_try_summary(es, "haiku", confidence=0.99).value
    assert wide.low < narrow.low and wide.high >= narrow.high and wide.confidence == 0.99
    assert (wide.low, wide.high) == exact_interval(9, 10, 0.99)
    assert "exact 99% interval" in first_try_summary(es, "haiku", confidence=0.99).reason


def test_retries_other_models_and_non_passes_are_not_counted_as_first_try_passes():
    """Second attempts, other models and 'partial', 'fail' and 'error' outcomes do not count: here 1 pass in 4 Haiku first attempts."""
    es = parse_ledger([line(outcome="fail"), line(attempt=2, outcome="pass"), line(outcome="partial"), line(outcome="error"),
                       line(model="sonnet"), line(outcome="pass")])
    v = first_try_summary(es, "haiku").value
    assert (v.passes, v.attempts) == (1, 4)


def test_no_first_attempts_is_not_observed_and_a_bad_question_is_invalid():
    """A model with no first attempts is NOT_OBSERVED (nothing measured), while an empty model name or a nonsense confidence (0, 1, NaN, a bool, a string) is INVALID with a reason, and nothing raises."""
    es = load_ledger(SAMPLE)
    j = first_try_summary(es, "opus")
    assert (j.status, j.value, j.reason) == (Status.NOT_OBSERVED, None, "no attempt-1 entries for 'opus'")
    assert first_try_summary(parse_ledger([line(attempt=2)]), "haiku").status is Status.NOT_OBSERVED
    for model, conf in (("", 0.95), (None, 0.95), (3, 0.95), ("haiku", 0), ("haiku", 1), ("haiku", 1.5), ("haiku", float("nan")),
                        ("haiku", True), ("haiku", "0.95"), ("haiku", None)):
        j = first_try_summary(es, model, confidence=conf)
        assert j.status is Status.INVALID and j.value is None and j.reason.strip(), (model, conf)
    assert first_try_summary(es, "", confidence=0).reason == "model must be a non-empty string"  # the model is checked first


def test_summary_accepts_a_one_shot_iterator():
    """first_try_summary works when handed a one-shot iterator rather than a tuple."""
    assert first_try_summary(iter(parse_ledger([line()])), "haiku").value.passes == 1


def test_the_live_ledger_summary_agrees_with_a_recount():
    """On the live ledger, the Haiku first-try counts equal a plain recount of the file and the interval brackets the rate."""
    rows = [json.loads(x) for x in (Path(buildlog.LEDGER_PATH)).read_text().splitlines() if x.strip()]
    first = [r for r in rows if r["model"] == "haiku" and r["attempt"] == 1]
    v = first_try_summary(load_ledger(), "haiku").value
    assert (v.passes, v.attempts) == (sum(r["outcome"] == "pass" for r in first), len(first))
    assert v.low <= v.rate <= v.high


# ==== worlds really calls dsdk.prob and does no interval math itself ====


def test_buildlog_calls_exact_interval_and_contains_no_interval_arithmetic():
    """buildlog.py imports and calls dsdk.prob.exact_interval, and its source has no square root, binomial coefficient, power or z-score of its own."""
    src = Path(inspect.getsourcefile(buildlog)).read_text()
    tree = ast.parse(src)
    imported = {a.name for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module == "dsdk.prob" for a in n.names}
    called = {n.func.id for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
    assert "exact_interval" in imported and "exact_interval" in called
    summary_src = inspect.getsource(first_try_summary)
    for forbidden in ("sqrt", "comb", "**", "1.96", "z *", "wilson", "pow("):
        assert forbidden not in summary_src, f"interval arithmetic in first_try_summary: {forbidden!r}"


# ==== Per-round throughput series ====


def test_round_throughput_on_the_sample_matches_the_hand_count():
    """On the frozen sample there are four rounds (0 to 3) with 4, 2, 2 and 3 attempts, the Sonnet contract without a round is left out, and round 0 has 3 passes, 3 first tries (2 passed) and 998 agent-seconds."""
    rounds = round_throughput(load_ledger(SAMPLE))
    assert [r.round for r in rounds] == [0, 1, 2, 3]
    assert all(isinstance(r, RoundStats) for r in rounds)
    assert [(r.attempts, r.passes) for r in rounds] == [(4, 3), (2, 2), (2, 2), (3, 3)]
    r0 = rounds[0]
    assert (r0.first_try_attempts, r0.first_try_passes, r0.agent_seconds, r0.tests_green) == (3, 2, 998.0, 0)
    assert (r0.started, r0.finished, r0.models) == (1791492929, 1791493098, ("haiku",))
    assert [(r.agent_seconds, r.tests_green) for r in rounds[1:]] == [(293.0, 172), (241.0, 272), (830.0, 174)]
    assert [(r.started, r.finished) for r in rounds[1:]] == [(1791494048, 1791494189), (1791494223, 1791494270), (1791494379, 1791494496)]


def test_round_throughput_ignores_unrounded_entries_and_keeps_gaps_and_order():
    """Entries without a round are left out, rounds come out in ascending order whatever order the ledger lists them, and a missing round number (a gap) stays missing."""
    es = parse_ledger([line(round=5), line(round=2), line(), line(round=5, task="T2")])
    assert [(r.round, r.attempts) for r in round_throughput(es)] == [(2, 1), (5, 2)]
    assert round_throughput(()) == () and round_throughput(parse_ledger([line()])) == ()


def test_tests_green_counts_only_passing_entries_with_a_test_count():
    """tests_green adds up tests_passed only for entries that passed and recorded a count: a failed attempt's tests and a missing count add nothing, and a recorded zero is just zero."""
    es = parse_ledger([line(round=1, tests_passed=10, tests_total=10), line(round=1, outcome="fail", tests_passed=3, tests_total=9),
                       line(round=1), line(round=1, tests_passed=0, tests_total=4)])
    assert round_throughput(es)[0].tests_green == 10


def test_models_in_a_round_are_sorted_and_distinct_and_times_are_min_and_max():
    """A round that mixes models lists each once in alphabetical order, and started and finished are the smallest and largest timestamps, not the first and last lines."""
    es = parse_ledger([line(round=1, ts=50, model="sonnet"), line(round=1, ts=10, model="haiku"), line(round=1, ts=30, model="haiku")])
    r = round_throughput(es)[0]
    assert (r.models, r.started, r.finished) == (("haiku", "sonnet"), 10, 50)


def test_round_throughput_accepts_a_one_shot_iterator():
    """round_throughput works when handed a one-shot iterator rather than a tuple."""
    assert len(round_throughput(iter(parse_ledger([line(round=1)])))) == 1


def test_round_totals_add_up_to_the_ledger():
    """Summed over all rounds, attempts equal the number of ledger entries that have a round, so nothing is dropped or double counted."""
    es = load_ledger()
    assert sum(r.attempts for r in round_throughput(es)) == sum(1 for e in es if e.round is not None)
    assert sum(r.first_try_attempts for r in round_throughput(es)) == sum(1 for e in es if e.round is not None and e.attempt == 1)
