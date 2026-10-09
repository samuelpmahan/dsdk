"""The Wumpus world for the Lab's Logic Cave: caves identical to the page's, the logic-only agent, and the probability rung that answers
(with dsdk.prob) when the logic-only agent has nothing provably safe left.

Hand derivations used below (pit prior 1/5, so a pit-free square weighs 4/5):
* Visited (1,1) only, with a breeze: the frontier is (1,2), (2,1) and the evidence is "P12 | P21". The three worlds P12 only, P21 only, both weigh
  4/25, 4/25, 1/25 (total 9/25), so P(P12) = (4/25 + 1/25) / (9/25) = 5/9 and the expected number of pits is 5/9 + 5/9 = 10/9.
* Visited (1,1), (1,2), (2,1) with breezes at the last two and none at (1,1): the frontier is (1,3), (2,2), (3,1) and the evidence is
  "(P13 | P22) & (P22 | P31)". P22 true: weight 1/5 whatever the others are. P22 false needs P13 and P31: (4/5)(1/5)(1/5) = 4/125.
  Total 25/125 + 4/125 = 29/125, so P(P22) = 25/29 and P(P13) = P(P31) = (5/125 + 4/125) / (29/125) = 9/29; expected pits 43/29.
* Visited (1,1) only, with a stench: the Wumpus is on (1,2) or (2,1), equally likely, so each has probability 1/2.
"""
import ast
import inspect
import json
from fractions import Fraction as F
from itertools import product
from pathlib import Path

import pytest

from dsdk.core import Status
from dsdk.worlds import wumpus
from dsdk.worlds.wumpus import (
    PIT_PRIOR, Cave, Percept, demo_cave, frontier, knowledge, lab_data, mulberry32, neighbours, percept, provably_safe, run_agent,
    seeded_cave, state_key, stuck_risk, sweep_rates,
)

NONE = Percept(False, False, False)
BREEZE = Percept(True, False, False)
STENCH = Percept(False, True, False)
DEMO_STUCK = {(1, 1): NONE, (1, 2): BREEZE, (2, 1): BREEZE}


# ==== The generator and the caves are identical to the page's (values taken from the page's own JavaScript run in Node) ====


def test_the_random_stream_matches_the_pages_mulberry32_to_ten_decimals():
    """The Python random stream gives the same first three numbers as the page's JavaScript for seeds 1, 7 and 300 (0.6270739406, 0.0027357212, 0.5274470400 for seed 1), so a cave means the same thing in both."""
    want = {1: (0.6270739406, 0.0027357212, 0.5274470400), 7: (0.0117047532, 0.0619582576, 0.9769076328), 300: (0.8090277314, 0.0044199354, 0.7696573723)}
    for seed, values in want.items():
        rng = mulberry32(seed)
        assert tuple(round(rng(), 10) for _ in range(3)) == values


def test_the_demo_cave_is_the_fixture_cave():
    """The demo cave has pits at (3,1), (1,3) and (3,4), the Wumpus at (4,4) and the gold at (3,3), as in EmbodiedWumpusWorld's demo."""
    c = demo_cave()
    assert (c.pits, c.wumpus, c.gold) == (frozenset({(3, 1), (1, 3), (3, 4)}), (4, 4), (3, 3))


def test_seeded_caves_match_the_pages_generator():
    """Seeded caves for seeds 1, 2, 3, 7 and 300 have exactly the pits, Wumpus and gold that the page's JavaScript generator produces (a pit may share a square with the Wumpus or gold)."""
    want = {1: ({(3, 1), (2, 4)}, (4, 1), (1, 3)), 2: ({(3, 3)}, (4, 1), (4, 3)), 3: ({(3, 1), (1, 2), (1, 3), (4, 3), (1, 4)}, (3, 4), (2, 2)),
            7: ({(2, 1), (3, 1), (1, 4), (4, 4)}, (3, 2), (2, 2)), 300: ({(3, 1), (2, 2), (3, 3), (2, 4)}, (3, 2), (3, 2))}
    for seed, (pits, wumpus_cell, gold) in want.items():
        c = seeded_cave(seed)
        assert (set(c.pits), c.wumpus, c.gold) == (pits, wumpus_cell, gold), seed
        assert isinstance(c.pits, frozenset) and (1, 1) not in c.pits and c.wumpus != (1, 1) and c.gold != (1, 1)
    assert seeded_cave(300).name == "Random cave #300" and demo_cave().name == "Demo cave"


def test_neighbours_are_the_orthogonal_squares_inside_the_cave_in_sorted_order():
    """The neighbours of a corner have two squares, of an edge three, of the middle four, always sorted by (x, y)."""
    assert neighbours((1, 1)) == ((1, 2), (2, 1))
    assert neighbours((4, 4)) == ((3, 4), (4, 3))
    assert neighbours((1, 2)) == ((1, 1), (1, 3), (2, 2))
    assert neighbours((2, 2)) == ((1, 2), (2, 1), (2, 3), (3, 2))


def test_percepts_in_the_demo_cave():
    """In the demo cave: no breeze or stench at the start, a breeze at (2,1) (a pit at (3,1) is next to it), a stench at (3,4), (4,3) and (4,4) but not at (3,3), glitter only on the gold square and only until the gold is carried."""
    c = demo_cave()
    assert percept(c, (1, 1), False) == NONE
    assert percept(c, (2, 1), False) == BREEZE
    assert [percept(c, s, False).stench for s in ((3, 4), (4, 3), (4, 4), (3, 3))] == [True, True, True, False]
    assert percept(c, (3, 3), False).glitter and not percept(c, (3, 3), True).glitter and not percept(c, (3, 2), False).glitter


# ==== What the agent knows: frontier and knowledge sentences, written as text ====


def test_frontier_is_the_unvisited_squares_next_to_visited_ones_sorted():
    """The frontier of {(1,1),(1,2),(2,1)} is (1,3), (2,2), (3,1), sorted; with only the start visited it is (1,2), (2,1)."""
    assert frontier({(1, 1), (1, 2), (2, 1)}) == ((1, 3), (2, 2), (3, 1))
    assert frontier({(1, 1)}) == ((1, 2), (2, 1))


def test_knowledge_sentences_for_the_demo_stuck_state():
    """For the demo's stuck state the pit sentences are 'P13 | P22' and 'P22 | P31', and with no stench anywhere the Wumpus sentences exclude every open square: ~W13, ~W22, ~W22, ~W31."""
    pit, wum = knowledge(DEMO_STUCK)
    assert pit == ["P13 | P22", "P22 | P31"]
    assert wum == ["~W13", "~W22", "~W22", "~W31"]


def test_a_square_without_a_breeze_excludes_every_open_neighbour():
    """A visited square with no breeze contributes one '~Pxy' sentence for each open neighbour, and a square whose neighbours are all visited contributes nothing."""
    pit, _ = knowledge({(1, 1): NONE})
    assert pit == ["~P12", "~P21"]
    assert knowledge({(1, 1): NONE, (1, 2): NONE, (2, 1): NONE})[0] == ["~P13", "~P22", "~P22", "~P31"]


def test_state_key_is_canonical_and_lists_squares_in_xy_order():
    """The state key writes each visited square as x, y, B or dash, S or dash in (x, y) order joined by semicolons, whatever order the dictionary was built in, for example '11--;12B-;21B-'."""
    assert state_key(DEMO_STUCK) == "11--;12B-;21B-"
    assert state_key({(2, 1): BREEZE, (1, 1): STENCH}) == "11-S;21B-"


# ==== Provably safe squares come from dsdk.logic entailment ====


def test_provably_safe_squares():
    """With nothing perceived at the start both neighbours are provably safe; with a breeze or a stench at the start none is, and a pit-safe but Wumpus-uncertain square is not safe."""
    assert provably_safe({(1, 1): NONE}) == ((1, 2), (2, 1))
    assert provably_safe({(1, 1): BREEZE}) == ()
    assert provably_safe({(1, 1): STENCH}) == ()
    assert provably_safe(DEMO_STUCK) == ()


def test_a_square_cleared_by_a_no_breeze_neighbour_is_safe_even_if_another_has_a_breeze():
    """A frontier square that a no-breeze neighbour clears is safe even when another neighbour felt a breeze: with no breeze at (1,2) and a breeze at (2,1), squares (1,3) and (2,2) are provably safe while the logic pins the pit on (3,1)."""
    percepts = {(1, 1): NONE, (1, 2): NONE, (2, 1): BREEZE}
    safe = provably_safe(percepts)
    assert (1, 3) in safe and (2, 2) in safe and (3, 1) not in safe


# ==== The probability rung: exact risk for each frontier square, from dsdk.prob ====


def test_risk_with_a_breeze_at_the_start_is_five_ninths_for_each_neighbour():
    """With only a breeze at the start, each of the two frontier squares is a pit with probability 5/9, neither can hold the Wumpus, and the expected number of pits is 10/9."""
    j = stuck_risk({(1, 1): BREEZE})
    assert j.status is Status.KNOWN
    assert [(r.cell, r.pit, r.wumpus, r.death) for r in j.value.frontier] == [((1, 2), F(5, 9), F(0), F(5, 9)), ((2, 1), F(5, 9), F(0), F(5, 9))]
    assert j.value.expected_pits == F(10, 9)


def test_risk_in_the_demo_stuck_state():
    """In the demo's stuck state, (2,2) is a pit with probability 25/29 and (1,3) and (3,1) with 9/29 each, with no Wumpus danger, and 43/29 pits are expected."""
    risk = stuck_risk(DEMO_STUCK).value
    assert [(r.cell, r.pit, r.wumpus, r.death) for r in risk.frontier] == [
        ((1, 3), F(9, 29), F(0), F(9, 29)), ((2, 2), F(25, 29), F(0), F(25, 29)), ((3, 1), F(9, 29), F(0), F(9, 29))]
    assert risk.expected_pits == F(43, 29)
    assert PIT_PRIOR == F(1, 5)


def test_a_stench_at_the_start_splits_the_wumpus_evenly_and_leaves_pits_at_zero():
    """With a stench and no breeze at the start the Wumpus is on (1,2) or (2,1) with probability 1/2 each, neither is a pit, so the chance of death at each is 1/2."""
    risk = stuck_risk({(1, 1): STENCH}).value
    assert [(r.cell, r.pit, r.wumpus, r.death) for r in risk.frontier] == [((1, 2), F(0), F(1, 2), F(1, 2)), ((2, 1), F(0), F(1, 2), F(1, 2))]
    assert risk.expected_pits == 0


def test_pit_and_wumpus_danger_combine_as_independent_events():
    """With both a breeze and a stench at the start, each neighbour has pit probability 5/9 and Wumpus probability 1/2, so the chance of death is 1 - (4/9)(1/2) = 7/9."""
    risk = stuck_risk({(1, 1): Percept(True, True, False)}).value
    assert all(r.pit == F(5, 9) and r.wumpus == F(1, 2) and r.death == F(7, 9) for r in risk.frontier)


def test_impossible_percepts_are_invalid_not_a_made_up_number():
    """Percepts no cave can produce (a stench at the start and at (1,2), which would put the Wumpus on two sides at once) give INVALID with a reason about zero-probability evidence, never a probability."""
    j = stuck_risk({(1, 1): STENCH, (1, 2): STENCH})
    assert j.status is Status.INVALID and j.value is None and j.reason.startswith("evidence has probability zero")


def test_a_fully_explored_cave_has_an_empty_frontier():
    """When every square is visited the frontier is empty and the answer is KNOWN with no squares and zero expected pits."""
    j = stuck_risk({(x, y): NONE for x in range(1, 5) for y in range(1, 5)})
    assert j.status is Status.KNOWN and j.value.frontier == () and j.value.expected_pits == 0


def brute_force(percepts):
    """Independent oracle: enumerate pit patterns on the frontier and the Wumpus square over ALL unvisited squares, keep those consistent with every percept."""
    visited = set(percepts)
    front = frontier(visited)
    unvisited = [(x, y) for x in range(1, 5) for y in range(1, 5) if (x, y) not in visited]
    pit_w = {c: F(0) for c in front}
    total_p = F(0)
    for bits in product((False, True), repeat=len(front)):
        pits = {c for c, b in zip(front, bits) if b}
        if all(percepts[v].breeze == any(n in pits for n in neighbours(v) if n not in visited) for v in visited):
            w = F(1, 5) ** len(pits) * F(4, 5) ** (len(front) - len(pits))
            total_p += w
            for c in pits:
                pit_w[c] += w
    wum = {c: 0 for c in front}
    ok = 0
    for cell in unvisited:
        if all(percepts[v].stench == (cell in neighbours(v)) for v in visited):
            ok += 1
            if cell in wum:
                wum[cell] += 1
    return {c: (pit_w[c] / total_p, F(wum[c], ok)) for c in front}


def test_risk_matches_a_brute_force_oracle_on_every_stuck_state_of_forty_caves():
    """For every stuck state reached by either agent in the demo cave and seeds 1 to 40, the pit and Wumpus probabilities equal a plain enumeration that shares no code with dsdk and spreads the Wumpus over ALL unvisited squares, not just the frontier."""
    checked = 0
    for cave in [demo_cave()] + [seeded_cave(s) for s in range(1, 41)]:
        for prob in (False, True):
            for st in run_agent(cave, probabilistic=prob).stuck:
                if len(frontier(set(st))) > 11:
                    continue
                want = brute_force(st)
                got = {r.cell: (r.pit, r.wumpus) for r in stuck_risk(st).value.frontier}
                assert got == want, state_key(st)
                checked += 1
    assert checked >= 30


# ==== The agents ====


def test_the_logic_agent_on_the_demo_cave_gets_stuck_and_leaves():
    """On the demo cave the logic-only agent explores until nothing is provably safe, records that one stuck state, and climbs out empty-handed without gambling."""
    r = run_agent(demo_cave())
    assert r.outcome == "climbed out empty-handed" and r.gambles == ()
    assert [state_key(s) for s in r.stuck] == ["11--;12B-;21B-"]


def test_the_probabilistic_agent_on_the_demo_cave_takes_the_least_risky_step_and_dies():
    """At the demo's stuck state (1,3) and (3,1) are equally risky (9/29), the tie goes to the smaller square (1,3), and that square is a pit, so the probabilistic agent dies."""
    r = run_agent(demo_cave(), probabilistic=True)
    assert r.outcome == "died" and r.gambles == ((1, 3),)


def test_a_safe_cave_is_solved_by_logic_alone_and_the_gold_ends_the_run():
    """In a cave with no hazards near the start the logic agent finds the gold at (2,1), escapes with it, and never becomes stuck."""
    r = run_agent(Cave("empty", frozenset(), (4, 4), (2, 1)))
    assert r.outcome == "escaped with gold" and r.stuck == () and r.gambles == ()


def test_seed_one_is_solved_by_logic_alone():
    """Seed 1 has no hazard near the gold at (1,3), so both agents escape with the gold and neither gambles (checked by hand: (1,2) has no breeze, so (1,3) is provably safe)."""
    for prob in (False, True):
        r = run_agent(seeded_cave(1), probabilistic=prob)
        assert r.outcome == "escaped with gold" and r.gambles == ()


def test_the_probabilistic_agent_can_gamble_twice_and_win_the_gold():
    """On seed 2 the logic agent leaves empty-handed, while the probabilistic agent gambles on (4,2) and then (4,3), survives both, and escapes with the gold."""
    assert run_agent(seeded_cave(2)).outcome == "climbed out empty-handed"
    r = run_agent(seeded_cave(2), probabilistic=True)
    assert r.outcome == "escaped with gold" and r.gambles == ((4, 2), (4, 3)) and len(r.stuck) == 2


def test_the_probabilistic_agent_can_survive_a_gamble_and_still_leave_empty_handed():
    """On seed 5 the probabilistic agent gambles on (1,3) and (3,1), survives, runs out of safe or non-certain squares, and climbs out without the gold."""
    r = run_agent(seeded_cave(5), probabilistic=True)
    assert r.outcome == "climbed out empty-handed" and r.gambles == ((1, 3), (3, 1)) and len(r.stuck) == 3


def test_the_probabilistic_agent_dies_on_seed_three_by_its_first_gamble():
    """On seed 3 the probabilistic agent's first gamble is (1,2), which is a pit, so it dies, while the logic agent leaves empty-handed."""
    assert run_agent(seeded_cave(3)).outcome == "climbed out empty-handed"
    r = run_agent(seeded_cave(3), probabilistic=True)
    assert r.outcome == "died" and r.gambles == ((1, 2),)


def test_every_gamble_is_the_least_risky_square_and_is_never_certain_death():
    """On seeds 1 to 60 every probabilistic gamble is a frontier square with the smallest chance of death (smallest square on ties) and that chance is below 1, recomputed from the stuck state."""
    gambles = 0
    for s in range(1, 61):
        r = run_agent(seeded_cave(s), probabilistic=True)
        for st, g in zip(r.stuck, r.gambles):
            risk = stuck_risk(st).value.frontier
            best = min((x for x in risk if x.death < 1), key=lambda x: (x.death, x.cell))
            assert g == best.cell and best.death < 1
            gambles += 1
    assert gambles > 20


def test_the_logic_agent_never_dies_on_seeds_one_to_three_hundred():
    """The logic-only agent is sound: it does not die in any of the 300 seeded caves."""
    assert sweep_rates(range(1, 301), probabilistic=False).died == 0


def test_death_and_escape_rates_over_three_hundred_seeds():
    """Over seeds 1 to 300 the logic agent escapes with gold in 71 caves, leaves empty-handed in 229 and never dies; the probabilistic agent escapes with gold in 133, leaves empty in 21 and dies in 146, so gambling finds the gold more often and costs lives."""
    logic = sweep_rates(range(1, 301), probabilistic=False)
    prob = sweep_rates(range(1, 301), probabilistic=True)
    assert (logic.caves, logic.died, logic.gold, logic.empty) == (300, 0, 71, 229)
    assert (prob.caves, prob.died, prob.gold, prob.empty) == (300, 146, 133, 21)


def test_a_stuck_state_is_recorded_as_a_copy():
    """The stuck states in a run are separate copies: they keep their own squares even though the agent goes on exploring afterwards."""
    r = run_agent(seeded_cave(5), probabilistic=True)
    sizes = [len(s) for s in r.stuck]
    assert sizes == sorted(sizes) and len(set(sizes)) == len(sizes)


# ==== The data the Lab page needs ====


@pytest.fixture(scope="module")
def data():
    return lab_data()


def test_lab_data_has_a_risk_table_for_every_stuck_state_either_agent_reaches(data):
    """The Lab data has exactly one entry for every distinct stuck state that the logic or the probabilistic agent reaches in the demo cave and seeds 1 to 300, each with the frontier risks as exact fractions."""
    keys = set()
    for cave in [demo_cave()] + [seeded_cave(s) for s in range(1, 301)]:
        for prob in (False, True):
            keys |= {state_key(st) for st in run_agent(cave, probabilistic=prob).stuck}
    assert set(data["states"]) == keys and len(keys) == 174
    demo = data["states"]["11--;12B-;21B-"]
    assert demo == {"frontier": [["13", "9/29", "0/1", "9/29"], ["22", "25/29", "0/1", "25/29"], ["31", "9/29", "0/1", "9/29"]], "expected_pits": "43/29"}


def test_lab_data_rates_and_prior_and_size(data):
    """The Lab data carries the 300-seed rates for both agents and the pit prior 1/5, is plain JSON, and stays small (under 60 KB)."""
    assert data["pit_prior"] == "1/5"
    assert data["rates"] == {"logic": {"caves": 300, "died": 0, "gold": 71, "empty": 229}, "probabilistic": {"caves": 300, "died": 146, "gold": 133, "empty": 21}}
    assert len(json.dumps(data)) < 60_000


def test_lab_data_for_a_few_seeds_is_smaller_and_consistent():
    """Asking for only seeds 1 to 3 gives the demo cave's and those seeds' stuck states and rates over 3 caves, so the seed range is honoured."""
    data = lab_data(range(1, 4))
    assert data["rates"]["logic"]["caves"] == 3 and "11--;12B-;21B-" in data["states"] and len(data["states"]) < 12


# ==== The module calls dsdk.prob and dsdk.logic and does not reimplement them ====


def test_wumpus_module_calls_prob_and_logic_and_has_no_enumeration_of_its_own():
    """wumpus.py imports and calls ask, expectation and prior_belief from dsdk.prob and entails from dsdk.logic, and builds no Belief, no weighted world and no product loops of its own."""
    src = Path(inspect.getsourcefile(wumpus)).read_text()
    tree = ast.parse(src)
    imported = {a.name for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module in ("dsdk.prob", "dsdk.logic") for a in n.names}
    called = {n.func.id for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
    assert {"ask", "expectation", "prior_belief", "entails"} <= imported & called
    for forbidden in ("WeightedWorld", "Belief(", "itertools", "product(", "comb("):
        assert forbidden not in src, forbidden
