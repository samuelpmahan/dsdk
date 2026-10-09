"""Integration tests: probability questions written as text flow through the whole stack.

Every test here runs at least two layers together on REAL output of the lower layer, never on hand-made stand-ins:
  text -> dsdk.lang.parse_formula (relaxed syntax) -> dsdk.logic Formula -> dsdk.prob exact answer (-> dsdk.core Judgment),
and where noted also dsdk.graph (Bayes-net DAGs, lineage of belief updates) and dsdk.core (ticks and receipts).
The independent expectations are hand-computed fractions (the Wumpus 4/9, 4/9, 1/9 numbers, the textbook sprinkler values) or the answer
obtained by building the logic formula by hand and calling the probability function directly.
"""
import json
from fractions import Fraction
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from dsdk.core import PxC, Status
from dsdk.graph import Graph, lineage_graph, reachable
from dsdk.lang import ParseError, parse_formula
from dsdk.logic import And, Const, Iff, Implies, Not, Or, Var, to_str
from dsdk.prob import (
    ask, ask_net, bayes_net, belief_history, compare_text, current_belief, observe_text, parse_text, prior_belief, probability,
    start_series,
)

ROOT = Path(__file__).resolve().parents[2]
KB = json.loads((ROOT / "fixtures" / "logic" / "wumpus_kb.json").read_text())
Fr = Fraction
A, B, C = Var("A"), Var("B"), Var("C")


def known(j):
    assert j.status is Status.KNOWN, j
    return j.value


def kb_belief(p):
    """The Wumpus knowledge base, built from the fixture's STRING premises with the language package's strict parser."""
    constraint = None
    for prem in KB["premises"]:
        f = parse_formula(prem["string"])
        constraint = f if constraint is None else And(constraint, f)
    return prior_belief({v: p for v in KB["variables"] if v.startswith("P")}, constraint)


# ==== Questions written as text give the Wumpus numbers ====
def test_the_headline_question_as_text_gives_five_ninths():
    """Asking "A" given "A | B" on the 0.2 pit prior returns exactly 5/9 (55.56%), the number the JavaScript oracle prints."""
    assert known(ask(prior_belief({"A": 0.2, "B": 0.2}), "A", "A | B")) == Fr(5, 9)


def test_the_same_question_at_prior_half_gives_two_thirds():
    """At prior 0.5 the text question "A" given "A | B" gives exactly 2/3 (66.67%)."""
    assert known(ask(prior_belief({"A": 0.5, "B": 0.5}), "A", "A | B")) == Fr(2, 3)


def test_a_text_question_equals_building_the_logic_formula_by_hand():
    """Whatever the text says, the answer equals calling the probability function on the hand-built logic formulas, so the parser adds no semantics of its own."""
    b = prior_belief({"A": Fr(1, 3), "B": Fr(1, 2), "C": Fr(1, 5)})
    cases = [("A & ~B", None, And(A, Not(B)), None), ("A -> B", "C", Implies(A, B), C), ("A <-> B", "~C | A", Iff(A, B), Or(Not(C), A))]
    for qt, gt, q, g in cases:
        assert ask(b, qt, gt) == probability(b, q, g)


def test_the_knowledge_base_from_fixture_strings_matches_the_fixtures_three_models():
    """Parsing the fixture's premise strings with the strict parser and weighting them gives the fixture's three models in order."""
    belief = kb_belief(0.2)
    assert [w.assignment() for w in belief.worlds] == KB["models"]


def test_user_style_questions_about_the_knowledge_base():
    """The questions from the design brief work as typed: "P22 | P31" is certain, "B21 & ~B11" is certain, "P22" is 5/9 at prior 0.2."""
    b = kb_belief(0.2)
    assert known(ask(b, "P22 | P31")) == 1
    assert known(ask(b, "B21 & ~B11")) == 1
    assert known(ask(b, "P22")) == Fr(5, 9)
    assert known(ask(b, "P22", "B21 & ~B11")) == Fr(5, 9)
    assert known(ask(b, "~P12 & ~P21")) == 1


def test_every_query_in_the_knowledge_base_fixture_agrees_with_its_logical_verdict():
    """For each fixture query string: entailed means probability exactly 1 and not entailed means below 1 (strict parser output, exact weights)."""
    b = kb_belief(0.2)
    for q in KB["queries"]:
        p = known(ask(b, q["string"]))
        assert (p == 1) == q["entails"], q["name"]


def test_degenerate_prior_makes_every_text_question_invalid_not_certain():
    """With pit prior 0 the observed breeze is impossible, so even the question "true" is INVALID with a zero-weight reason, not 1."""
    j = ask(kb_belief(0), "true")
    assert j.status is Status.INVALID and "zero total weight" in j.reason


# ==== Precedence and associativity of the text reach the numbers ====
def test_and_binds_tighter_than_or_in_the_probability():
    """"A | B & C" means A | (B & C): on a belief where the two readings differ the answer is the first reading's, not (A | B) & C."""
    b = prior_belief({"A": Fr(1, 2), "B": Fr(1, 2), "C": Fr(1, 4)})
    first = known(probability(b, Or(A, And(B, C))))
    second = known(probability(b, And(Or(A, B), C)))
    assert first != second
    assert known(ask(b, "A | B & C")) == first
    assert known(ask(b, "(A | B) & C")) == second


def test_implication_is_right_associative_in_the_probability():
    """"A -> B -> C" means A -> (B -> C); the left reading has a different probability here."""
    b = prior_belief({"A": Fr(1, 2), "B": Fr(1, 3), "C": Fr(1, 5)})
    right, left = Implies(A, Implies(B, C)), Implies(Implies(A, B), C)
    assert known(probability(b, right)) != known(probability(b, left))
    assert known(ask(b, "A -> B -> C")) == known(probability(b, right))


def test_not_binds_tightest_and_double_negation_cancels():
    """"~A & B" is (not A) and B, "~~A" is A, and the numbers show it."""
    b = prior_belief({"A": Fr(1, 4), "B": Fr(1, 3)})
    assert known(ask(b, "~A & B")) == Fr(3, 4) * Fr(1, 3)
    assert known(ask(b, "~~A")) == Fr(1, 4)


def test_constants_and_redundant_parentheses_and_whitespace():
    """"true" and "false" are constants, extra parentheses and spaces change nothing."""
    b = prior_belief({"A": Fr(1, 4)})
    assert known(ask(b, "true")) == 1 and known(ask(b, "false")) == 0
    assert known(ask(b, "  ( ( A ) )  ")) == Fr(1, 4)


def test_a_variable_named_like_a_constant_prefix_is_a_variable():
    """"trueish" is a variable name, not the constant true followed by junk, so asking about it on a belief without that variable is UNKNOWN."""
    j = ask(prior_belief({"A": Fr(1, 2)}), "trueish")
    assert j.status is Status.UNKNOWN and "trueish" in j.reason


# ==== Text that cannot be parsed is INVALID with the offset ====
@pytest.mark.parametrize(
    "text,offset",
    [("A &", 3), ("", 0), ("A B", 2), ("(A | B", 6), ("A | | B", 4), ("A @ B", 2), ("~", 1), ("A -> ", 5)],
)
def test_unparseable_query_text_is_invalid_and_names_the_offset(text, offset):
    """Bad query text gives INVALID (never a guessed number) and the reason says "unparseable query text" and ends the message with "(at offset N)" where N is the first bad position."""
    j = ask(prior_belief({"A": Fr(1, 2), "B": Fr(1, 2)}), text)
    assert j.status is Status.INVALID and j.value is None
    assert j.reason.startswith("unparseable query text: ")
    assert f"(at offset {offset})" in j.reason


def test_the_reason_lists_what_the_parser_expected():
    """A parse error carries the parser's expected-token set, sorted, so the user can see what would have been accepted; a lexical error has none."""
    j = ask(prior_belief({"A": Fr(1, 2)}), "A &")
    assert j.reason.endswith("; expected one of: FALSE, LPAREN, NAME, TILDE, TRUE")
    lex = ask(prior_belief({"A": Fr(1, 2)}), "A @ B")
    assert "expected one of" not in lex.reason


def test_the_reason_matches_what_the_language_package_itself_reports():
    """The offset in the reason is the offset of the ParseError that parse_formula raises for the same text."""
    with pytest.raises(ParseError) as info:
        parse_formula("A | | B", relaxed=True)
    j = ask(prior_belief({"A": Fr(1, 2), "B": Fr(1, 2)}), "A | | B")
    assert f"(at offset {info.value.offset})" in j.reason and sorted(info.value.expected)[0] in j.reason


def test_unparseable_evidence_text_is_labelled_as_evidence():
    """A good query with bad evidence text is INVALID with the role "evidence text"."""
    j = ask(prior_belief({"A": Fr(1, 2), "B": Fr(1, 2)}), "A", "B &")
    assert j.status is Status.INVALID and j.reason.startswith("unparseable evidence text: ") and "(at offset 3)" in j.reason


def test_the_query_text_is_reported_first_when_both_are_bad():
    """When both texts are bad the reason is about the query text."""
    j = ask(prior_belief({"A": Fr(1, 2)}), "&", "&")
    assert j.reason.startswith("unparseable query text: ")


def test_whitespace_only_text_is_a_parse_error_at_its_length():
    """A text of three spaces is unparseable at offset 3."""
    j = ask(prior_belief({"A": Fr(1, 2)}), "   ")
    assert j.status is Status.INVALID and "(at offset 3)" in j.reason


def test_parse_text_returns_the_formula_or_the_invalid_judgment():
    """parse_text is the single place where text becomes a formula: KNOWN with the logic Formula that parse_formula returns, or the INVALID reason."""
    assert known(parse_text("A & ~B")) == And(A, Not(B))
    assert parse_text("A &").status is Status.INVALID
    assert parse_text("A &", "evidence text").reason.startswith("unparseable evidence text: ")


def test_parse_failure_is_distinguishable_from_impossible_evidence():
    """Impossible evidence is INVALID too, but its reason says "probability zero" and does not start with "unparseable"; a parse failure is the opposite."""
    b = prior_belief({"A": Fr(1, 2)})
    impossible = ask(b, "A", "A & ~A")
    broken = ask(b, "A", "A &")
    assert impossible.status is broken.status is Status.INVALID
    assert "probability zero" in impossible.reason and not impossible.reason.startswith("unparseable")
    assert broken.reason.startswith("unparseable") and "probability zero" not in broken.reason


def test_unmodelled_variable_in_text_is_unknown():
    """A well-formed question about a variable the belief does not model is UNKNOWN, with the names sorted, not INVALID."""
    j = ask(prior_belief({"A": Fr(1, 2)}), "Z | Y")
    assert j.status is Status.UNKNOWN and j.reason == "unmodelled variables: Y, Z"


@pytest.mark.parametrize("args", [(5, "A"), ("belief", "A")])
def test_non_belief_or_non_text_is_a_type_error(args):
    """A non-belief, a non-string query or a non-string evidence is a Python TypeError, not a Judgment (only text problems are Judgments)."""
    b = prior_belief({"A": Fr(1, 2)})
    with pytest.raises(TypeError):
        ask(*args)
    with pytest.raises(TypeError):
        ask(b, 5)
    with pytest.raises(TypeError):
        ask(b, "A", 5)


# ==== Round trips through to_str and random text ====
def formulas():
    leaf = st.sampled_from(["A", "B", "C"]).map(Var) | st.booleans().map(Const)
    return st.recursive(leaf, lambda c: c.map(Not) | st.builds(And, c, c) | st.builds(Or, c, c) | st.builds(Implies, c, c) | st.builds(Iff, c, c), max_leaves=6)


@settings(max_examples=80)
@given(formulas(), formulas())
def test_the_canonical_text_of_any_formula_gets_the_same_answer_as_the_formula(f, g):
    """For random formulas, asking with the logic package's canonical string (to_str) equals asking the probability function with the formula itself, for both query and evidence, including INVALID verdicts."""
    b = prior_belief({"A": Fr(1, 3), "B": Fr(1, 2), "C": Fr(3, 4)})
    assert ask(b, to_str(f), to_str(g)) == probability(b, f, g)


# ==== Bayes nets: graph DAG + joint + text ====
SPRINKLER_EDGES = [("Cloudy", "Sprinkler"), ("Cloudy", "Rain"), ("Sprinkler", "WetGrass"), ("Rain", "WetGrass")]
SPRINKLER_CPTS = {
    "Cloudy": {(): Fr(1, 2)},
    "Sprinkler": {(True,): Fr(1, 10), (False,): Fr(1, 2)},
    "Rain": {(True,): Fr(8, 10), (False,): Fr(2, 10)},
    "WetGrass": {(True, True): Fr(99, 100), (True, False): Fr(9, 10), (False, True): Fr(9, 10), (False, False): Fr(0)},
}


def sprinkler():
    return bayes_net(Graph.from_edges(SPRINKLER_EDGES, ["Cloudy", "Sprinkler", "Rain", "WetGrass"]), SPRINKLER_CPTS)


def test_text_questions_on_the_sprinkler_network_give_the_textbook_values():
    """On the graph-DAG sprinkler net, "Rain" given "WetGrass" is about 0.708 and given "WetGrass & Sprinkler" about 0.320, so the sprinkler explains the rain away."""
    net = sprinkler()
    rain_wet = known(ask_net(net, "Rain", "WetGrass"))
    rain_both = known(ask_net(net, "Rain", "WetGrass & Sprinkler"))
    assert float(rain_wet) == pytest.approx(0.708, abs=5e-4) and float(rain_both) == pytest.approx(0.320, abs=5e-4)
    assert rain_both < rain_wet


def test_net_text_answers_equal_the_hand_built_formula_answers():
    """The text answer on the net equals probability() on the joint with hand-built formulas, so graph, logic and probability agree."""
    from dsdk.prob import joint_belief

    net = sprinkler()
    j = joint_belief(net)
    q, g = Or(Var("Rain"), Var("Sprinkler")), And(Var("WetGrass"), Not(Var("Cloudy")))
    assert ask_net(net, "Rain | Sprinkler", "WetGrass & ~Cloudy") == probability(j, q, g)


def test_net_questions_with_bad_text_or_unknown_node_or_impossible_evidence():
    """Bad text is INVALID with the offset, an unknown node name is UNKNOWN, and evidence that contradicts itself is INVALID with "probability zero"."""
    net = sprinkler()
    assert "(at offset 6)" in ask_net(net, "Rain &", "WetGrass").reason
    assert ask_net(net, "Hail").status is Status.UNKNOWN
    assert "probability zero" in ask_net(net, "Rain", "Rain & ~Rain").reason


def test_a_net_too_large_to_enumerate_is_reported_as_invalid_after_parsing():
    """A network with more nodes than the supported maximum answers INVALID ("cannot enumerate"), but a parse error is reported first."""
    nodes = [f"n{i:02d}" for i in range(17)]
    net = bayes_net(Graph.from_edges([], nodes), {n: {(): Fr(1, 2)} for n in nodes})
    assert ask_net(net, "n00").reason.startswith("cannot enumerate")
    assert ask_net(net, "n00 &").reason.startswith("unparseable")


def test_ask_net_rejects_a_non_net():
    """Anything but a Bayes net is a TypeError."""
    with pytest.raises(TypeError):
        ask_net("net", "A")


# ==== Sampling and belief updates driven by text ====
def test_compare_text_puts_the_exact_value_next_to_a_seeded_estimate():
    """compare_text("A", "A | B") on the Wumpus prior returns the exact 5/9 and a seeded estimate within four standard errors of it."""
    c = known(compare_text(prior_belief({"A": 0.2, "B": 0.2}), "A", 20000, 7, "A | B"))
    assert c.exact == Fr(5, 9) and c.error < 4 * c.estimate.stderr and c.covered


def test_compare_text_reports_parse_errors_and_exact_invalid_before_sampling():
    """Unparseable text is INVALID with the offset, and impossible evidence stays INVALID (exact wins over the sampler's UNKNOWN)."""
    b = prior_belief({"A": 0.2, "B": 0.2})
    assert compare_text(b, "A &", 10, 1).reason.startswith("unparseable query text")
    j = compare_text(b, "A", 500, 1, "A & ~A")
    assert j.status is Status.INVALID and "probability zero" in j.reason


def test_observing_text_records_the_parsed_formula_with_lineage():
    """observe_text("A | B") binds the parsed Or(A, B) as the evidence Part, leaves a belief whose P(A) is 5/9, and the lineage graph reaches the new belief from the start."""
    store = PxC()
    start = start_series(store, "s", prior_belief({"A": 0.2, "B": 0.2}))
    new = known(observe_text(store, "s", "A | B"))
    assert store.get("px.s.evidence.1").value == Or(A, B)
    assert known(probability(new.value, A)) == Fr(5, 9)
    assert known(reachable(lineage_graph(new), start, new)) is True
    assert belief_history(store, "s")[-1] is new


def test_observing_text_that_does_not_parse_leaves_the_store_untouched():
    """Unparseable evidence is INVALID with the offset and adds no Part and no receipt."""
    store = PxC()
    start_series(store, "s", prior_belief({"A": 0.2, "B": 0.2}))
    before = (store.entries(), store.receipts())
    j = observe_text(store, "s", "A |")
    assert j.status is Status.INVALID and j.reason.startswith("unparseable evidence text") and "(at offset 3)" in j.reason
    assert (store.entries(), store.receipts()) == before


def test_observing_impossible_text_is_rejected_by_the_belief_not_the_parser():
    """A well-formed but impossible observation ("A & ~A") parses, then the series refuses it as INVALID with "impossible" and the store is untouched."""
    store = PxC()
    start_series(store, "s", prior_belief({"A": 0.2, "B": 0.2}))
    before = (store.entries(), store.receipts())
    j = observe_text(store, "s", "A & ~A")
    assert j.status is Status.INVALID and "impossible" in j.reason and not j.reason.startswith("unparseable")
    assert (store.entries(), store.receipts()) == before


def test_a_sequence_of_text_observations_equals_one_text_question_on_the_conjunction():
    """Observing "A | B" then "~A" gives the same P(B) as asking "B" given "(A | B) & ~A" directly on the prior (exactly 1)."""
    prior = prior_belief({"A": 0.2, "B": 0.2})
    store = PxC()
    start_series(store, "s", prior)
    observe_text(store, "s", "A | B")
    observe_text(store, "s", "~A")
    assert known(probability(current_belief(store, "s").value, B)) == known(ask(prior, "B", "(A | B) & ~A")) == 1


def test_observe_text_type_error_comes_before_anything_else():
    """A non-string observation is a TypeError."""
    store = PxC()
    start_series(store, "s", prior_belief({"A": 0.5}))
    with pytest.raises(TypeError):
        observe_text(store, "s", 5)
