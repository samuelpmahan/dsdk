"""Contract tests: belief updates as dsdk.core ticks. Every update leaves lineage (a DAG of Parts that dsdk.graph can traverse),
is atomic, and impossible evidence never touches the store."""
import pytest

from dsdk.core import AddressOccupiedError, MissingPartError, Part, PxC, ReceiptStatus, Status, TickInProgressError
from dsdk.graph import lineage_graph, reachable, shortest_path, topological_order
from dsdk.logic import And, Const, Not, Or, Var
from dsdk.prob import Belief, belief_history, condition, current_belief, observe, prior_belief, probability, start_series

from prob_helpers import Fr

A, B = Var("A"), Var("B")
BREEZE = Or(A, B)


def fresh(name="s", priors=None):
    store = PxC()
    prior = prior_belief(priors or {"A": 0.2, "B": 0.2})
    start = start_series(store, name, prior)
    return store, prior, start


def snapshot(store):
    return store.entries(), store.receipts()


# ==== Starting a belief series and reading its history ====
def test_start_series_binds_a_raw_part_at_belief_0():
    """Start series binds a raw part at belief 0."""
    store, prior, start = fresh()
    assert store.get("px.s.belief.0") is start
    assert start.composition is None and start.value == prior
    assert belief_history(store, "s") == (start,)
    assert current_belief(store, "s") is start


def test_start_series_is_write_once():
    """Start series is write once."""
    store, prior, _ = fresh()
    with pytest.raises(AddressOccupiedError):
        start_series(store, "s", prior)


@pytest.mark.parametrize("name", ["", "a.b", "a b", "1x", "x\n", "é", "a-b"])
def test_series_names_must_be_identifiers(name):
    """A series name that is empty, has a dot, a space, a leading digit, a newline, a non-ASCII letter or a hyphen is a ValueError."""
    with pytest.raises(ValueError):
        start_series(PxC(), name, prior_belief({"A": 0.5}))


def test_series_argument_types():
    """A non-store, a non-string name, a non-belief or a non-formula evidence is a TypeError."""
    b = prior_belief({"A": 0.5})
    with pytest.raises(TypeError):
        start_series("store", "s", b)
    with pytest.raises(TypeError):
        start_series(PxC(), 1, b)
    with pytest.raises(TypeError):
        start_series(PxC(), "s", "belief")
    with pytest.raises(TypeError):
        observe(PxC(), "s", "A")
    with pytest.raises(TypeError):
        belief_history("store", "s")


def test_history_of_an_unstarted_series_is_missing_part():
    """Asking for the history, the current belief, or an observation of a series that was never started raises the core missing-part error."""
    with pytest.raises(MissingPartError):
        belief_history(PxC(), "nope")
    with pytest.raises(MissingPartError):
        observe(PxC(), "nope", A)
    with pytest.raises(MissingPartError):
        current_belief(PxC(), "nope")


# ==== Each observation is a tick that leaves addresses, values and lineage ====
def test_observe_returns_known_with_the_new_belief_part_bound_at_belief_1():
    """Observe returns known with the new belief part bound at belief 1."""
    store, prior, start = fresh()
    j = observe(store, "s", BREEZE)
    assert j.status is Status.KNOWN
    new = j.value
    assert isinstance(new, Part) and store.get("px.s.belief.1") is new
    assert new.value == condition(prior, BREEZE)
    assert belief_history(store, "s") == (start, new) and current_belief(store, "s") is new


def test_the_headline_wumpus_update_through_the_store():
    """Observing the breeze through the store gives a belief in which the pit at A has probability 5/9."""
    store, _, _ = fresh()
    new = observe(store, "s", BREEZE).value
    assert probability(new.value, A).value == Fr(5, 9)


def test_evidence_is_recorded_as_its_own_part():
    """The observed formula is stored as its own composed part at the evidence address."""
    store, _, _ = fresh()
    observe(store, "s", BREEZE)
    ev = store.get("px.s.evidence.1")
    assert ev.value == BREEZE and ev.composition is not None


def test_belief_part_composition_names_prev_and_evidence_by_identity():
    """The new belief's composition names its inputs prev and evidence, and they are the very Part objects of the previous belief and the evidence."""
    store, _, start = fresh()
    new = observe(store, "s", BREEZE).value
    inputs = dict(new.composition.inputs)
    assert list(inputs) == ["prev", "evidence"]
    assert inputs["prev"] is start
    assert inputs["evidence"] is store.get("px.s.evidence.1")
    assert dict(inputs["evidence"].composition.inputs).keys() == {"formula"}


def test_calculation_parts_are_shared_across_updates():
    """Every belief update uses the same calculation Part, and every evidence record uses another one shared by all updates."""
    store, _, _ = fresh()
    b1 = observe(store, "s", BREEZE).value
    b2 = observe(store, "s", Not(Var("A"))).value
    assert b1.composition.calculation is b2.composition.calculation
    e1, e2 = store.get("px.s.evidence.1"), store.get("px.s.evidence.2")
    assert e1.composition.calculation is e2.composition.calculation
    assert e1.composition.calculation is not b1.composition.calculation


def test_two_updates_equal_conditioning_on_the_conjunction():
    """Two updates equal conditioning on the conjunction."""
    store, prior, _ = fresh()
    observe(store, "s", BREEZE)
    observe(store, "s", Not(A))
    assert current_belief(store, "s").value == condition(prior, And(BREEZE, Not(A)))
    assert probability(current_belief(store, "s").value, B).value == 1


def test_receipts_two_produced_per_update_with_the_tick_id():
    """Each update records two PRODUCED receipts, evidence then belief, both tagged with the tick id name.observe.k."""
    store, _, _ = fresh()
    observe(store, "s", BREEZE)
    observe(store, "s", Not(A))
    rs = store.receipts()
    assert len(rs) == 4 and all(r.status is ReceiptStatus.PRODUCED for r in rs)
    assert [r.tick for r in rs] == ["s.observe.1", "s.observe.1", "s.observe.2", "s.observe.2"]
    assert [r.into for r in rs] == ["px.s.evidence.1", "px.s.belief.1", "px.s.evidence.2", "px.s.belief.2"]


def test_binding_order_and_no_stray_addresses():
    """After one update the store holds exactly the starting belief, the evidence and the new belief, in that order."""
    store, _, _ = fresh()
    observe(store, "s", BREEZE)
    assert [a for a, _ in store.entries()] == ["px.s.belief.0", "px.s.evidence.1", "px.s.belief.1"]


def test_lineage_dag_reaches_every_earlier_belief_and_every_evidence():
    """The lineage graph of the newest belief contains every earlier belief and every piece of evidence, the shortest path is the chain of beliefs, and lineage points forward only."""
    store, _, start = fresh()
    b1 = observe(store, "s", BREEZE).value
    b2 = observe(store, "s", Not(A)).value
    g = lineage_graph(b2)
    assert g.directed and g.closed_world
    for part in (start, b1, store.get("px.s.evidence.1"), store.get("px.s.evidence.2")):
        assert g.has_node(part)
    assert reachable(g, start, b2).status is Status.KNOWN and reachable(g, start, b2).value is True
    assert shortest_path(g, start, b2) == (start, b1, b2), "the prev chain is the shortest lineage path"
    assert reachable(g, b2, start).value is False, "lineage points forward only"
    order = topological_order(g)
    assert order.index(start) < order.index(b1) < order.index(b2)


def test_lineage_distinguishes_branches_of_evidence():
    """The lineage graph's edges are labelled prev, evidence and formula, so a reader can tell the branches apart."""
    store, _, _ = fresh()
    observe(store, "s", BREEZE)
    g = lineage_graph(store.get("px.s.belief.1"))
    labels = {e.label for e in g.edges}
    assert {"prev", "evidence", "formula"} <= {l for lab in labels for l in lab.split(",")}


def test_two_series_in_one_store_do_not_interfere():
    """Two independent belief series in the same store keep their own histories and results."""
    store = PxC()
    start_series(store, "x", prior_belief({"A": 0.2, "B": 0.2}))
    start_series(store, "y", prior_belief({"A": 0.5, "B": 0.5}))
    observe(store, "x", BREEZE)
    observe(store, "y", BREEZE)
    observe(store, "x", Not(A))
    assert len(belief_history(store, "x")) == 3 and len(belief_history(store, "y")) == 2
    assert probability(current_belief(store, "y").value, A).value == Fr(2, 3)


def test_stored_belief_cannot_be_mutated_through_a_reference():
    """Reading a stored belief twice gives equal values, so the store's state is not altered through the value."""
    store, prior, _ = fresh()
    first = store.get("px.s.belief.0").value
    assert first == prior
    assert store.get("px.s.belief.0").value == prior


# ==== Impossible or unmodelled evidence leaves the store untouched ====
def test_impossible_evidence_is_invalid_and_leaves_no_trace():
    """Contradictory or zero-probability evidence gives INVALID, and afterwards the store's entries and receipts are exactly what they were."""
    store, _, start = fresh()
    observe(store, "s", BREEZE)
    before = snapshot(store)
    for e in (And(A, Not(A)), Const(False), And(Not(A), Not(B))):
        j = observe(store, "s", e)
        assert j.status is Status.INVALID and j.value is None and j.reason.strip()
        assert "impossible" in j.reason
    assert snapshot(store) == before, "no Part, no receipt, no tick"


def test_evidence_contradicting_the_current_belief_is_impossible_even_if_logically_satisfiable():
    """After seeing 'A', the evidence 'not A' is satisfiable in logic but has probability zero in the CURRENT belief."""
    store, _, _ = fresh()
    observe(store, "s", A)
    j = observe(store, "s", Not(A))
    assert j.status is Status.INVALID
    assert len(belief_history(store, "s")) == 2


def test_the_series_keeps_working_after_a_rejected_observation():
    """After an INVALID observation the series accepts the next valid one at the same index, and no rejected try consumed an index."""
    store, prior, _ = fresh()
    assert observe(store, "s", And(A, Not(A))).status is Status.INVALID
    assert observe(store, "s", BREEZE).status is Status.KNOWN
    assert [t for t in {r.tick for r in store.receipts()}] == ["s.observe.1"], "the rejected try did not consume index 1"


def test_zero_prior_makes_every_observation_impossible():
    """With prior 0 for both pits, observing the breeze is INVALID."""
    store = PxC()
    start_series(store, "z", prior_belief({"A": 0, "B": 0}))
    assert observe(store, "z", BREEZE).status is Status.INVALID


def test_a_dead_starting_belief_is_invalid_for_everything():
    """A series that starts from a belief of zero total weight answers INVALID to any observation."""
    store = PxC()
    start_series(store, "d", condition(prior_belief({"A": 0.5}), Const(False)))
    assert observe(store, "d", Const(True)).status is Status.INVALID


def test_unmodelled_evidence_is_unknown_and_leaves_no_trace():
    """Evidence mentioning a variable the belief does not model is UNKNOWN and leaves the store untouched."""
    store, _, _ = fresh()
    before = snapshot(store)
    j = observe(store, "s", And(A, Var("Z")))
    assert j.status is Status.UNKNOWN and j.reason == "unmodelled variables: Z"
    assert snapshot(store) == before


# ==== Updates are atomic and respect open ticks ====
def test_a_failing_compose_rolls_the_whole_update_back():
    """If an address needed by the update is already taken, the tick rolls back: no new belief is bound, no new entries or receipts exist, and the exception propagates."""
    store, _, _ = fresh()
    store.set("px.s.evidence.1", Part("squatter"))
    before = snapshot(store)
    with pytest.raises(AddressOccupiedError):
        observe(store, "s", BREEZE)
    assert not store.has("px.s.belief.1")
    assert snapshot(store) == before
    assert len(belief_history(store, "s")) == 1


def test_observe_inside_an_open_tick_raises_tick_in_progress():
    """Observing while another tick is open raises the core tick-in-progress error and binds nothing."""
    store, _, _ = fresh()
    with store.tick("outer"):
        with pytest.raises(TickInProgressError):
            observe(store, "s", BREEZE)
    assert not store.has("px.s.belief.1")


def test_long_series_keeps_indices_dense_and_equals_one_big_condition():
    """Four successive observations give belief indices 0 to 4 with no gaps, equal conditioning once on the conjunction of all four, and the first belief reaches the last in the lineage graph."""
    store, prior, _ = fresh(priors={"A": Fr(1, 2), "B": Fr(1, 2), "C": Fr(1, 2)})
    evs = [Or(A, B), Not(A), Or(Var("C"), A), Or(Var("C"), Not(B))]
    for e in evs:
        assert observe(store, "s", e).status is Status.KNOWN
    assert [a for a, _ in store.entries() if ".belief." in a] == [f"px.s.belief.{i}" for i in range(5)]
    big = evs[0]
    for e in evs[1:]:
        big = And(big, e)
    assert current_belief(store, "s").value == condition(prior, big)
    g = lineage_graph(current_belief(store, "s"))
    assert shortest_path(g, store.get("px.s.belief.0"), store.get("px.s.belief.4")) is not None
