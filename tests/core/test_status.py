"""Contract tests for dsdk.core.Status / Judgment (clauses: members, construction, immutability)."""
import dataclasses

import pytest

from dsdk.core import Judgment, Status

ALL = [Status.KNOWN, Status.UNKNOWN, Status.NOT_OBSERVED, Status.INVALID, Status.NOT_APPLICABLE]
NON_KNOWN = [s for s in ALL if s is not Status.KNOWN]


# --- Clause 1: the five statuses exist and are distinct ----------------------
def test_five_distinct_statuses():
    """The five epistemic states must be distinct members, or callers cannot tell 'unknown' from 'never measured'."""
    assert len(set(ALL)) == 5, "expected 5 distinct Status members"
    assert {s.name for s in Status} >= {"KNOWN", "UNKNOWN", "NOT_OBSERVED", "INVALID", "NOT_APPLICABLE"}


# --- Clause 2: KNOWN requires a value, others forbid it ----------------------
def test_known_with_value_is_valid():
    """A KNOWN judgment carries its value, which is the whole point of KNOWN."""
    j = Judgment(Status.KNOWN, 42)
    assert j.status is Status.KNOWN and j.value == 42 and j.reason == ""


@pytest.mark.parametrize("value", [False, 0, "", [], 0.0])
def test_known_accepts_falsy_values(value):
    """Falsy values are legitimate knowledge (e.g. 'the pit is absent' = False); only None is forbidden."""
    assert Judgment(Status.KNOWN, value).value == value, "a falsy value must be accepted for KNOWN"


def test_known_without_value_rejected():
    """KNOWN with value None is a contradiction in terms and must raise ValueError."""
    with pytest.raises(ValueError):
        Judgment(Status.KNOWN)
    with pytest.raises(ValueError):
        Judgment(Status.KNOWN, None, "forgot the value")


@pytest.mark.parametrize("status", NON_KNOWN)
@pytest.mark.parametrize("value", [1, False, 0, ""])
def test_non_known_with_value_rejected(status, value):
    """Only KNOWN may carry a value; otherwise a consumer might trust a value that is not established (even falsy ones)."""
    reason = "because" if status is Status.INVALID else ""
    with pytest.raises(ValueError):
        Judgment(status, value, reason)


@pytest.mark.parametrize("status", [Status.UNKNOWN, Status.NOT_OBSERVED, Status.NOT_APPLICABLE])
def test_non_known_without_value_valid_with_optional_reason(status):
    """UNKNOWN / NOT_OBSERVED / NOT_APPLICABLE need no value and may have an empty or a non-empty reason."""
    assert Judgment(status).value is None
    assert Judgment(status, None, "why").reason == "why"


# --- Clause 3: INVALID needs a real reason -----------------------------------
@pytest.mark.parametrize("reason", ["", "   ", "\t\n"])
def test_invalid_requires_nonblank_reason(reason):
    """INVALID without an explanation is undebuggable; blank/whitespace reasons count as missing."""
    with pytest.raises(ValueError):
        Judgment(Status.INVALID, None, reason)


def test_invalid_with_reason_valid():
    """INVALID with a real reason is the one legal shape for INVALID."""
    j = Judgment(Status.INVALID, None, "probability 1.7 > 1")
    assert j.status is Status.INVALID and j.reason == "probability 1.7 > 1"


# --- Clause 4: argument types -------------------------------------------------
@pytest.mark.parametrize("bad", ["known", None, 1, True])
def test_status_must_be_status_member(bad):
    """Strings and ints must not masquerade as Status, or typos would silently create 'valid' judgments."""
    with pytest.raises(TypeError):
        Judgment(bad, 1)


@pytest.mark.parametrize("bad", [None, 3, b"x"])
def test_reason_must_be_str(bad):
    """reason is human text; a non-str reason is a programming error (TypeError)."""
    with pytest.raises(TypeError):
        Judgment(Status.UNKNOWN, None, bad)


# --- Clause 5: immutability, equality, hashing -------------------------------
def test_frozen():
    """Judgments are shared between packages; mutation after the fact would change someone else's belief."""
    j = Judgment(Status.KNOWN, 1)
    with pytest.raises(dataclasses.FrozenInstanceError):
        j.value = 2  # type: ignore[misc]
    with pytest.raises(dataclasses.FrozenInstanceError):
        j.status = Status.UNKNOWN  # type: ignore[misc]


def test_equality_and_hash_by_fields():
    """Equal judgments must be interchangeable as dict keys / set members."""
    a, b = Judgment(Status.KNOWN, True), Judgment(Status.KNOWN, True)
    assert a == b and hash(a) == hash(b) and len({a, b}) == 1
    assert Judgment(Status.KNOWN, True) != Judgment(Status.KNOWN, False)
    assert Judgment(Status.UNKNOWN) != Judgment(Status.NOT_OBSERVED), "UNKNOWN and NOT_OBSERVED must never compare equal"
    assert Judgment(Status.UNKNOWN, None, "a") != Judgment(Status.UNKNOWN, None, "b"), "reason participates in equality"


def test_known_true_and_known_one_are_not_confused_with_unknown():
    """KNOWN(False) must differ from UNKNOWN: 'known to be false' is not 'do not know'."""
    assert Judgment(Status.KNOWN, False) != Judgment(Status.UNKNOWN)
