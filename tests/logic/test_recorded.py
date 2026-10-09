"""Contract tests for dsdk.logic.recorded: a checked proof recorded in the kernel store (one tick, one Part per step) and replayed from the lineage.

Layers: dsdk.logic (steps, rules, the checker) x dsdk.core (PxC, Part, tick, receipts). The independent expectations are the checker itself
(`dsdk.logic.check` must report the same first bad step and the same reason as the recording does) and hand-written proofs.
"""
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from dsdk.core import AddressOccupiedError, Part, PxC, ReceiptStatus, Status, TickInProgressError
from dsdk.logic import And, Implies, Not, Or, Rule, Step, Var, check
from dsdk.logic.recorded import ProofStepError, RecordedProof, StepCalculation, record_proof, replay_proof

p, q, r = Var("p"), Var("q"), Var("r")
PREMISES = [p, Implies(p, q), Implies(q, r)]
CHAIN = [
    Step(p, Rule.PREMISE, ()),
    Step(Implies(p, q), Rule.PREMISE, ()),
    Step(q, Rule.MODUS_PONENS, (1, 0)),
    Step(Implies(q, r), Rule.PREMISE, ()),
    Step(r, Rule.MODUS_PONENS, (3, 2)),
]


def known(j):
    assert j.status is Status.KNOWN, j
    return j.value


def snap(store):
    return store.entries(), store.receipts()


# ==== Recording a valid proof binds one Part per step in one tick ====
def test_a_valid_chain_is_recorded_one_part_per_step_at_consecutive_addresses():
    """Recording the five-step chain p, p implies q, q, q implies r, r binds px.c.0 to px.c.4, each Part's value is that step's formula, and the result lists the same Part objects in order."""
    store = PxC()
    rec = known(record_proof(store, "c", CHAIN, PREMISES))
    assert isinstance(rec, RecordedProof) and rec.prefix == "c" and len(rec.parts) == 5
    assert [a for a, _ in store.entries()] == [f"px.c.{i}" for i in range(5)]
    for i, step in enumerate(CHAIN):
        assert store.get(f"px.c.{i}") is rec.parts[i] and rec.parts[i].value == step.formula
    assert rec.conclusion is rec.parts[-1] and rec.conclusion.value == r


def test_every_step_is_a_composed_part_with_a_remembered_rule_and_exactly_the_cited_inputs():
    """Premise steps are composed too (no inputs); a modus-ponens step has exactly two inputs c0, c1 that are the very Parts it cites, in cite order; each calculation remembers its rule and formula."""
    store = PxC()
    rec = known(record_proof(store, "c", CHAIN, PREMISES))
    for i, (step, part) in enumerate(zip(CHAIN, rec.parts)):
        comp = part.composition
        assert comp is not None
        calc = comp.calculation.value
        assert isinstance(calc, StepCalculation) and calc.rule is step.rule and calc.formula == step.formula
        assert list(comp.inputs) == [f"c{j}" for j in range(len(step.cites))]
        assert all(comp.inputs[f"c{j}"] is rec.parts[c] for j, c in enumerate(step.cites))
    assert dict(rec.parts[2].composition.inputs).keys() == {"c0", "c1"}


def test_the_whole_proof_is_one_tick_with_one_produced_receipt_per_step():
    """The store records exactly one PRODUCED receipt per step, all tagged with the tick id "proof.c", in step order."""
    store = PxC()
    known(record_proof(store, "c", CHAIN, PREMISES))
    rs = store.receipts()
    assert [r.into for r in rs] == [f"px.c.{i}" for i in range(5)]
    assert all(r.status is ReceiptStatus.PRODUCED and r.tick == "proof.c" for r in rs)


def test_each_step_gets_its_own_calculation_part():
    """Every step has its own calculation Part (the closure differs by step), so no two steps share a calculation."""
    rec = known(record_proof(PxC(), "c", CHAIN, PREMISES))
    calcs = [pt.composition.calculation for pt in rec.parts]
    assert len({id(c) for c in calcs}) == 5


def test_and_or_double_negation_and_tollens_steps_record_too():
    """Proofs using and-introduction, and-elimination, or-introduction, double-negation elimination and modus tollens are recorded and replayed, including a step that cites the same Part twice."""
    a = Var("a")
    proof = [
        Step(a, Rule.PREMISE, ()), Step(And(a, a), Rule.AND_INTRO, (0, 0)), Step(a, Rule.AND_ELIM_LEFT, (1,)), Step(a, Rule.AND_ELIM_RIGHT, (1,)),
        Step(Or(a, Var("z")), Rule.OR_INTRO_LEFT, (0,)), Step(Or(Var("z"), a), Rule.OR_INTRO_RIGHT, (0,)),
        Step(Not(Not(a)), Rule.PREMISE, ()), Step(a, Rule.DOUBLE_NEGATION_ELIM, (6,)),
        Step(Implies(a, Var("b")), Rule.PREMISE, ()), Step(Not(Var("b")), Rule.PREMISE, ()), Step(Not(a), Rule.MODUS_TOLLENS, (8, 9)),
    ]
    prem = [a, Not(Not(a)), Implies(a, Var("b")), Not(Var("b"))]
    assert check(proof, prem).ok
    store = PxC()
    known(record_proof(store, "m", proof, prem))
    assert known(replay_proof(store, "m")) == tuple(proof)


# ==== Replay rebuilds the proof from the lineage alone ====
def test_replay_returns_the_original_steps_and_the_checker_accepts_them():
    """Replaying the recorded chain gives a tuple of Steps equal to the original proof, and dsdk.logic.check accepts that rebuilt proof against the original premises."""
    store = PxC()
    known(record_proof(store, "c", CHAIN, PREMISES))
    steps = known(replay_proof(store, "c"))
    assert steps == tuple(CHAIN) and check(steps, PREMISES).ok


def test_replay_of_an_unknown_prefix_is_not_observed():
    """Asking for a proof that was never recorded is NOT_OBSERVED, not an error and not an empty proof."""
    j = replay_proof(PxC(), "nothing")
    assert j.status is Status.NOT_OBSERVED and "nothing" in j.reason


def test_replay_rejects_a_step_that_is_a_raw_part():
    """A raw Part (no composition) at a step address, put there by someone else, is INVALID: the step was not produced by a proof step."""
    store = PxC()
    store.set("px.f.0", Part(p))
    j = replay_proof(store, "f")
    assert j.status is Status.INVALID and j.reason.startswith("step 0 was not produced by a proof step")


def test_replay_rejects_a_composed_part_made_by_another_calculation():
    """A Part composed by an ordinary function is not a proof step, even if its value is a formula."""
    store = PxC()
    store.compose("px.f.0", Part(lambda inputs: p))
    assert replay_proof(store, "f").reason.startswith("step 0 was not produced by a proof step")


def test_replay_reports_the_first_bad_step_of_a_mixed_chain():
    """A valid first step followed by a raw Part is reported at step 1."""
    store = PxC()
    store.compose("px.f.0", Part(StepCalculation(Rule.PREMISE, p, (p,))))
    store.set("px.f.1", Part(q))
    assert replay_proof(store, "f").reason.startswith("step 1 was not produced by a proof step")


def test_replay_rejects_a_step_that_cites_a_part_from_another_proof():
    """A step whose input is a Part of a different proof (not an earlier step of the same prefix) is INVALID."""
    store = PxC()
    other = known(record_proof(store, "a", [Step(Not(Not(p)), Rule.PREMISE, ())], [Not(Not(p))]))
    store.compose("px.b.0", Part(StepCalculation(Rule.DOUBLE_NEGATION_ELIM, p, ())), {"c0": other.parts[0]})
    j = replay_proof(store, "b")
    assert j.status is Status.INVALID and "not an earlier step of this proof" in j.reason


def test_replay_rejects_steps_that_disagree_about_the_premises():
    """If two steps remember different premise lists, the replay is INVALID instead of guessing which is right."""
    store = PxC()
    store.compose("px.d.0", Part(StepCalculation(Rule.PREMISE, p, (p,))))
    store.compose("px.d.1", Part(StepCalculation(Rule.PREMISE, q, (q,))))
    assert replay_proof(store, "d").reason.startswith("steps disagree about the premises")


# ==== A failed check rolls the whole tick back ====
def tampered():
    s = list(CHAIN)
    yield "swapped citations", [*s[:2], Step(q, Rule.MODUS_PONENS, (0, 1)), *s[3:]]
    yield "wrong conclusion", [*s[:2], Step(Var("zz"), Rule.MODUS_PONENS, (1, 0)), *s[3:]]
    yield "forward citation", [*s[:2], Step(q, Rule.MODUS_PONENS, (1, 7)), *s[3:]]
    yield "negative citation", [*s[:2], Step(q, Rule.MODUS_PONENS, (-1, 0)), *s[3:]]
    yield "invented premise", [Step(Var("zz"), Rule.PREMISE, ()), *s[1:]]
    yield "affirming the consequent", [*s[:2], Step(p, Rule.MODUS_PONENS, (1, 2)), *s[3:]]
    yield "wrong number of cites", [*s[:2], Step(q, Rule.MODUS_PONENS, (1,)), *s[3:]]
    yield "late failure", [*s[:4], Step(q, Rule.MODUS_PONENS, (3, 2))]


@pytest.mark.parametrize("name,proof", list(tampered()), ids=[n for n, _ in tampered()])
def test_an_invalid_proof_is_invalid_with_the_checkers_reason_and_binds_nothing(name, proof):
    """For each corrupted chain, record_proof answers INVALID with exactly the reason dsdk.logic.check gives (same step number, same wording), and the store has no binding and no tick left open."""
    store = PxC()
    expected = check(proof, PREMISES)
    assert not expected.ok
    j = record_proof(store, "c", proof, PREMISES)
    assert j.status is Status.INVALID and j.value is None and j.reason == expected.reason
    assert store.entries() == ()
    assert not store.has("px.c.0")
    assert known(record_proof(store, "c", CHAIN, PREMISES)).prefix == "c", "the prefix is still free after a rolled-back attempt"


def test_the_rolled_back_attempt_leaves_failed_receipts_for_the_steps_already_composed():
    """When step 2 is bad, steps 0 and 1 were composed and then rolled back, so the store shows two FAILED receipts tagged with the tick id and nothing bound."""
    store = PxC()
    bad = [*CHAIN[:2], Step(Var("zz"), Rule.MODUS_PONENS, (1, 0)), *CHAIN[3:]]
    assert record_proof(store, "c", bad, PREMISES).status is Status.INVALID
    rs = store.receipts()
    assert [r.into for r in rs] == ["px.c.0", "px.c.1"]
    assert all(r.status is ReceiptStatus.FAILED and r.tick == "proof.c" and isinstance(r.error, ProofStepError) for r in rs)
    assert store.entries() == ()


def test_a_bad_first_step_fails_before_anything_is_composed():
    """If step 0 is not a premise nothing is attempted: no bindings and no receipts."""
    store = PxC()
    j = record_proof(store, "c", [Step(Var("zz"), Rule.PREMISE, ())], PREMISES)
    assert j.status is Status.INVALID and j.reason == "step 0 (premise): formula is not one of the premises"
    assert snap(store) == ((), ())


def test_an_address_already_taken_rolls_the_whole_proof_back_and_raises():
    """If one of the step addresses is already bound, the store's AddressOccupiedError propagates and none of the proof's other steps stay bound."""
    store = PxC()
    store.set("px.c.3", Part("squatter"))
    with pytest.raises(AddressOccupiedError):
        record_proof(store, "c", CHAIN, PREMISES)
    assert [a for a, _ in store.entries()] == ["px.c.3"]


def test_the_same_prefix_cannot_be_recorded_twice():
    """Recording is write-once: a second proof under the same prefix raises AddressOccupiedError and leaves the first intact and replayable."""
    store = PxC()
    known(record_proof(store, "c", CHAIN, PREMISES))
    before = snap(store)
    with pytest.raises(AddressOccupiedError):
        record_proof(store, "c", CHAIN, PREMISES)
    assert snap(store)[0] == before[0] and known(replay_proof(store, "c")) == tuple(CHAIN)


def test_recording_inside_an_open_tick_raises_tick_in_progress():
    """A record request while another tick is open raises the core TickInProgressError and binds nothing."""
    store = PxC()
    with store.tick("outer"):
        with pytest.raises(TickInProgressError):
            record_proof(store, "c", CHAIN, PREMISES)
    assert store.entries() == ()


def test_a_step_calculation_enforces_its_own_rule_even_outside_record_proof():
    """Composing a modus-ponens StepCalculation with the wrong inputs fails with ProofStepError, records a FAILED receipt, and leaves the address free: the rule is enforced where the Part is made."""
    store = PxC()
    a = store.compose("px.x.0", Part(StepCalculation(Rule.PREMISE, p, (p, Implies(p, q)))))
    b = store.compose("px.x.1", Part(StepCalculation(Rule.PREMISE, Implies(p, q), (p, Implies(p, q)))))
    with pytest.raises(ProofStepError):
        store.compose("px.x.2", Part(StepCalculation(Rule.MODUS_PONENS, q, ())), {"c0": a, "c1": b})  # implication must come first
    assert not store.has("px.x.2") and store.receipts()[-1].status is ReceiptStatus.FAILED
    ok = store.compose("px.x.2", Part(StepCalculation(Rule.MODUS_PONENS, q, ())), {"c0": b, "c1": a})
    assert ok.value == q


def test_a_step_calculation_rejects_a_claim_that_does_not_follow():
    """A premise step claiming a formula that is not among the premises, and a modus-ponens step claiming the wrong conclusion from correct inputs, are both rejected with ProofStepError when composed."""
    store = PxC()
    a = store.compose("px.y.0", Part(StepCalculation(Rule.PREMISE, p, (p, Implies(p, q)))))
    b = store.compose("px.y.1", Part(StepCalculation(Rule.PREMISE, Implies(p, q), (p, Implies(p, q)))))
    with pytest.raises(ProofStepError):
        store.compose("px.y.2", Part(StepCalculation(Rule.PREMISE, Var("zz"), (p,))))
    with pytest.raises(ProofStepError):
        store.compose("px.y.2", Part(StepCalculation(Rule.MODUS_PONENS, r, ())), {"c0": b, "c1": a})
    assert not store.has("px.y.2")


def test_an_empty_proof_is_invalid_and_touches_nothing():
    """An empty proof is INVALID ("empty proof") and leaves no receipt, even though dsdk.logic.check calls the empty proof valid, because nothing could be replayed."""
    store = PxC()
    j = record_proof(store, "c", [], PREMISES)
    assert j.status is Status.INVALID and j.reason.startswith("empty proof") and snap(store) == ((), ())


# ==== Arguments ====
@pytest.mark.parametrize("prefix", ["", "a.b", "a b", "1x", "x\n", "é", "a-b"])
def test_prefixes_must_be_identifiers(prefix):
    """A prefix that is empty, has a dot or space, starts with a digit, ends with a newline, is not ASCII or has a hyphen is a ValueError for both functions."""
    with pytest.raises(ValueError):
        record_proof(PxC(), prefix, CHAIN, PREMISES)
    with pytest.raises(ValueError):
        replay_proof(PxC(), prefix)


def test_argument_types():
    """A non-store, a non-string prefix, a proof that is not a sequence of Steps (including a bare string and None), and premises that are not formulas are TypeErrors."""
    with pytest.raises(TypeError):
        record_proof("store", "c", CHAIN, PREMISES)
    with pytest.raises(TypeError):
        record_proof(PxC(), 3, CHAIN, PREMISES)
    for bad in ("proof", None, [CHAIN[0], "step"], 5):
        with pytest.raises(TypeError):
            record_proof(PxC(), "c", bad, PREMISES)
    with pytest.raises(TypeError):
        record_proof(PxC(), "c", CHAIN, [p, "not a formula"])
    with pytest.raises(TypeError):
        replay_proof("store", "c")


def test_premises_may_be_any_iterable_consumed_once():
    """A generator of premises works (it is consumed once) and the premises are remembered by the steps."""
    store = PxC()
    known(record_proof(store, "c", CHAIN, (f for f in PREMISES)))
    assert known(replay_proof(store, "c")) == tuple(CHAIN)


def test_two_proofs_in_one_store_do_not_interfere():
    """Two proofs under different prefixes are independent: each replays to its own steps."""
    store = PxC()
    other = [Step(p, Rule.PREMISE, ()), Step(Or(p, q), Rule.OR_INTRO_LEFT, (0,))]
    known(record_proof(store, "a", CHAIN, PREMISES))
    known(record_proof(store, "b", other, [p]))
    assert known(replay_proof(store, "a")) == tuple(CHAIN) and known(replay_proof(store, "b")) == tuple(other)


# ==== Random valid proofs round trip ====
names = ["a", "b", "c"]


@st.composite
def valid_proofs(draw):
    premises = [Var("a"), Implies(Var("a"), Var("b")), Implies(Var("b"), Var("c")), And(Var("a"), Var("c")), Not(Not(Var("b")))]
    steps = [Step(f, Rule.PREMISE, ()) for f in draw(st.lists(st.sampled_from(premises), min_size=1, max_size=4))]
    for _ in range(draw(st.integers(0, 6))):
        fs = [s.formula for s in steps]
        moves = []
        for i, f in enumerate(fs):
            if isinstance(f, And):
                moves += [Step(f.left, Rule.AND_ELIM_LEFT, (i,)), Step(f.right, Rule.AND_ELIM_RIGHT, (i,))]
            if isinstance(f, Not) and isinstance(f.operand, Not):
                moves.append(Step(f.operand.operand, Rule.DOUBLE_NEGATION_ELIM, (i,)))
            moves.append(Step(Or(f, Var("z")), Rule.OR_INTRO_LEFT, (i,)))
            for j, g in enumerate(fs):
                if isinstance(f, Implies) and f.left == g:
                    moves.append(Step(f.right, Rule.MODUS_PONENS, (i, j)))
                moves.append(Step(And(f, g), Rule.AND_INTRO, (i, j)))
        steps.append(draw(st.sampled_from(moves)))
    return steps, premises


@settings(max_examples=60, deadline=None)
@given(valid_proofs())
def test_random_valid_proofs_record_and_replay_to_themselves(case):
    """For random valid proofs built from the nine rules, the recording succeeds, every step's Part value is its formula, and the replay returns exactly the original steps."""
    proof, premises = case
    assert check(proof, premises).ok
    store = PxC()
    rec = known(record_proof(store, "r", proof, premises))
    assert [pt.value for pt in rec.parts] == [s.formula for s in proof]
    assert known(replay_proof(store, "r")) == tuple(proof)


@settings(max_examples=60, deadline=None)
@given(valid_proofs(), st.data())
def test_random_corruptions_are_rejected_with_the_checkers_verdict(case, data):
    """Corrupting one step of a random valid proof (a different formula or a different rule) gives the same verdict from record_proof as from dsdk.logic.check: INVALID with the same reason when check rejects it, KNOWN when it happens to still be valid."""
    proof, premises = case
    i = data.draw(st.integers(0, len(proof) - 1))
    s = proof[i]
    other = data.draw(st.sampled_from([Step(Var("zz"), s.rule, s.cites), Step(s.formula, Rule.MODUS_TOLLENS, s.cites), Step(s.formula, s.rule, (0,) if s.cites != (0,) else ())]))
    bad = [*proof[:i], other, *proof[i + 1:]]
    expected = check(bad, premises)
    store = PxC()
    j = record_proof(store, "r", bad, premises)
    if expected.ok:
        assert j.status is Status.KNOWN
    else:
        assert j.status is Status.INVALID and j.reason == expected.reason and store.entries() == ()
