"""The Wumpus world for the Lab's Logic Cave: caves, percepts, the logic-only agent, and the probability rung that
answers when the logic-only agent has nothing provably safe left.

Squares are ``(x, y)`` tuples with ``1 <= x, y <= 4``; the agent starts on ``(1, 1)``. A square's text name is ``f"{x}{y}"``, so the
propositional variables are ``P21`` (a pit at (2,1)) and ``W21`` (the Wumpus at (2,1)).

The cave (identical, rule for rule, to the page ``lab/src/lab.html``)
--------------------------------------------------------------------
* ``demo_cave()``: pits at (3,1), (1,3), (3,4); Wumpus at (4,4); gold at (3,3).
* ``seeded_cave(seed)``: the 15 squares other than (1,1) in the order ``y = 1..4`` outer, ``x = 1..4`` inner. A random stream is
  ``mulberry32(seed)``. Each of the 15 squares in turn is a pit when ``rng() < 0.2`` (so a pit may share a square with the Wumpus or the
  gold); then ``wumpus = cells[floor(rng() * 15)]``, then ``gold = cells[floor(rng() * 15)]``, in that order, three separate groups of draws.
* Percepts at ``cell`` (``has_gold`` = the agent already carries the gold): ``breeze`` = some orthogonal neighbour is a pit;
  ``stench`` = the Wumpus is on ``cell`` or on an orthogonal neighbour; ``glitter`` = the gold is on ``cell`` and ``has_gold`` is false.
* A square kills the agent on entry when it is a pit or holds the Wumpus.

What the agent knows
--------------------
Visited squares are known pit-free and Wumpus-free (the agent survived them). For each visited square ``v`` let ``open(v)`` be its
UNVISITED neighbours, sorted by ``(x, y)``. The knowledge base is two lists of sentences in the relaxed formula text of
``dsdk.lang.parse_formula``:
* pit sentences: if ``v`` has a breeze, ``"P.. | P.. | ..."`` over ``open(v)`` (joined with ``" | "``); otherwise one sentence ``"~Pxy"`` for
  each ``(x, y)`` in ``open(v)``;
* Wumpus sentences: the same with ``W`` and the stench.
Visited squares are taken in ``(x, y)`` order. The FRONTIER is the set of unvisited squares next to a visited one, sorted by ``(x, y)``.

Probability model
-----------------
Pits are independent, each with prior ``PIT_PRIOR`` = 1/5 (the generator's 0.2), on the frontier squares; unvisited squares off the frontier
cannot change a frontier square's posterior. The Wumpus is in exactly one UNVISITED square, uniformly. Only the frontier squares appear in any
sentence, so the belief has one variable ``Wxy`` per frontier square plus ONE extra variable ``WR`` standing for "the Wumpus is on an unvisited square
off the frontier"; exactly one of these variables is true, every such world has weight 1. This grouping does not change any frontier posterior: a
stench sentence lists all of its visited square's unvisited neighbours, so it rules ``WR`` out, and when there is no stench anywhere every frontier
``Wxy`` is ruled out and ``WR`` is the only world left. Pits and the Wumpus are independent, so
P(death at c) = 1 - (1 - P(pit at c)) * (1 - P(Wumpus at c)).
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from fractions import Fraction

from dsdk.core import Judgment, Status
from dsdk.logic import Not, Var, entails
from dsdk.prob import ask, exact_interval, expectation, prior_belief, to_prob  # noqa: F401  (exact_interval and to_prob: used by the new functions)
from dsdk.lang import parse_formula

Cell = tuple[int, int]
SIZE = 4
START: Cell = (1, 1)
PIT_PRIOR = Fraction(1, 5)
OUTCOMES = ("died", "escaped with gold", "climbed out empty-handed")


def imul(a: int, b: int) -> int:
    return (a * b) & 0xFFFFFFFF


def mulberry32(seed: int):
    """The generator of the page (a 32-bit mulberry32): returns a function that gives floats in [0, 1) exactly as the JavaScript does."""
    state = seed & 0xFFFFFFFF

    def rng() -> float:
        nonlocal state
        state = (state + 0x6D2B79F5) & 0xFFFFFFFF
        t = imul(state ^ (state >> 15), 1 | state)
        t = ((t + imul(t ^ (t >> 7), 61 | t)) & 0xFFFFFFFF) ^ t
        return ((t ^ (t >> 14)) & 0xFFFFFFFF) / 4294967296

    return rng


@dataclass(frozen=True)
class Cave:
    name: str
    pits: frozenset
    wumpus: Cell
    gold: Cell


def demo_cave() -> Cave:
    return Cave("Demo cave", frozenset({(3, 1), (1, 3), (3, 4)}), (4, 4), (3, 3))


def seeded_cave(seed: int) -> Cave:
    rng = mulberry32(seed)
    cells = [(x, y) for y in range(1, SIZE + 1) for x in range(1, SIZE + 1) if (x, y) != START]
    pits = frozenset(c for c in cells if rng() < 0.2)
    wumpus = cells[math.floor(rng() * len(cells))]
    gold = cells[math.floor(rng() * len(cells))]
    return Cave(f"Random cave #{seed}", pits, wumpus, gold)


def neighbours(cell: Cell) -> tuple[Cell, ...]:
    x, y = cell
    candidates = ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1))
    return tuple(sorted(c for c in candidates if 1 <= c[0] <= SIZE and 1 <= c[1] <= SIZE))


@dataclass(frozen=True)
class Percept:
    breeze: bool
    stench: bool
    glitter: bool


def percept(cave: Cave, cell: Cell, has_gold: bool) -> Percept:
    near = neighbours(cell)
    breeze = any(n in cave.pits for n in near)
    stench = cave.wumpus == cell or cave.wumpus in near
    glitter = cave.gold == cell and not has_gold
    return Percept(breeze, stench, glitter)


def name(cell: Cell) -> str:
    return f"{cell[0]}{cell[1]}"


def frontier(visited) -> tuple[Cell, ...]:
    seen = set(visited)
    out = {n for v in seen for n in neighbours(v) if n not in seen}
    return tuple(sorted(out))


def knowledge(percepts: dict) -> tuple[list[str], list[str]]:
    """(pit sentences, Wumpus sentences) for the visited squares in ``percepts`` (``{cell: Percept}``), as described in the module docstring."""
    pit_sentences: list[str] = []
    wumpus_sentences: list[str] = []
    for v in sorted(percepts):
        p = percepts[v]
        open_cells = [n for n in neighbours(v) if n not in percepts]
        if p.breeze:
            if open_cells:
                pit_sentences.append(" | ".join(f"P{name(n)}" for n in open_cells))
        else:
            pit_sentences.extend(f"~P{name(n)}" for n in open_cells)
        if p.stench:
            if open_cells:
                wumpus_sentences.append(" | ".join(f"W{name(n)}" for n in open_cells))
        else:
            wumpus_sentences.extend(f"~W{name(n)}" for n in open_cells)
    return pit_sentences, wumpus_sentences


def conjunction(sentences: list[str]) -> str:
    if not sentences:
        return "true"
    return " & ".join(f"({s})" for s in sentences)


def state_key(percepts: dict) -> str:
    """Canonical text of a knowledge state: for each visited square in ``(x, y)`` order ``f"{x}{y}{B or -}{S or -}"`` joined by ``";"``."""
    return ";".join(
        f"{name(c)}{'B' if p.breeze else '-'}{'S' if p.stench else '-'}" for c, p in sorted(percepts.items())
    )


@dataclass(frozen=True)
class CellRisk:
    cell: Cell
    pit: Fraction
    wumpus: Fraction
    death: Fraction


@dataclass(frozen=True)
class StuckRisk:
    frontier: tuple[CellRisk, ...]
    expected_pits: Fraction



def stuck_risk(percepts: dict) -> Judgment:
    """Exact risk of each frontier square given what the agent perceived at the visited squares in ``percepts``.

    ``KNOWN`` with a :class:`StuckRisk`: ``frontier`` has one :class:`CellRisk` per frontier square in ``(x, y)`` order:
    ``pit = P(Pxy | pit sentences)`` over ``prior_belief({Pxy: PIT_PRIOR for each frontier square})``, ``wumpus = P(Wxy | Wumpus sentences)``
    over the Wumpus belief of the module docstring (``prior_belief({}, exactly-one(frontier W's + WR))``), ``death = 1 - (1 - pit) * (1 - wumpus)``; ``expected_pits`` is ``dsdk.prob.expectation`` of the number of pits on the
    frontier given the pit sentences. Every number is obtained by CALLING ``dsdk.prob`` (``ask`` with the sentences as TEXT, ``expectation``):
    this function does no probability arithmetic beyond the ``death`` formula. An empty frontier gives ``KNOWN`` with ``frontier=()`` and
    ``expected_pits == 0``. If the percepts are impossible (a zero-probability evidence, which no real cave produces) the answer is
    ``INVALID`` with the reason of the first failing ``ask``. ``TypeError`` if ``percepts`` is not a dict of cell -> Percept.
    """
    if not isinstance(percepts, dict):
        raise TypeError(f"percepts must be a dict of cell -> Percept, not {type(percepts).__name__}")
    front = frontier(set(percepts))
    if not front:
        return Judgment(Status.KNOWN, StuckRisk((), Fraction(0)), "")
    pit_sentences, wumpus_sentences = knowledge(percepts)
    pit_text = conjunction(pit_sentences)
    wumpus_text = conjunction(wumpus_sentences)
    pit_belief = prior_belief({f"P{name(c)}": PIT_PRIOR for c in front})
    wumpus_vars = [f"W{name(c)}" for c in front] + ["WR"]
    exactly_one = [f"({' | '.join(wumpus_vars)})"]
    for i, a in enumerate(wumpus_vars):
        for b in wumpus_vars[i + 1:]:
            exactly_one.append(f"~({a} & {b})")
    wumpus_belief = prior_belief({}, parse_formula(" & ".join(exactly_one), relaxed=True))
    rows: list[CellRisk] = []
    for c in front:
        pit = ask(pit_belief, f"P{name(c)}", pit_text)
        if pit.status is not Status.KNOWN:
            return Judgment(Status.INVALID, None, pit.reason)
        wum = ask(wumpus_belief, f"W{name(c)}", wumpus_text)
        if wum.status is not Status.KNOWN:
            return Judgment(Status.INVALID, None, wum.reason)
        death = 1 - (1 - pit.value) * (1 - wum.value)
        rows.append(CellRisk(c, pit.value, wum.value, death))
    expr = " + ".join(f"(if P{name(c)} then 1 else 0)" for c in front)
    ex = expectation(pit_belief, expr, pit_text)
    if ex.status is not Status.KNOWN:
        return Judgment(Status.INVALID, None, ex.reason)
    return Judgment(Status.KNOWN, StuckRisk(tuple(rows), ex.value), "")


def exactly_one_wumpus_text(front: tuple[Cell, ...]) -> str:
    """The fact "there is exactly one Wumpus, on a frontier square or off the frontier" as relaxed formula text over the variables
    ``Wxy`` of the frontier squares (in the order given) and the extra variable ``WR`` (the Wumpus is on an unvisited square off the frontier).

    The text is ``"(W12 | W21 | WR)"`` (the disjunction of ALL these variables, ``WR`` last) followed by ``" & ~(a & b)"`` for every pair
    ``(a, b)`` of the variables, pairs in order (first variable against each later one, then the second, and so on), joined with ``" & "``.
    Example: ``exactly_one_wumpus_text(((1, 2), (2, 1)))`` is
    ``"(W12 | W21 | WR) & ~(W12 & W21) & ~(W12 & WR) & ~(W21 & WR)"``. An empty ``front`` gives ``"(WR)"`` (no pairs). This is the same fact the
    probability model of :func:`stuck_risk` uses, so logic and probability can be compared on equal terms.
    """
    variables = [f"W{name(c)}" for c in front] + ["WR"]
    parts = [f"({' | '.join(variables)})"]
    for i, a in enumerate(variables):
        for b in variables[i + 1:]:
            parts.append(f"~({a} & {b})")
    return " & ".join(parts)


def provably_safe(percepts: dict, *, exactly_one_wumpus: bool = False) -> tuple[Cell, ...]:
    """Frontier squares that the knowledge base ENTAILS to be pit-free and Wumpus-free, by ``dsdk.logic.entails`` over the sentences parsed
    with ``dsdk.lang.parse_formula(relaxed=True)`` (the pit sentences decide pits and the Wumpus sentences decide the Wumpus), in ``(x, y)`` order.

    ``exactly_one_wumpus`` (default ``False``, which is the page's logic agent and must give exactly the answers of the version without this
    option): when ``True`` the Wumpus knowledge also contains the fact of :func:`exactly_one_wumpus_text` for the current frontier (one more
    formula, parsed the same way). That fact lets logic rule out squares that two overlapping stenches cannot both explain: with stenches at
    (1,2) and (2,1) the Wumpus must be on (2,2), so (1,3) and (3,1) become provably safe. With the option on, a frontier square is provably
    safe EXACTLY when :func:`stuck_risk` gives it ``death == 0`` (logic and probability agree). ``TypeError`` if ``exactly_one_wumpus`` is not a bool."""
    if not isinstance(exactly_one_wumpus, bool):
        raise TypeError(f"exactly_one_wumpus must be a bool, not {type(exactly_one_wumpus).__name__}")
    front = frontier(set(percepts))
    pit_formulas = [parse_formula(s, relaxed=True) for s in knowledge(percepts)[0]]
    wumpus_formulas = [parse_formula(s, relaxed=True) for s in knowledge(percepts)[1]]
    if exactly_one_wumpus and front:
        wumpus_formulas.append(parse_formula(exactly_one_wumpus_text(front), relaxed=True))
    return tuple(
        c
        for c in front
        if entails(pit_formulas, Not(Var(f"P{name(c)}"))) and entails(wumpus_formulas, Not(Var(f"W{name(c)}")))
    )


@dataclass(frozen=True)
class AgentRun:
    outcome: str
    stuck: tuple[dict, ...]
    gambles: tuple[Cell, ...]


_STUCK_RISK: dict = {}
"""Module-level memo of :func:`stuck_risk` by :func:`state_key` (a knowledge state always has the same risk)."""


def _cached_stuck_risk(percepts: dict) -> Judgment:
    """:func:`stuck_risk` of ``percepts``, computed once per knowledge state."""
    if not isinstance(percepts, dict):
        raise TypeError(f"percepts must be a dict of cell -> Percept, not {type(percepts).__name__}")
    key = state_key(percepts)
    if key not in _STUCK_RISK:
        _STUCK_RISK[key] = stuck_risk(percepts)
    return _STUCK_RISK[key]


def run_agent(cave: Cave, *, probabilistic: bool = False, exactly_one_wumpus: bool = False, risk_limit: object = None) -> AgentRun:
    """Play one cave. Starting on (1,1) with its percept:
    1. a square with glitter while the gold is not carried: take the gold;
    2. carrying the gold: leave -> ``"escaped with gold"``;
    3. otherwise visit every provably safe frontier square (in ``(x, y)`` order, one at a time, re-deriving after each; the order cannot change
       the final outcome because safety only grows with knowledge);
    4. when nothing is provably safe the agent is STUCK: the current ``percepts`` map is appended to ``stuck``. The logic-only agent leaves empty-handed
       (``"climbed out empty-handed"``). The probabilistic agent (``probabilistic=True``) asks :func:`stuck_risk`, drops frontier squares with
       ``death == 1``, and if any remain steps onto the one with the smallest ``death`` (ties: smallest ``(x, y)``), appending it to ``gambles``;
       entering a pit or the Wumpus square ends the run with ``"died"``, otherwise the square is visited and the loop continues; if none remain it
       leaves empty-handed.
    ``stuck`` holds a copy of the percepts dict at each stuck moment (cell -> Percept).
    Options (the defaults reproduce the behaviour described above exactly, so the page's agents and every earlier number are unchanged):
    * ``exactly_one_wumpus``: passed to :func:`provably_safe` (step 3 and the stuck test use the stronger logic). ``False`` by default.
    * ``risk_limit``: ``None`` (default) or a number between 0 and 1 inclusive, converted with ``dsdk.prob.to_prob`` (so ``0.2`` is exactly 1/5; its
      ``TypeError``/``ValueError`` propagate for a bool, a string, a negative number or one above 1). In step 4 the probabilistic agent only considers
      frontier squares with ``death < 1`` AND (when a limit is given) ``death <= risk_limit``; if none qualify it leaves empty-handed. A limit of 1 therefore
      behaves exactly like ``None`` (certain death is never chosen), and a limit of 0 steps only on squares with zero risk. ``risk_limit`` is only
      meaningful for the probabilistic agent: giving a limit with ``probabilistic=False`` raises ``ValueError("risk_limit needs probabilistic=True")``
      (after the limit itself has been validated). A limited agent either picks the same square as the unlimited one or stops, so every stuck state it
      reaches is also reached by the unlimited probabilistic agent on the same cave.
    """
    limit = None if risk_limit is None else to_prob(risk_limit, "risk_limit")
    if limit is not None and not probabilistic:
        raise ValueError("risk_limit needs probabilistic=True")
    percepts: dict = {START: percept(cave, START, False)}
    here = START
    has_gold = False
    stuck: list[dict] = []
    gambles: list[Cell] = []
    while True:
        if percepts[here].glitter and not has_gold:
            has_gold = True
        if has_gold:
            return AgentRun("escaped with gold", tuple(stuck), tuple(gambles))
        safe = provably_safe(percepts, exactly_one_wumpus=exactly_one_wumpus)
        if safe:
            here = safe[0]
            percepts[here] = percept(cave, here, has_gold)
            continue
        stuck.append(dict(percepts))
        if not probabilistic:
            return AgentRun("climbed out empty-handed", tuple(stuck), tuple(gambles))
        risk = _cached_stuck_risk(percepts)
        if risk.status is not Status.KNOWN:
            raise RuntimeError(risk.reason)
        options = [r for r in risk.value.frontier if r.death != 1 and (limit is None or r.death <= limit)]
        if not options:
            return AgentRun("climbed out empty-handed", tuple(stuck), tuple(gambles))
        best = min(options, key=lambda r: (r.death, r.cell))
        gambles.append(best.cell)
        here = best.cell
        if here in cave.pits or here == cave.wumpus:
            return AgentRun("died", tuple(stuck), tuple(gambles))
        percepts[here] = percept(cave, here, has_gold)


@dataclass(frozen=True)
class Rates:
    caves: int
    died: int
    gold: int
    empty: int


def sweep_rates(seeds, *, probabilistic: bool, exactly_one_wumpus: bool = False, risk_limit: object = None) -> Rates:
    """Outcome counts over ``seeded_cave(s)`` for each seed: how many died, escaped with gold, climbed out empty-handed. The two options are passed
    unchanged to :func:`run_agent` (defaults reproduce the earlier counts: logic-only 0/71/229, probabilistic 146/133/21 died/gold/empty over seeds 1 to 300)."""
    caves = died = gold = empty = 0
    for s in seeds:
        caves += 1
        outcome = run_agent(
            seeded_cave(s), probabilistic=probabilistic, exactly_one_wumpus=exactly_one_wumpus, risk_limit=risk_limit
        ).outcome
        if outcome == "died":
            died += 1
        elif outcome == "escaped with gold":
            gold += 1
        else:
            empty += 1
    return Rates(caves, died, gold, empty)


RISK_LIMITS = (Fraction(0), Fraction(1, 10), Fraction(1, 5), Fraction(1, 3), Fraction(1, 2), Fraction(1))
"""The default risk limits of :func:`risk_curve`."""


@dataclass(frozen=True)
class CurvePoint:
    """One point of the risk curve: the probabilistic agent with ``risk_limit == limit`` over ``caves`` seeded caves.

    ``died`` / ``gold`` / ``empty`` are the outcome counts (they add up to ``caves``). ``death_low`` / ``death_high`` and ``gold_low`` /
    ``gold_high`` are the ends of the exact (Clopper-Pearson) 95% intervals for the death rate ``died / caves`` and the gold rate ``gold / caves``,
    taken UNCHANGED from :func:`dsdk.prob.exact_interval`.
    """

    limit: Fraction
    caves: int
    died: int
    gold: int
    empty: int
    death_low: float
    death_high: float
    gold_low: float
    gold_high: float


def risk_curve(seeds=range(1, 301), limits=RISK_LIMITS, *, exactly_one_wumpus: bool = False) -> tuple[CurvePoint, ...]:
    """How much death buys how much gold: one :class:`CurvePoint` per limit, in the order of ``limits``.

    For each limit run :func:`sweep_rates` with ``probabilistic=True`` and ``risk_limit=limit`` over ``seeds`` (every limit is validated by
    :func:`run_agent`; ``exactly_one_wumpus`` is passed on), then ask ``dsdk.prob.exact_interval(died, caves)`` and
    ``dsdk.prob.exact_interval(gold, caves)`` (95%). This function does no interval arithmetic of its own. Each ``exact_interval`` call costs several seconds at 300 caves, so the result for a given ``(count, caves)`` pair may be remembered in a module-level dict and reused (the same counts recur across limits and calls). ``limit`` in the result is the limit
    converted with ``dsdk.prob.to_prob``. ``seeds`` is consumed once (a range or any iterable of ints); no seeds at all raises ``ValueError("risk_curve
    needs at least one seed")``. Over seeds 1 to 300 with the default limits the (died, gold) pairs are (0, 79), (0, 79), (3, 86), (21, 102), (32, 109), (146, 133).
    """
    seeds = list(seeds)
    if not seeds:
        raise ValueError("risk_curve needs at least one seed")
    points: list[CurvePoint] = []
    for limit in limits:
        r = sweep_rates(seeds, probabilistic=True, exactly_one_wumpus=exactly_one_wumpus, risk_limit=limit)
        death_low, death_high = _cached_interval(r.died, r.caves)
        gold_low, gold_high = _cached_interval(r.gold, r.caves)
        points.append(
            CurvePoint(to_prob(limit, "risk_limit"), r.caves, r.died, r.gold, r.empty, death_low, death_high, gold_low, gold_high)
        )
    return tuple(points)


_INTERVALS: dict = {}
"""Module-level memo of :func:`dsdk.prob.exact_interval` by ``(successes, trials)`` at 95%."""


def _cached_interval(successes: int, trials: int) -> tuple[float, float]:
    key = (successes, trials)
    if key not in _INTERVALS:
        _INTERVALS[key] = exact_interval(successes, trials)
    return _INTERVALS[key]


def frac(x: Fraction) -> str:
    return f"{x.numerator}/{x.denominator}"


def lab_data(seeds=range(1, 301)) -> dict:
    """Everything the page needs, JSON-ready and small.

    ``{"pit_prior": "1/5", "states": {state_key: {"frontier": [[name, pit, wumpus, death], ...], "expected_pits": "a/b"}}, "rates": {"logic": {...}, "probabilistic": {...}}}``
    with every fraction as ``"numerator/denominator"`` text. ``states`` holds one entry for every stuck state (``state_key`` of the stuck percepts) reached by
    EITHER agent on the demo cave and on ``seeded_cave(s)`` for each seed, deduplicated by key; each entry is :func:`stuck_risk` of that state. ``rates`` has
    ``{"caves", "died", "gold", "empty"}`` over ``seeds`` for the logic-only and the probabilistic agent (:func:`sweep_rates`).

    It ALSO has ``"curve"``: the :func:`risk_curve` over ``seeds`` with the default limits, as a list of
    ``{"limit": "a/b", "caves", "died", "gold", "empty", "death": [low, high], "gold_ci": [low, high]}`` (limits as :func:`frac` text, intervals as floats).
    The states table does not need new entries for the curve: a limited agent only reaches stuck states that the unlimited probabilistic agent reaches."""
    states: dict = {}
    for cave in [demo_cave()] + [seeded_cave(s) for s in seeds]:
        for prob in (False, True):
            for st in run_agent(cave, probabilistic=prob).stuck:
                key = state_key(st)
                if key in states:
                    continue
                risk = _cached_stuck_risk(st)
                if risk.status is not Status.KNOWN:
                    raise RuntimeError(risk.reason)
                states[key] = {
                    "frontier": [[name(r.cell), frac(r.pit), frac(r.wumpus), frac(r.death)] for r in risk.value.frontier],
                    "expected_pits": frac(risk.value.expected_pits),
                }
    rates = {}
    for label, prob in (("logic", False), ("probabilistic", True)):
        r = sweep_rates(seeds, probabilistic=prob)
        rates[label] = {"caves": r.caves, "died": r.died, "gold": r.gold, "empty": r.empty}
    curve = [
        {
            "limit": frac(p.limit),
            "caves": p.caves,
            "died": p.died,
            "gold": p.gold,
            "empty": p.empty,
            "death": [p.death_low, p.death_high],
            "gold_ci": [p.gold_low, p.gold_high],
        }
        for p in risk_curve(seeds)
    ]
    return {"pit_prior": frac(PIT_PRIOR), "states": states, "rates": rates, "curve": curve}
