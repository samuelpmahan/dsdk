"""Contract tests for dsdk.core.PxC: write-once Parts, compose, lineage, receipts, atomic tick.

Sections: Part | addresses | set/get/has/entries | compose happy path | compose preflight |
compose failure | receipts | lineage | (tick sections: names contain 'tick' -- the T03 task runs `-k tick`).
"""
import dataclasses
import threading

import pytest
from hypothesis import given, strategies as st

from dsdk.core import (
    AddressOccupiedError,
    Composition,
    MissingPartError,
    Part,
    PxC,
    PxCError,
    Receipt,
    ReceiptStatus,
    TickInProgressError,
)


@pytest.fixture
def store():
    return PxC()


class Spy:
    """A calculation that counts how often it ran and what it received."""

    def __init__(self, result=0):
        self.calls = []
        self.result = result

    def __call__(self, values):
        self.calls.append(values)
        return self.result


def add_x(values):
    return values["x"] + values.get("y", 0)


# =============================== Part =======================================
def test_part_directly_made_has_no_composition():
    """A Part made directly is a leaf of the lineage DAG: composition must be None."""
    assert Part(3).composition is None, "directly-made Part must have composition None"


def test_part_holds_none_as_a_value():
    """None is a legitimate value (distinct from 'no Part'); the wrapper must not treat it as absent."""
    assert Part(None).value is None


def test_part_captures_value_at_construction():
    """Mutating the original after wrapping must not change the Part (else lineage values drift)."""
    original = {"a": [1, 2]}
    p = Part(original)
    original["a"].append(3)
    assert p.value == {"a": [1, 2]}, "Part must deep-copy on construction"


def test_part_value_is_a_fresh_copy_per_access():
    """Mutating a returned value must not change the Part (attack: mutation through a reference)."""
    p = Part({"a": [1]})
    first = p.value
    first["a"].append(99)
    first["new"] = 1
    assert p.value == {"a": [1]}, "Part.value must hand out a fresh deep copy each time"
    assert p.value is not p.value, "two accesses must not alias"


def test_part_preserves_cyclic_structure():
    """Deep copy must handle cycles and keep their shape (naive recursive copy would recurse forever)."""
    cyc = [1]
    cyc.append(cyc)
    out = Part(cyc).value
    assert out[0] == 1 and out[1] is out, "cycle must be preserved inside the copy"
    assert out is not cyc


def test_part_uncopyable_value_raises_typeerror():
    """If deepcopy fails the error must surface (not be swallowed into a half-built Part)."""
    with pytest.raises(TypeError):
        Part(threading.Lock())


def test_part_keeps_callables_by_reference():
    """Calculations are behaviour, not data: a stateful callable object must keep its identity (copying it would orphan its state)."""
    spy = Spy(1)
    assert Part(spy).value is spy, "callable values must be stored and returned as the same object"
    assert Part(len).value is len


def test_part_is_immutable():
    """Parts are shared across lineage; any attribute assignment must raise AttributeError."""
    p = Part(1)
    for name in ("value", "composition", "brand_new"):
        with pytest.raises(AttributeError):
            setattr(p, name, 5)


def test_part_equality_is_identity():
    """Two Parts with equal values are different lineage nodes; graphs (A5) rely on identity."""
    a, b = Part(1), Part(1)
    assert a != b, "equal values must not make Parts equal"
    assert a == a
    assert len({a, b}) == 2, "Parts must be hashable by identity"


# =============================== addresses ==================================
OPS = {
    "set": lambda s, a: s.set(a, Part(1)),
    "get": lambda s, a: s.get(a),
    "has": lambda s, a: s.has(a),
    "compose_into": lambda s, a: s.compose(a, Part(lambda v: 1)),
}


@pytest.mark.parametrize("op", sorted(OPS))
@pytest.mark.parametrize("addr", ["", "a", "px", "px.", "fn.", "sc.", "PX.a", "x.a", " px.a", "px_a", "px:a"])
def test_malformed_address_string_is_valueerror(store, op, addr):
    """Addresses must be '<px|fn|sc>.<non-empty>'; every operation must reject anything else with ValueError."""
    with pytest.raises(ValueError):
        OPS[op](store, addr)


@pytest.mark.parametrize("op", sorted(OPS))
@pytest.mark.parametrize("addr", [None, 5, b"px.a", ("px.a",), ["px.a"]])
def test_non_string_address_is_typeerror(store, op, addr):
    """A non-str address is a type error, not a value error."""
    with pytest.raises(TypeError):
        OPS[op](store, addr)


@pytest.mark.parametrize("addr", ["px.a", "fn.f", "sc.tmp", "px.a.b.c", "px. ", "px.é"])
def test_wellformed_addresses_accepted(store, addr):
    """Any non-empty remainder after a known namespace is legal (case-sensitive prefix)."""
    store.set(addr, Part(lambda v: 1) if addr.startswith("fn.") else Part(1))
    assert store.has(addr)


def test_invalid_set_leaves_store_empty(store):
    """A rejected set must have no side effects."""
    with pytest.raises(ValueError):
        store.set("nope", Part(1))
    assert store.entries() == () and store.receipts() == ()


# =============================== set/get/has/entries ========================
def test_set_returns_same_part_and_get_returns_same_object(store):
    """Parts are identities: set returns its argument and get returns that very object every time."""
    p = Part(7)
    assert store.set("px.a", p) is p, "set must return the Part it was given"
    assert store.get("px.a") is p and store.get("px.a") is p, "get must return the same Part object"


def test_set_rejects_raw_values(store):
    """Only Parts may be bound; a raw value would have no lineage slot. The address must remain free."""
    with pytest.raises(TypeError):
        store.set("px.a", 5)
    assert not store.has("px.a")
    store.set("px.a", Part(5))  # still free


def test_set_into_occupied_address_raises_and_keeps_original(store):
    """Write-once: there is no replacement, even with the same Part or an equal value."""
    p = Part(1)
    store.set("px.a", p)
    for other in (Part(2), Part(1), p):
        with pytest.raises(AddressOccupiedError):
            store.set("px.a", other)
    assert store.get("px.a") is p, "original binding must survive failed overwrites"
    assert len(store.entries()) == 1


def test_occupied_error_is_a_pxc_error(store):
    """Callers can catch the whole family with PxCError."""
    store.set("px.a", Part(1))
    with pytest.raises(PxCError):
        store.set("px.a", Part(1))


def test_get_missing_raises_missingpart_which_is_keyerror(store):
    """Missing is distinguishable from None and can be caught as KeyError."""
    with pytest.raises(MissingPartError):
        store.get("px.nope")
    with pytest.raises(KeyError):
        store.get("px.nope")


def test_has_reflects_bindings_and_never_creates(store):
    """has must be a pure query."""
    assert store.has("px.a") is False
    assert store.has("px.a") is False and store.entries() == ()
    store.set("px.a", Part(None))
    assert store.has("px.a") is True, "a bound Part holding None still counts as present"


def test_fn_namespace_requires_callable(store):
    """The one enforced namespace rule: fn.* addresses hold callables. Rejection leaves the address free."""
    with pytest.raises(TypeError):
        store.set("fn.bad", Part(5))
    assert not store.has("fn.bad")
    store.set("fn.ok", Part(lambda v: 1))


def test_other_namespaces_are_not_restricted(store):
    """px.* and sc.* accept any value (including callables): only fn.* is policed."""
    store.set("px.f", Part(lambda v: 1))
    store.set("sc.n", Part(5))
    store.set("sc.l", Part([1]))
    assert len(store.entries()) == 3


def test_entries_in_binding_order_as_immutable_snapshot(store):
    """entries() is a tuple of (address, Part) in binding order, unaffected by later bindings."""
    a, b = Part(1), Part(2)
    store.set("px.b", b)
    store.set("px.a", a)
    snap = store.entries()
    assert isinstance(snap, tuple) and snap == (("px.b", b), ("px.a", a)), "binding order, not sorted order"
    store.set("px.c", Part(3))
    assert len(snap) == 2, "earlier snapshot must not grow"
    assert len(store.entries()) == 3


# =============================== compose: happy path ========================
def test_compose_binds_and_returns_the_output_part(store):
    """compose runs the calculation on named inputs and binds the result Part at `into`."""
    store.set("fn.add", Part(add_x))
    store.set("px.x", Part(2))
    out = store.compose("px.y", "fn.add", {"x": "px.x"})
    assert out.value == 2 and store.get("px.y") is out, "compose must return the very Part it bound"


def test_compose_accepts_parts_or_addresses_for_calculation_and_inputs(store):
    """References may be string addresses or Part objects (unbound Parts included)."""
    calc, x = Part(add_x), Part(10)
    out = store.compose("px.o", calc, {"x": x, "y": Part(5)})
    assert out.value == 15
    store.set("fn.add", calc)
    assert store.compose("px.o2", "fn.add", {"x": x}).value == 10


def test_compose_calls_calculation_once_with_one_dict_in_caller_order(store):
    """The calculation receives exactly one positional dict {name: value}, in the caller's input order."""
    spy = Spy(1)
    store.compose("px.o", Part(spy), {"b": Part(1), "a": Part(2)})
    assert len(spy.calls) == 1, "calculation must run exactly once"
    assert type(spy.calls[0]) is dict and list(spy.calls[0].items()) == [("b", 1), ("a", 2)]


@pytest.mark.parametrize("kwargs", [{}, {"inputs": None}, {"inputs": {}}])
def test_compose_without_inputs_calls_with_empty_dict(store, kwargs):
    """Omitted, None, and empty inputs are equivalent: the calculation sees {}."""
    spy = Spy(1)
    out = store.compose("px.o", Part(spy), **kwargs)
    assert spy.calls == [{}]
    assert out.composition.inputs == {}


def test_calculation_cannot_mutate_its_inputs(store):
    """Attack: a calculation mutates its argument; the input Part must be untouched."""
    store.set("px.l", Part([1, 2]))

    def evil(values):
        values["l"].append(666)
        return len(values["l"])

    out = store.compose("px.n", Part(evil), {"l": "px.l"})
    assert out.value == 3
    assert store.get("px.l").value == [1, 2], "input Part must not be mutated by the calculation"


def test_output_is_captured_not_aliased(store):
    """Attack: the calculation keeps a reference to what it returned and mutates it later."""
    kept = [1]
    out = store.compose("px.o", Part(lambda v: kept))
    kept.append(2)
    assert out.value == [1], "output Part must hold its own copy"


def test_calculation_can_produce_a_calculation(store):
    """Calculations are function-valued Parts, so a calculation may make one (needed for fn.* outputs)."""
    store.compose("fn.made", Part(lambda v: (lambda w: w["x"] * 3)))
    assert store.compose("px.r", "fn.made", {"x": Part(4)}).value == 12


# =============================== lineage ====================================
def test_composition_records_calculation_and_inputs_by_identity(store):
    """The lineage DAG is made of the very Part objects used (A5 will traverse it)."""
    calc, x, y = Part(add_x), Part(1), Part(2)
    out = store.compose("px.o", calc, {"x": x, "y": y})
    comp = out.composition
    assert isinstance(comp, Composition)
    assert comp.calculation is calc, "composition.calculation must be the calculation Part itself"
    assert comp.inputs["x"] is x and comp.inputs["y"] is y, "inputs must be the same Part objects"
    assert list(comp.inputs) == ["x", "y"], "input order must be preserved"


def test_composition_inputs_are_read_only(store):
    """Lineage must not be editable through the Composition."""
    x = Part(1)
    comp = store.compose("px.o", Part(add_x), {"x": x}).composition
    with pytest.raises(TypeError):
        comp.inputs["x"] = Part(9)  # type: ignore[index]
    with pytest.raises(dataclasses.FrozenInstanceError):
        comp.calculation = Part(len)  # type: ignore[misc]


def test_composition_snapshots_the_callers_mapping(store):
    """Mutating the dict passed as `inputs` afterwards must not alter recorded lineage."""
    d = {"x": Part(1)}
    out = store.compose("px.o", Part(add_x), d)
    d["y"] = Part(5)
    del d["x"]
    assert list(out.composition.inputs) == ["x"]


def test_lineage_forms_a_dag_with_shared_nodes(store):
    """A diamond a -> (b, c) -> d: both branches must point at the SAME root Part, roots have no composition."""
    a = store.set("px.a", Part(1))
    inc = Part(lambda v: v["x"] + 1)
    b = store.compose("px.b", inc, {"x": "px.a"})
    c = store.compose("px.c", inc, {"x": "px.a"})
    d = store.compose("px.d", Part(add_x), {"x": "px.b", "y": "px.c"})
    assert d.value == 4
    assert d.composition.inputs["x"] is b and d.composition.inputs["y"] is c
    assert b.composition.inputs["x"] is a and c.composition.inputs["x"] is a, "shared ancestor must be one object"
    assert a.composition is None


# =============================== compose: preflight =========================
def spy_store(store):
    spy = Spy(1)
    store.set("fn.spy", Part(spy))
    return spy


def test_compose_into_occupied_fails_before_running(store):
    """Preflight: occupancy is checked before the calculation runs, no receipt, original kept."""
    spy = spy_store(store)
    keep = store.set("px.o", Part("orig"))
    with pytest.raises(AddressOccupiedError):
        store.compose("px.o", "fn.spy")
    assert spy.calls == [], "calculation must not run when `into` is occupied"
    assert store.receipts() == () and store.get("px.o") is keep


def test_occupied_into_is_reported_before_a_missing_calculation(store):
    """Check order is part of the contract: `into` is validated first."""
    store.set("px.o", Part(1))
    with pytest.raises(AddressOccupiedError):
        store.compose("px.o", "fn.does_not_exist")


@pytest.mark.parametrize(
    "calculation, exc",
    [
        ("fn.missing", MissingPartError),
        ("px.notfn", TypeError),  # bound, but its value is not callable
        (lambda: Part(5), TypeError),  # a Part whose value is not callable
        (lambda: len, TypeError),  # a bare function is not a Part
        (lambda: None, TypeError),
        (lambda: 5, TypeError),
    ],
)
def test_bad_calculation_fails_preflight(store, calculation, exc):
    """The calculation must resolve to a function-valued Part; nothing runs, no receipt, `into` stays free."""
    store.set("px.notfn", Part(5))
    if callable(calculation):  # parameters are thunks so Parts are not built at collection time
        calculation = calculation()
    with pytest.raises(exc):
        store.compose("px.o", calculation)
    assert store.receipts() == () and not store.has("px.o")


@pytest.mark.parametrize(
    "inputs, exc",
    [
        (lambda: [("x", Part(1))], TypeError),  # not a Mapping
        (lambda: 5, TypeError),
        (lambda: "px.a", TypeError),
        (lambda: {"": Part(1)}, TypeError),  # empty name
        (lambda: {5: Part(1)}, TypeError),  # non-str name
        (lambda: {"x": 5}, TypeError),  # raw value instead of Part/address
        (lambda: {"x": None}, TypeError),
        (lambda: {"x": "px.missing"}, MissingPartError),
        (lambda: {"good": Part(1), "x": "px.missing"}, MissingPartError),
    ],
)
def test_bad_inputs_fail_preflight_without_running(store, inputs, exc):
    """Every input problem is found before the calculation runs; no receipt; `into` stays free."""
    spy = spy_store(store)
    with pytest.raises(exc):
        store.compose("px.o", "fn.spy", inputs())
    assert spy.calls == [], "calculation must not run if any input is bad"
    assert store.receipts() == () and not store.has("px.o")


def test_bad_into_fails_preflight_without_running(store):
    """An invalid target address is a preflight failure too."""
    spy = spy_store(store)
    with pytest.raises(ValueError):
        store.compose("bad", "fn.spy")
    assert spy.calls == [] and store.receipts() == ()


# =============================== compose: failure ===========================
def test_failed_calculation_reraises_same_exception_and_frees_address(store):
    """A raising calculation: same exception object re-raised, address stays free, a retry can succeed."""
    boom = RuntimeError("boom")

    def bad(values):
        raise boom

    with pytest.raises(RuntimeError) as info:
        store.compose("px.o", Part(bad))
    assert info.value is boom, "the original exception object must propagate unchanged"
    assert not store.has("px.o") and store.entries() == ()
    assert store.compose("px.o", Part(lambda v: 1)).value == 1, "the address must be reusable after a failure"


def test_failed_compose_records_failed_receipt(store):
    """A failed run is testimony too: status FAILED, into, composition, error, and no output."""
    boom = ValueError("nope")
    calc, x = Part(lambda v: (_ for _ in ()).throw(boom)), Part(1)
    with pytest.raises(ValueError):
        store.compose("px.o", calc, {"x": x})
    (r,) = store.receipts()
    assert r.status is ReceiptStatus.FAILED and r.into == "px.o"
    assert r.error is boom and r.output is None and r.tick is None
    assert r.composition.calculation is calc and r.composition.inputs["x"] is x


def test_fn_namespace_output_must_be_callable_else_failed_receipt(store):
    """Composing a non-callable into fn.* runs, then fails the namespace rule: TypeError, FAILED receipt, address free."""
    with pytest.raises(TypeError):
        store.compose("fn.bad", Part(lambda v: 5))
    assert not store.has("fn.bad")
    (r,) = store.receipts()
    assert r.status is ReceiptStatus.FAILED and isinstance(r.error, TypeError)


def test_uncopyable_output_is_a_failed_compose(store):
    """If wrapping the output fails (uncopyable value) the compose fails cleanly like any other failure."""
    with pytest.raises(TypeError):
        store.compose("px.o", Part(lambda v: threading.Lock()))
    assert not store.has("px.o")
    assert store.receipts()[0].status is ReceiptStatus.FAILED


def test_reentrant_write_to_own_target_is_rejected_while_in_flight(store):
    """While a compose into `into` is running, `into` is occupied: a calculation writing to it gets AddressOccupiedError."""
    seen = {}

    def sneaky(values):
        seen["has"] = store.has("px.o")
        for name, action in (("set", lambda: store.set("px.o", Part("sneaky"))),
                             ("compose", lambda: store.compose("px.o", Part(lambda v: 0)))):
            try:
                action()
            except AddressOccupiedError as e:
                seen[name] = e
        return "real"

    out = store.compose("px.o", Part(sneaky))
    assert seen["has"] is False, "an in-flight address is not bound yet"
    assert isinstance(seen["set"], AddressOccupiedError) and isinstance(seen["compose"], AddressOccupiedError)
    assert store.get("px.o") is out and out.value == "real"


# =============================== receipts ===================================
def test_produced_receipt_fields(store):
    """A PRODUCED receipt points at the bound output and the very Composition on that output."""
    out = store.compose("px.o", Part(lambda v: 1), {"x": Part(1)})
    (r,) = store.receipts()
    assert isinstance(r, Receipt) and r.status is ReceiptStatus.PRODUCED
    assert r.into == "px.o" and r.output is out and r.error is None and r.tick is None
    assert r.composition is out.composition


def test_set_records_no_receipt(store):
    """Receipts testify to compositions only; plain set is not a computation."""
    store.set("px.a", Part(1))
    assert store.receipts() == ()


def test_receipts_are_ordered_snapshots_and_frozen(store):
    """Receipts come back as a tuple in order of occurrence; they cannot be edited."""
    store.compose("px.a", Part(lambda v: 1))
    with pytest.raises(ZeroDivisionError):
        store.compose("px.b", Part(lambda v: 1 / 0))
    store.compose("px.c", Part(lambda v: 3))
    snap = store.receipts()
    assert isinstance(snap, tuple)
    assert [(r.into, r.status) for r in snap] == [
        ("px.a", ReceiptStatus.PRODUCED), ("px.b", ReceiptStatus.FAILED), ("px.c", ReceiptStatus.PRODUCED)]
    store.compose("px.d", Part(lambda v: 4))
    assert len(snap) == 3, "an earlier snapshot must not grow"
    with pytest.raises(dataclasses.FrozenInstanceError):
        snap[0].into = "px.zzz"  # type: ignore[misc]


# =============================== atomic tick ================================
def test_tick_commits_all_composes_in_order_with_receipts(store):
    """Normal exit binds everything, in compose order, with one PRODUCED receipt each tagged with the tick id."""
    store.set("px.x", Part(1))
    with store.tick("update") as tx:
        a = tx.compose("px.a", Part(lambda v: v["x"] + 1), {"x": "px.x"})
        b = tx.compose("px.b", Part(lambda v: v["x"] * 10), {"x": a})
    assert [k for k, _ in store.entries()] == ["px.x", "px.a", "px.b"]
    assert store.get("px.a") is a and store.get("px.b") is b and b.value == 20
    assert [(r.into, r.status, r.tick) for r in store.receipts()] == [
        ("px.a", ReceiptStatus.PRODUCED, "update"), ("px.b", ReceiptStatus.PRODUCED, "update")]
    assert store.receipts()[1].output is b


def test_tick_later_compose_can_read_earlier_staged_part_by_address(store):
    """Dependent steps (belief update) must read the previous step by address before commit; lineage points at the staged Part."""
    with store.tick("t") as tx:
        a = tx.compose("px.a", Part(lambda v: 5))
        assert tx.has("px.a") and tx.get("px.a") is a
        b = tx.compose("px.b", Part(lambda v: v["a"] + 1), {"a": "px.a"})
    assert b.value == 6 and b.composition.inputs["a"] is a


def test_tick_staged_work_is_invisible_outside_until_commit(store):
    """Isolation: store queries during an open tick show committed state only (no half-updated belief)."""
    store.set("px.old", Part(1))
    with store.tick("t") as tx:
        tx.compose("px.new", Part(lambda v: 2))
        assert store.has("px.new") is False
        assert [k for k, _ in store.entries()] == ["px.old"]
        assert store.receipts() == (), "receipts of a tick appear only when it exits"
        assert tx.has("px.old") and not tx.has("px.zzz")
        with pytest.raises(MissingPartError):
            store.get("px.new")
    assert store.has("px.new")


def test_tick_blocks_store_writes_and_nested_ticks_while_open(store):
    """Only one tick at a time and no side-door writes: otherwise atomicity cannot be guaranteed."""
    with store.tick("t"):
        with pytest.raises(TickInProgressError):
            store.set("px.a", Part(1))
        with pytest.raises(TickInProgressError):
            store.compose("px.a", Part(lambda v: 1))
        with pytest.raises(TickInProgressError):
            with store.tick("inner"):
                pass
    store.set("px.a", Part(1))  # store usable again after the tick
    assert store.entries()[0][0] == "px.a"


def test_tick_exception_rolls_back_everything_and_marks_every_compose_failed(store):
    """Atomicity: if the block raises, NOTHING is bound; each compose gets a FAILED receipt carrying the escaping exception."""
    store.set("px.keep", Part(0))
    late = RuntimeError("late")
    with pytest.raises(RuntimeError) as info:
        with store.tick("t") as tx:
            tx.compose("px.a", Part(lambda v: 1))
            tx.compose("px.b", Part(lambda v: 2))
            raise late
    assert info.value is late, "the same exception must be re-raised"
    assert [k for k, _ in store.entries()] == ["px.keep"], "no tick binding may survive a rollback"
    rs = store.receipts()
    assert [(r.into, r.status, r.tick) for r in rs] == [
        ("px.a", ReceiptStatus.FAILED, "t"), ("px.b", ReceiptStatus.FAILED, "t")]
    assert all(r.error is late and r.output is None for r in rs), "discarded composes carry the rollback exception"


def test_tick_failing_calculation_aborts_all_and_keeps_its_own_error(store):
    """A calculation failure escaping the block: earlier composes carry that exception; the failed one keeps its own (same object)."""
    boom = ValueError("boom")

    def bad(values):
        raise boom

    with pytest.raises(ValueError):
        with store.tick("t") as tx:
            tx.compose("px.a", Part(lambda v: 1))
            tx.compose("px.b", Part(bad))
            tx.compose("px.never", Part(lambda v: 3))  # never reached
    assert store.entries() == ()
    assert [(r.into, r.status) for r in store.receipts()] == [
        ("px.a", ReceiptStatus.FAILED), ("px.b", ReceiptStatus.FAILED)]
    assert all(r.error is boom for r in store.receipts())


def test_tick_rollback_error_differs_from_own_error_when_block_raises_something_else(store):
    """If the block catches a compose failure and then raises a different exception, each receipt keeps the right error."""
    own, outer = ValueError("own"), KeyError("outer")

    def bad(values):
        raise own

    with pytest.raises(KeyError):
        with store.tick("t") as tx:
            tx.compose("px.a", Part(lambda v: 1))
            try:
                tx.compose("px.b", Part(bad))
            except ValueError:
                pass
            raise outer
    a, b = store.receipts()
    assert (a.into, a.error) == ("px.a", outer), "successful-but-discarded compose carries the escaping exception"
    assert (b.into, b.error) == ("px.b", own), "the compose that itself failed keeps its own error"


def test_tick_addresses_are_free_again_after_rollback(store):
    """Rollback must release staged addresses and the tick lock so the work can be retried."""
    with pytest.raises(RuntimeError):
        with store.tick("t1") as tx:
            tx.compose("px.a", Part(lambda v: 1))
            raise RuntimeError
    with store.tick("t2") as tx:
        tx.compose("px.a", Part(lambda v: 2))
    assert store.get("px.a").value == 2


def test_tick_caught_calculation_failure_does_not_abort(store):
    """A compose failure the block handles does not roll back; its FAILED receipt sits in attempt order between PRODUCED ones."""
    own = ValueError("handled")

    def bad(values):
        raise own

    with store.tick("t") as tx:
        tx.compose("px.a", Part(lambda v: 1))
        with pytest.raises(ValueError):
            tx.compose("px.b", Part(bad))
        assert not tx.has("px.b"), "a failed compose stages nothing"
        tx.compose("px.b", Part(lambda v: 2))  # address is free for a retry within the tick
        tx.compose("px.c", Part(lambda v: 3))
    assert [k for k, _ in store.entries()] == ["px.a", "px.b", "px.c"]
    assert [(r.into, r.status) for r in store.receipts()] == [
        ("px.a", ReceiptStatus.PRODUCED), ("px.b", ReceiptStatus.FAILED),
        ("px.b", ReceiptStatus.PRODUCED), ("px.c", ReceiptStatus.PRODUCED)]
    assert store.receipts()[1].error is own and store.receipts()[1].output is None


def test_tick_preflight_failures_inside_tick_raise_without_receipt(store):
    """Same preflight rules inside a tick: raise, no receipt; the tick can continue and commit."""
    store.set("px.taken", Part(1))
    with store.tick("t") as tx:
        tx.compose("px.a", Part(lambda v: 1))
        with pytest.raises(AddressOccupiedError):
            tx.compose("px.taken", Part(lambda v: 2))  # committed binding
        with pytest.raises(AddressOccupiedError):
            tx.compose("px.a", Part(lambda v: 2))  # staged binding
        with pytest.raises(MissingPartError):
            tx.compose("px.b", Part(lambda v: 2), {"x": "px.missing"})
        with pytest.raises(ValueError):
            tx.compose("bad", Part(lambda v: 2))
    assert [r.into for r in store.receipts()] == ["px.a"]
    assert store.get("px.taken").value == 1


def test_tick_fn_rule_applies_to_staged_outputs(store):
    """Policing of fn.* output callability holds inside ticks too."""
    with store.tick("t") as tx:
        with pytest.raises(TypeError):
            tx.compose("fn.bad", Part(lambda v: 5))
        assert not tx.has("fn.bad")
    assert store.receipts()[0].status is ReceiptStatus.FAILED


def test_tick_empty_commits_with_no_receipts(store):
    """Degenerate tick: nothing staged, nothing recorded, store usable."""
    with store.tick("noop"):
        pass
    assert store.entries() == () and store.receipts() == ()


def test_tick_scope_is_dead_after_exit(store):
    """Using a scope after its block ended would bypass atomicity; every method must raise TickInProgressError."""
    with store.tick("t") as tx:
        pass
    with pytest.raises(TickInProgressError):
        tx.compose("px.a", Part(lambda v: 1))
    with pytest.raises(TickInProgressError):
        tx.get("px.a")
    with pytest.raises(TickInProgressError):
        tx.has("px.a")
    assert not store.has("px.a")


@pytest.mark.parametrize("bad, exc", [("", ValueError), (5, TypeError), (None, TypeError)])
def test_tick_id_must_be_nonempty_str_and_failure_leaves_store_usable(store, bad, exc):
    """A bad tick id is rejected on entry without leaving the store stuck in 'tick open'."""
    with pytest.raises(exc):
        with store.tick(bad):
            pass
    store.set("px.a", Part(1))  # would raise TickInProgressError if the failed tick had left the store busy


def test_tick_ids_are_recorded_per_tick(store):
    """Receipts identify their tick; ungrouped composes have tick None."""
    store.compose("px.solo", Part(lambda v: 0))
    with store.tick("one") as tx:
        tx.compose("px.a", Part(lambda v: 1))
    with store.tick("two") as tx:
        tx.compose("px.b", Part(lambda v: 2))
    assert [r.tick for r in store.receipts()] == [None, "one", "two"]


# =============================== property tests =============================
json_like = st.recursive(
    st.none() | st.booleans() | st.integers() | st.text(max_size=5),
    lambda c: st.lists(c, max_size=4) | st.dictionaries(st.text(max_size=3), c, max_size=4),
    max_leaves=15,
)


@given(json_like)
def test_property_part_value_equals_input_but_never_aliases(v):
    """For any JSON-like value: Part(v).value == v, and containers are never the same object (capture holds)."""
    p = Part(v)
    assert p.value == v
    if isinstance(v, (list, dict)):
        assert p.value is not v, "Part must not hand out the caller's own object"


@given(st.lists(st.tuples(st.sampled_from(["px.a", "px.b", "px.c", "sc.d"]), st.integers()), max_size=12))
def test_property_write_once_first_writer_wins(ops):
    """Model check: replaying random sets against a first-writer-wins dict must match the store exactly."""
    store, model = PxC(), {}
    for addr, n in ops:
        if addr in model:
            with pytest.raises(AddressOccupiedError):
                store.set(addr, Part(n))
        else:
            store.set(addr, Part(n))
            model[addr] = n
    assert [(k, p.value) for k, p in store.entries()] == list(model.items())


@given(st.lists(st.integers(-1000, 1000), max_size=8))
def test_property_compose_sum_matches_python_sum(nums):
    """compose over N named inputs equals sum(); also checks inputs may be arbitrarily many."""
    store = PxC()
    inputs = {f"n{i}": Part(n) for i, n in enumerate(nums)}
    out = store.compose("px.total", Part(lambda v: sum(v.values())), inputs)
    assert out.value == sum(nums)
    assert list(out.composition.inputs) == list(inputs)
