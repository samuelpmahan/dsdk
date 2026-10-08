"""Fixture-driven tests: the JSON in fixtures/logic/ is the language-neutral oracle shared with the JS port.

The fixtures were produced by an independent brute-force script, not by dsdk, so a disagreement here means the
implementation (or the fixture) is wrong -- never "fix" the fixture to match the code without re-deriving it by hand.
"""
import json
from pathlib import Path

import pytest

from dsdk.logic import (
    And, Const, Not, Var, countermodel, entails, evaluate, is_satisfiable, is_valid, models, size, to_str,
    truth_table, variables,
)

from helpers import decode, parse

FIXDIR = Path(__file__).resolve().parents[2] / "fixtures" / "logic"
FORMULAS = json.loads((FIXDIR / "formulas.json").read_text(encoding="utf-8"))
WUMPUS = json.loads((FIXDIR / "wumpus_kb.json").read_text(encoding="utf-8"))
CASES = FORMULAS["cases"]
IDS = [c["name"] for c in CASES]


def rows(case):
    return [(r["assignment"], r["value"]) for r in case["truth_table"]]


# ------------------------- formulas.json ------------------------------------
def test_fixture_files_are_well_formed():
    """Sanity: enough cases, unique names, every case has the promised keys (a broken fixture must fail loudly)."""
    assert len(CASES) >= 20 and len(set(IDS)) == len(IDS)
    for c in CASES:
        assert {"name", "string", "structure", "variables", "size", "truth_table", "satisfiable", "valid", "model_count"} <= set(c)


@pytest.mark.parametrize("case", CASES, ids=IDS)
def test_to_str_matches_fixture_string(case):
    """Structure -> canonical string must equal the fixture string exactly (the cross-language format contract)."""
    assert to_str(decode(case["structure"])) == case["string"]


@pytest.mark.parametrize("case", CASES, ids=IDS)
def test_reference_parser_reads_fixture_string_back(case):
    """string -> structure via the test-suite's reference parser round-trips (checks grammar and fixture agree)."""
    assert parse(case["string"]) == decode(case["structure"])


@pytest.mark.parametrize("case", CASES, ids=IDS)
def test_variables_and_size_match_fixture(case):
    """variables() and size() agree with the oracle."""
    f = decode(case["structure"])
    assert variables(f) == frozenset(case["variables"]) and size(f) == case["size"]


@pytest.mark.parametrize("case", CASES, ids=IDS)
def test_truth_table_matches_fixture_including_order(case):
    """Same rows, same values, same ORDER as the oracle."""
    assert truth_table(decode(case["structure"])) == rows(case)


@pytest.mark.parametrize("case", CASES, ids=IDS)
def test_evaluate_matches_every_fixture_row(case):
    """Two-valued evaluate reproduces every oracle row."""
    f = decode(case["structure"])
    for assignment, value in rows(case):
        assert evaluate(f, assignment) is value, f"{case['string']} under {assignment}"


@pytest.mark.parametrize("case", CASES, ids=IDS)
def test_models_count_and_flags_match_fixture(case):
    """models / is_satisfiable / is_valid agree with the oracle; models are exactly the True rows, in order."""
    f = decode(case["structure"])
    ms = list(models(f))
    assert ms == [a for a, v in rows(case) if v]
    assert len(ms) == case["model_count"]
    assert is_satisfiable(f) is case["satisfiable"] and is_valid(f) is case["valid"]


@pytest.mark.parametrize("name", FORMULAS["invalid_var_names"])
def test_invalid_var_names_from_fixture_are_rejected(name):
    """The shared list of illegal names (JS port must reject the same ones)."""
    with pytest.raises(ValueError):
        Var(name)


# ------------------------- wumpus_kb.json -----------------------------------
PREMISES = WUMPUS["premises"]
QUERIES = WUMPUS["queries"]


def premises():
    return [decode(p["structure"]) for p in PREMISES]


def test_wumpus_fixture_strings_match_structures():
    """Every premise and query string equals to_str of its structure."""
    for item in PREMISES + QUERIES:
        assert to_str(decode(item["structure"])) == item["string"], item["name"]


def test_wumpus_kb_has_exactly_the_hand_derived_models():
    """The KB has 3 models: no pit at P11/P12/P21, breeze at B21 forces (P22 or P31). A3 weights these models."""
    assert WUMPUS["model_count"] == 3 and len(WUMPUS["models"]) == 3
    from functools import reduce
    kb = reduce(And, premises())
    assert list(models(kb, over=WUMPUS["variables"])) == WUMPUS["models"]


@pytest.mark.parametrize("q", QUERIES, ids=[q["name"] for q in QUERIES])
def test_wumpus_entailments(q):
    """KB |= query (or not) exactly as the oracle says, e.g. KB |= ~P12, KB |= ~P21, KB !|= P22, KB !|= ~P22."""
    assert entails(premises(), decode(q["structure"])) is q["entails"], f"KB |= {q['string']} should be {q['entails']}"


@pytest.mark.parametrize("q", QUERIES, ids=[q["name"] for q in QUERIES])
def test_wumpus_first_countermodel(q):
    """countermodel returns the oracle's FIRST countermodel (or None when entailed)."""
    assert countermodel(premises(), decode(q["structure"])) == q["first_countermodel"]


def test_wumpus_headline_facts_spelled_out():
    """The four facts the planner asked for, independent of the JSON: ~P12 yes, ~P21 yes, P22 no, ~P22 no."""
    kb = premises()
    p12, p21, p22 = Var("P12"), Var("P21"), Var("P22")
    assert entails(kb, Not(p12)) and entails(kb, Not(p21))
    assert not entails(kb, p22) and not entails(kb, Not(p22))
