"""The Wumpus oracle: dsdk.prob must reproduce embodiedwumpusworld/src/priors.js (branch lab/wumpus-core) and weight the three
models of fixtures/logic/wumpus_kb.json.

Headline numbers (two neighbours A, B, independent pit prior p, a perfect breeze observed):
  p = 0.2 -> posterior A-only 4/9, B-only 4/9, both 1/9; P(pit at A | breeze) = 5/9 = 55.56 %
  p = 0.5 -> posterior 1/3, 1/3, 1/3;                    P(pit at A | breeze) = 2/3 = 66.67 %
In closed form P(A | breeze) = 1 / (2 - p).
"""
import json
import shutil
import subprocess
from fractions import Fraction
from pathlib import Path

import pytest

from dsdk import logic
from dsdk.core import Status
from dsdk.logic import And, Iff, Not, Or, Var
from dsdk.prob import condition, marginals, normalise, prior_belief, probability

from prob_helpers import Fr

ROOT = Path(__file__).resolve().parents[2]
ORACLE = json.loads((ROOT / "fixtures" / "prob" / "wumpus_priors.json").read_text())
KB = json.loads((ROOT / "fixtures" / "logic" / "wumpus_kb.json").read_text())
JS_PRIORS = Path("/home/user/samuelpmahan/embodiedwumpusworld/src/priors.js")

A, B = Var("A"), Var("B")
BREEZE = Or(A, B)
LABELS = {("A", False, "B", False): "Neither", ("A", True, "B", False): "A only", ("A", False, "B", True): "B only", ("A", True, "B", True): "Both"}


def posterior_for(p):
    prior = prior_belief({"A": p, "B": p})
    post = normalise(condition(prior, BREEZE))
    assert post.status is Status.KNOWN
    return prior, post.value


def labelled(belief):
    return {LABELS[tuple(x for pair in w.values for x in pair)]: w.weight for w in belief.worlds}


def formula_from_json(node):
    op = node["op"]
    if op == "var":
        return Var(node["name"])
    if op == "not":
        return Not(formula_from_json(node["operand"]))
    cls = {"and": And, "or": Or, "iff": Iff, "implies": logic.Implies}[op]
    return cls(formula_from_json(node["left"]), formula_from_json(node["right"]))


def kb_belief(p):
    pit_cells = [v for v in KB["variables"] if v.startswith("P")]
    constraint = None
    for prem in KB["premises"]:
        f = formula_from_json(prem["structure"])
        constraint = f if constraint is None else And(constraint, f)
    return prior_belief({c: p for c in pit_cells}, constraint)


# ==== The Wumpus breeze experiment reproduces 4/9, 4/9, 1/9 and 55.56% to 66.67% ====
def test_headline_posterior_is_4_9_4_9_1_9():
    """With prior 0.2 and a breeze, the posterior is A-only 4/9, B-only 4/9, both 1/9 and neither 0, summing to 1."""
    prior, post = posterior_for(0.2)
    assert labelled(post) == {"Neither": 0, "A only": Fr(4, 9), "B only": Fr(4, 9), "Both": Fr(1, 9)}
    assert sum(labelled(post).values()) == 1


def test_prior_hypotheses_are_the_four_independent_cases():
    """JS 'hypotheses' (before the breeze): Neither (1-p)^2, A only p(1-p), B only p(1-p), Both p^2."""
    prior, _ = posterior_for(0.2)
    assert labelled(prior) == {"Neither": Fr(16, 25), "A only": Fr(4, 25), "B only": Fr(4, 25), "Both": Fr(1, 25)}


def test_marginal_at_A_moves_from_55_56_to_66_67_percent_when_prior_goes_to_half():
    """P(pit at A | breeze) is exactly 5/9 (55.56%) at prior 0.2 and 2/3 (66.67%) at prior 0.5, so it rises with the prior."""
    _, low = posterior_for(0.2)
    _, high = posterior_for(0.5)
    pa_low, pa_high = probability(low, A).value, probability(high, A).value
    assert (pa_low, pa_high) == (Fr(5, 9), Fr(2, 3))
    assert f"{float(pa_low) * 100:.2f}" == "55.56" and f"{float(pa_high) * 100:.2f}" == "66.67"
    assert pa_low < pa_high


def test_at_prior_half_all_three_possible_cases_are_equally_likely():
    """At prior 0.5 the three cases that survive the breeze each have posterior 1/3."""
    _, post = posterior_for(0.5)
    assert labelled(post) == {"Neither": 0, "A only": Fr(1, 3), "B only": Fr(1, 3), "Both": Fr(1, 3)}


@pytest.mark.parametrize("p", [Fr(1, 20), Fr(1, 10), Fr(1, 5), Fr(1, 4), Fr(3, 10), Fr(1, 2), Fr(3, 4), Fr(9, 10), Fr(1)])
def test_closed_form_probability_of_A_is_one_over_two_minus_p(p):
    """P(A | breeze) = (p(1-p) + p^2) / (1 - (1-p)^2) = p / (2p - p^2) = 1 / (2 - p), exactly."""
    prior = prior_belief({"A": p, "B": p})
    assert probability(prior, A, BREEZE).value == 1 / (2 - p)


def test_posterior_probability_of_A_is_increasing_in_the_prior():
    """The slider in the Lab: a higher pit prior makes a pit at A more likely given the same breeze."""
    ps = [Fr(i, 20) for i in range(1, 20)]
    values = [probability(prior_belief({"A": p, "B": p}), A, BREEZE).value for p in ps]
    assert values == sorted(values) and len(set(values)) == len(values)


# ==== Agreement with the numbers produced by the JavaScript oracle ====
@pytest.mark.parametrize("case", ORACLE["cases"], ids=lambda c: str(c["prior"]))
def test_every_js_oracle_case_agrees_exactly_and_in_floats(case):
    """For each prior in the fixture generated from the JavaScript priors.js, the prior weights, posterior weights and P(A) agree with the JavaScript floats to 1e-12, and the float prior converts to the exact fraction in the fixture."""
    p = Fraction(case["prior_exact"])
    assert float(p) == case["prior"]
    prior, post = posterior_for(case["prior"])  # the float prior goes through the repr rule
    assert prior_belief({"A": case["prior"], "B": case["prior"]}) == prior_belief({"A": p, "B": p})
    for label, weight in labelled(post).items():
        assert float(weight) == pytest.approx(case["js_posterior"][label], abs=1e-12), label
    for label, weight in labelled(prior).items():
        assert float(weight) == pytest.approx(case["js_prior_weights"][label], abs=1e-12), label
    assert float(probability(post, A).value) == pytest.approx(case["js_probability_A"], abs=1e-12)


def test_js_fixture_has_the_headline_values():
    """The JavaScript fixture itself holds 0.5555555555555556 and 0.6666666666666666 for the two headline priors."""
    by_prior = {c["prior"]: c for c in ORACLE["cases"]}
    assert by_prior[0.2]["js_probability_A"] == pytest.approx(0.5555555555555556)
    assert by_prior[0.5]["js_probability_A"] == pytest.approx(0.6666666666666666)


def test_prior_zero_js_throws_and_dsdk_answers_invalid():
    """JS: 'conditionWeights requires a positive finite total weight' (RangeError). dsdk: a flagged INVALID Judgment, not an exception and not a number."""
    assert "RangeError" in ORACLE["zero_prior"]["js_error"]
    prior = prior_belief({"A": 0, "B": 0})
    j = probability(prior, A, BREEZE)
    assert j.status is Status.INVALID and j.value is None and "probability zero" in j.reason
    assert normalise(condition(prior, BREEZE)).status is Status.INVALID


def test_prior_one_means_both_pits_for_certain():
    """With prior 1 the posterior puts all weight on both pits."""
    prior = prior_belief({"A": 1, "B": 1})
    post = normalise(condition(prior, BREEZE)).value
    assert labelled(post) == {"Neither": 0, "A only": 0, "B only": 0, "Both": 1}


@pytest.mark.skipif(shutil.which("node") is None or not JS_PRIORS.exists(), reason="node or the embodiedwumpusworld checkout is not available")
def test_live_parity_with_the_js_oracle_for_priors_the_fixture_never_saw():
    """Run the real priors.js for new priors and compare. Skipped on machines without node or the checkout."""
    script = (
        "import('%s').then(m=>{const out=[];for(const p of [0.07,0.42,0.66]){const r=m.breezeExperiment(p);"
        "out.push([p,r.probabilityA,r.posterior.map(h=>h.weight)])}console.log(JSON.stringify(out))})" % JS_PRIORS.as_posix()
    )
    out = subprocess.run(["node", "-e", script], capture_output=True, text=True, timeout=60, check=True).stdout
    for p, js_a, js_weights in json.loads(out):
        prior, post = posterior_for(p)
        assert float(probability(post, A).value) == pytest.approx(js_a, abs=1e-12)
        got = [float(w.weight) for w in post.worlds]  # Neither, B only, A only, Both -> JS order is Neither, A only, B only, Both
        assert got == pytest.approx([js_weights[0], js_weights[2], js_weights[1], js_weights[3]], abs=1e-12)


# ==== Weighting the three models of the Wumpus knowledge base ====
def test_kb_models_are_exactly_the_fixtures_three_models_in_order():
    """Weighting the Wumpus knowledge base gives exactly its three models, in the fixture's order."""
    belief = kb_belief(0.2)
    assert len(belief.worlds) == KB["model_count"] == 3
    assert [w.assignment() for w in belief.worlds] == KB["models"]


def test_kb_model_weights_at_prior_one_fifth_are_4_9_4_9_1_9():
    """Weight of a model = p^(pits) (1-p)^(non-pits) over the pit cells. P11, P12, P21 are false in all three models (factor (4/5)^3);
    P22/P31 give 4/25, 4/25, 1/25 -- exactly the breeze experiment's proportions."""
    belief = kb_belief(0.2)
    q = Fr(4, 5) ** 3
    assert [w.weight for w in belief.worlds] == [q * Fr(4, 25), q * Fr(4, 25), q * Fr(1, 25)]
    post = normalise(belief).value
    assert [w.weight for w in post.worlds] == [Fr(4, 9), Fr(4, 9), Fr(1, 9)]


def test_kb_posterior_at_prior_half_is_uniform_over_the_three_models():
    """At prior 0.5 the three models of the knowledge base each have posterior 1/3."""
    post = normalise(kb_belief(0.5)).value
    assert [w.weight for w in post.worlds] == [Fr(1, 3)] * 3


@pytest.mark.parametrize("p", [Fr(1, 10), Fr(1, 5), Fr(1, 2), Fr(7, 10)])
def test_kb_pit_probabilities_follow_the_models(p):
    """P(P22) = P(P31) = (p(1-p) + p^2)/(2p - p^2) = 1/(2-p); known-safe cells have probability exactly 0."""
    m = marginals(kb_belief(p))
    assert m.status is Status.KNOWN
    assert m.value["P22"] == m.value["P31"] == 1 / (2 - p)
    assert m.value["P11"] == m.value["P12"] == m.value["P21"] == 0
    assert m.value["B21"] == 1 and m.value["B11"] == 0, "percepts are forced by the KB"


def test_kb_probabilities_agree_with_logical_entailment():
    """Entailed -> probability exactly 1 or 0; not entailed -> strictly between. The fixture's own query list is the oracle."""
    belief = kb_belief(0.2)
    for q in KB["queries"]:
        f = formula_from_json(q["structure"])
        pr = probability(belief, f)
        assert pr.status is Status.KNOWN, q["name"]
        if q["entails"]:
            assert pr.value == 1, q["name"]
        else:
            assert pr.value < 1, q["name"]
        negation = probability(belief, Not(f)).value
        assert negation == 1 - pr.value


def test_kb_cells_that_are_not_entailed_either_way_are_strictly_uncertain():
    """Cells P22 and P31 have probability strictly between 0 and 1 and the logic package confirms the knowledge base entails neither them nor their negations."""
    belief = kb_belief(0.2)
    for cell in ("P22", "P31"):
        assert 0 < probability(belief, Var(cell)).value < 1
        assert not logic.entails([formula_from_json(p["structure"]) for p in KB["premises"]], Var(cell))
        assert not logic.entails([formula_from_json(p["structure"]) for p in KB["premises"]], Not(Var(cell)))


@pytest.mark.parametrize("p", [0, 1])
def test_degenerate_kb_priors_make_the_percepts_impossible_so_everything_is_invalid(p):
    """prior 0: no pits anywhere contradicts the observed breeze; prior 1: P11 is certainly a pit but the KB says ~P11. Both give
    total weight 0, so every query is INVALID -- the agent must not 'conclude' anything from an impossible world."""
    belief = kb_belief(p)
    assert belief.total == 0
    for cell in ("P22", "P31"):
        j = probability(belief, Var(cell))
        assert j.status is Status.INVALID
