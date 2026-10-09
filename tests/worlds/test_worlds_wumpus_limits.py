"""Two extensions of the Logic Cave: (1) the logic agent may be given the fact "exactly one Wumpus", which is what the probability model already
assumes, and (2) the probabilistic agent may be given a risk limit, which turns "never gamble / always gamble" into a whole trade-off curve.

Hand derivations used below:
* Visited (1,1) with nothing perceived, (1,2) and (2,1) both with a stench and no breeze. The stench at (1,2) puts the Wumpus on (1,3) or (2,2); the
  stench at (2,1) puts it on (2,2) or (3,1). Exactly one Wumpus must satisfy both, so it is on (2,2), and (1,3) and (3,1) are Wumpus-free. Without the
  "exactly one" fact logic cannot exclude them (a Wumpus on (1,3) and another on (3,1) would explain both stenches), with it logic can.
* A risk limit of 0 means "only step on squares with zero chance of death", which is the same set of squares the exactly-one logic proves safe.
* An exact (Clopper-Pearson) 95% interval for 0 events in n trials is (0, 1 - 0.025^(1/n)). For 0 deaths in 300 caves: upper end 1 - 0.025^(1/300) = 0.01222.
"""
import ast
import inspect
import json
import math
from fractions import Fraction as F
from pathlib import Path

import pytest

from dsdk.worlds import wumpus
from dsdk.worlds.wumpus import (
    RISK_LIMITS, Percept, demo_cave, exactly_one_wumpus_text, lab_data, provably_safe, risk_curve, run_agent, seeded_cave, state_key, stuck_risk,
    sweep_rates,
)

NONE = Percept(False, False, False)
STENCH = Percept(False, True, False)
TWO_STENCHES = {(1, 1): NONE, (1, 2): STENCH, (2, 1): STENCH}
SEEDS = range(1, 301)


def cp_interval(k, n, confidence=0.95):
    """An independent Clopper-Pearson interval: plain floats and bisection on binomial tails, no dsdk."""
    a = (1 - confidence) / 2

    def tail_le(kk, p):  # P(X <= kk)
        return sum(math.comb(n, i) * p**i * (1 - p) ** (n - i) for i in range(kk + 1))

    def solve(f):
        lo, hi = 0.0, 1.0
        for _ in range(100):
            mid = (lo + hi) / 2
            lo, hi = (lo, mid) if f(mid) else (mid, hi)
        return (lo + hi) / 2

    low = 0.0 if k == 0 else solve(lambda p: 1 - tail_le(k - 1, p) >= a)
    high = 1.0 if k == n else solve(lambda p: tail_le(k, p) <= a)
    return low, high


@pytest.fixture(scope="module")
def curve():
    return risk_curve()


@pytest.fixture(scope="module")
def stuck_states():
    """Every stuck state met by the logic, the exactly-one logic and the probabilistic agent on the demo cave and seeds 1 to 300."""
    states = {}
    for cave in [demo_cave()] + [seeded_cave(s) for s in SEEDS]:
        for kw in ({}, {"exactly_one_wumpus": True}, {"probabilistic": True}):
            for st in run_agent(cave, **kw).stuck:
                states.setdefault(state_key(st), st)
    return states


# ==== The exactly-one-Wumpus fact as text ====


def test_the_exactly_one_text_lists_every_variable_then_every_pair():
    """For frontier squares (1,2) and (2,1) the fact is '(W12 | W21 | WR) & ~(W12 & W21) & ~(W12 & WR) & ~(W21 & WR)', with the off-frontier variable WR last."""
    assert exactly_one_wumpus_text(((1, 2), (2, 1))) == "(W12 | W21 | WR) & ~(W12 & W21) & ~(W12 & WR) & ~(W21 & WR)"


def test_the_exactly_one_text_for_one_square_and_for_none():
    """One frontier square gives '(W12 | WR) & ~(W12 & WR)' and an empty frontier gives just '(WR)'."""
    assert exactly_one_wumpus_text(((1, 2),)) == "(W12 | WR) & ~(W12 & WR)"
    assert exactly_one_wumpus_text(()) == "(WR)"


# ==== Logic with the exactly-one fact proves more, and exactly what probability calls risk-free ====


def test_default_logic_is_unchanged_and_the_option_is_explicit():
    """Without the option the logic agent proves nothing on the two-stench state; asking explicitly for False gives the same answer, and a non-bool option is a TypeError."""
    assert provably_safe(TWO_STENCHES) == () == provably_safe(TWO_STENCHES, exactly_one_wumpus=False)
    with pytest.raises(TypeError):
        provably_safe(TWO_STENCHES, exactly_one_wumpus=1)


def test_two_overlapping_stenches_pin_the_wumpus_and_clear_its_neighbours():
    """With stenches at (1,2) and (2,1) and the exactly-one fact, logic proves (1,3) and (3,1) safe, while (2,2) stays unsafe because the Wumpus must be there."""
    assert provably_safe(TWO_STENCHES, exactly_one_wumpus=True) == ((1, 3), (3, 1))


def test_probability_agrees_on_the_two_stench_state():
    """On the same state dsdk.prob gives the Wumpus probability 1 on (2,2) and a death chance of exactly 0 on (1,3) and (3,1): the squares logic just proved safe."""
    risk = {r.cell: r for r in stuck_risk(TWO_STENCHES).value.frontier}
    assert risk[(2, 2)].wumpus == 1 and risk[(2, 2)].death == 1
    assert risk[(1, 3)].death == 0 and risk[(3, 1)].death == 0


def test_with_the_option_logic_proves_exactly_the_zero_risk_squares_on_every_stuck_state_of_the_seeds(stuck_states):
    """On all the distinct stuck states met by any of the agents on the demo cave and seeds 1 to 300, the squares logic proves safe with the exactly-one fact are exactly the squares dsdk.prob gives a death chance of 0: neither more nor fewer."""
    assert len(stuck_states) >= 150
    for key, st in stuck_states.items():
        zero = {r.cell for r in stuck_risk(st).value.frontier if r.death == 0}
        assert set(provably_safe(st, exactly_one_wumpus=True)) == zero, key


def test_on_states_where_the_exactly_one_agent_is_stuck_every_square_has_some_risk(stuck_states):
    """Where the exactly-one logic agent itself gets stuck, nothing is provable and every frontier square has a death chance above 0, so there is no free square left to find."""
    stuck = 0
    for cave in [demo_cave()] + [seeded_cave(s) for s in SEEDS]:
        for st in run_agent(cave, exactly_one_wumpus=True).stuck:
            stuck += 1
            assert provably_safe(st, exactly_one_wumpus=True) == ()
            assert all(r.death > 0 for r in stuck_risk(st).value.frontier)
    assert stuck > 150


def test_the_default_logic_agent_still_reads_0_died_71_gold_229_empty():
    """The default logic-only agent over seeds 1 to 300 still gives 0 died, 71 escaped with gold and 229 climbed out empty, with the option written out or left out."""
    for kw in ({}, {"exactly_one_wumpus": False}):
        r = sweep_rates(SEEDS, probabilistic=False, **kw)
        assert (r.caves, r.died, r.gold, r.empty) == (300, 0, 71, 229)


def test_the_exactly_one_logic_agent_finds_eight_more_golds_and_never_dies():
    """With the exactly-one fact the logic agent over seeds 1 to 300 escapes with gold in 79 caves instead of 71, climbs out empty in 221 and still never dies."""
    r = sweep_rates(SEEDS, probabilistic=False, exactly_one_wumpus=True)
    assert (r.caves, r.died, r.gold, r.empty) == (300, 0, 79, 221)


def test_a_risk_limit_of_zero_is_the_exactly_one_logic_agent():
    """On every one of the 300 seeds the probabilistic agent with risk limit 0 has the same outcome as the logic agent with the exactly-one fact: zero risk and provably safe are the same thing."""
    for s in SEEDS:
        cave = seeded_cave(s)
        assert run_agent(cave, probabilistic=True, risk_limit=0).outcome == run_agent(cave, exactly_one_wumpus=True).outcome, s


# ==== The risk limit ====


def test_the_default_risk_limit_reproduces_146_133_21():
    """With no risk limit, with a limit of None written out, and with a limit of 1, the probabilistic agent over seeds 1 to 300 still gives 146 died, 133 escaped with gold and 21 climbed out empty, because certain death is never chosen."""
    for kw in ({}, {"risk_limit": None}, {"risk_limit": 1}, {"risk_limit": F(1)}):
        r = sweep_rates(SEEDS, probabilistic=True, **kw)
        assert (r.caves, r.died, r.gold, r.empty) == (300, 146, 133, 21), kw


def test_risk_limits_are_validated():
    """A risk limit needs the probabilistic agent (ValueError otherwise), must be a number from 0 to 1 (a bool or a string is a TypeError, a negative number or one above 1 a ValueError), and 0.2 means exactly 1/5."""
    cave = seeded_cave(2)
    with pytest.raises(ValueError, match="risk_limit needs probabilistic=True"):
        run_agent(cave, risk_limit=F(1, 2))
    for bad in (True, "0.5", [0.5]):
        with pytest.raises(TypeError):
            run_agent(cave, probabilistic=True, risk_limit=bad)
    for bad in (-0.1, 1.5, F(3, 2)):
        with pytest.raises(ValueError):
            run_agent(cave, probabilistic=True, risk_limit=bad)
    for s in range(1, 61):
        c = seeded_cave(s)
        assert run_agent(c, probabilistic=True, risk_limit=0.2) == run_agent(c, probabilistic=True, risk_limit=F(1, 5))


def test_a_limited_agent_stops_instead_of_taking_a_bigger_risk():
    """On seed 3 the probabilistic agent's first gamble has a death chance above 1/5, so with a limit of 1/5 it climbs out empty-handed instead of dying there."""
    assert run_agent(seeded_cave(3), probabilistic=True).outcome == "died"
    r = run_agent(seeded_cave(3), probabilistic=True, risk_limit=F(1, 5))
    assert r.outcome == "climbed out empty-handed" and r.gambles == ()


def test_every_gamble_respects_the_limit():
    """On seeds 1 to 60 with a limit of 1/3, every gamble taken has a recomputed death chance of at most 1/3, and it is the least risky square of its stuck state."""
    taken = 0
    for s in range(1, 61):
        r = run_agent(seeded_cave(s), probabilistic=True, risk_limit=F(1, 3))
        for st, g in zip(r.stuck, r.gambles):
            risk = {x.cell: x.death for x in stuck_risk(st).value.frontier}
            assert risk[g] <= F(1, 3) and risk[g] == min(v for v in risk.values() if v < 1)
            taken += 1
    assert taken > 10


def test_a_limited_agent_only_reaches_stuck_states_the_unlimited_agent_reaches():
    """For limits 1/5 and 1/3 on all 300 seeds, every stuck state a limited agent reaches is also reached by the unlimited probabilistic agent on that cave, so the Lab's risk table already covers the curve."""
    for s in SEEDS:
        cave = seeded_cave(s)
        full = {state_key(x) for x in run_agent(cave, probabilistic=True).stuck}
        for limit in (F(1, 5), F(1, 3)):
            assert {state_key(x) for x in run_agent(cave, probabilistic=True, risk_limit=limit).stuck} <= full, (s, limit)


# ==== The risk curve with exact intervals from dsdk.prob ====


def test_the_curve_counts_over_seeds_1_to_300():
    """With the default limits 0, 1/10, 1/5, 1/3, 1/2 and 1 the curve shows (died, gold) = (0, 79), (0, 79), (3, 86), (21, 102), (32, 109), (146, 133) over 300 caves, and the three outcomes always add up to 300."""
    assert RISK_LIMITS == (F(0), F(1, 10), F(1, 5), F(1, 3), F(1, 2), F(1))
    curve_ = risk_curve()
    assert [p.limit for p in curve_] == list(RISK_LIMITS)
    assert [(p.died, p.gold) for p in curve_] == [(0, 79), (0, 79), (3, 86), (21, 102), (32, 109), (146, 133)]
    assert all(p.caves == 300 and p.died + p.gold + p.empty == 300 for p in curve_)


def test_the_last_point_of_the_curve_is_the_unlimited_agent():
    """The limit-1 end of the curve is the 146 / 133 / 21 of the unlimited probabilistic agent."""
    last = risk_curve()[-1]
    assert (last.limit, last.died, last.gold, last.empty) == (F(1), 146, 133, 21)


def test_zero_deaths_in_300_caves_has_the_closed_form_upper_end(curve):
    """At limit 0 there are 0 deaths in 300 caves, so the exact 95% interval is 0 to 1 - 0.025^(1/300) = 0.012223, a value derived by hand from the binomial tail."""
    p = curve[0]
    assert p.death_low == 0.0
    assert p.death_high == pytest.approx(1 - 0.025 ** (1 / 300), abs=1e-9) and round(p.death_high, 5) == 0.01222


def test_intervals_hand_checked_on_two_limits_against_an_independent_calculation(curve):
    """For limit 1/5 (3 deaths, 86 golds in 300) and limit 1/3 (21 deaths, 102 golds) the death and gold intervals equal a separate Clopper-Pearson calculation done with plain floats and bisection, to 1e-9; for 3 deaths the textbook interval is 0.0021 to 0.0289."""
    by_limit = {p.limit: p for p in curve}
    for limit, (d, g) in ((F(1, 5), (3, 86)), (F(1, 3), (21, 102))):
        p = by_limit[limit]
        assert (p.died, p.gold) == (d, g)
        for got, want in ((p.death_low, cp_interval(d, 300)[0]), (p.death_high, cp_interval(d, 300)[1]),
                          (p.gold_low, cp_interval(g, 300)[0]), (p.gold_high, cp_interval(g, 300)[1])):
            assert got == pytest.approx(want, abs=1e-9)
    p = by_limit[F(1, 5)]
    assert round(p.death_low, 4) == 0.0021 and round(p.death_high, 4) == 0.0289


def test_every_point_has_intervals_around_its_rates(curve):
    """Each curve point's death and gold intervals bracket the observed rate (died/300 and gold/300) and stay inside 0 to 1."""
    for p in curve:
        assert 0 <= p.death_low <= p.died / 300 <= p.death_high <= 1
        assert 0 <= p.gold_low <= p.gold / 300 <= p.gold_high <= 1


def test_the_curve_takes_its_intervals_from_dsdk_prob():
    """wumpus.py imports and calls exact_interval from dsdk.prob (and to_prob for limits), and the module source contains no square root, binomial coefficient or z-score of its own."""
    src = Path(inspect.getsourcefile(wumpus)).read_text()
    tree = ast.parse(src)
    imported = {a.name for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module == "dsdk.prob" for a in n.names}
    called = {n.func.id for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
    assert {"exact_interval", "to_prob"} <= imported and "exact_interval" in called
    for forbidden in ("sqrt", "comb(", "1.96", "wilson"):
        assert forbidden not in src, forbidden


def test_curve_argument_checks_and_custom_limits():
    """No seeds is a ValueError, custom limits come back in the order given (converted with to_prob, so 0.5 is 1/2), and a bad limit is rejected like in run_agent."""
    with pytest.raises(ValueError, match="at least one seed"):
        risk_curve(seeds=[])
    pts = risk_curve(seeds=range(1, 21), limits=(0.5, 0))
    assert [p.limit for p in pts] == [F(1, 2), F(0)] and all(p.caves == 20 for p in pts)
    with pytest.raises(ValueError):
        risk_curve(seeds=range(1, 6), limits=(2,))


# ==== The Lab data carries the curve ====


def test_lab_data_has_the_curve_as_json(curve):
    """The Lab data gains a 'curve' list with one entry per default limit holding the limit as text like '1/5', the counts, and the death and gold intervals as pairs of floats equal to the risk curve's; the data stays plain JSON under 60 KB."""
    data = lab_data()
    assert [c["limit"] for c in data["curve"]] == ["0/1", "1/10", "1/5", "1/3", "1/2", "1/1"]
    for entry, p in zip(data["curve"], curve):
        assert (entry["caves"], entry["died"], entry["gold"], entry["empty"]) == (p.caves, p.died, p.gold, p.empty)
        assert entry["death"] == [p.death_low, p.death_high] and entry["gold_ci"] == [p.gold_low, p.gold_high]
    assert data["rates"]["probabilistic"] == {"caves": 300, "died": 146, "gold": 133, "empty": 21}
    assert len(json.dumps(data)) < 60_000
