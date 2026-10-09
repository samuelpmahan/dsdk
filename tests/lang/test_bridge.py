"""Contract tests for dsdk.lang.bridge: logic -> Calc embedding (A1 link) and Calc traces as PxC lineage chains (A0 link)."""
import itertools
import json
from pathlib import Path

import pytest
from hypothesis import given
from hypothesis import strategies as st

from dsdk import logic
from dsdk.core import AddressOccupiedError, Part, PxC, ReceiptStatus, Status, TickInProgressError
from dsdk.lang import calc
from dsdk.lang.bridge import bind_assignment, from_formula, trace_into_pxc
from dsdk.lang.calc import BinOp, BoolLit, Let, Not, StuckError, Type, Var, classify, evaluate, free_vars, parse_calc, to_source, trace, typecheck
from dsdk.lang.formula_syntax import parse_formula

from lang_helpers import T, any_exprs, formulas, right_sum, show

a, b, c = logic.Var("a"), logic.Var("b"), logic.Var("c")
LOGIC_FIX = Path(__file__).resolve().parents[2] / "fixtures" / "logic"


# ------------------------------------------------------------------ from_formula
SHAPES = [
    (lambda: logic.Const(True), lambda: BoolLit(True)),
    (lambda: logic.Const(False), lambda: BoolLit(False)),
    (lambda: logic.Var("a"), lambda: Var("a")),
    (lambda: logic.Not(a), lambda: Not(Var("a"))),
    (lambda: logic.And(a, b), lambda: BinOp("and", Var("a"), Var("b"))),
    (lambda: logic.Or(a, b), lambda: BinOp("or", Var("a"), Var("b"))),
    (lambda: logic.Implies(a, b), lambda: BinOp("or", Not(Var("a")), Var("b"))),
    (lambda: logic.Iff(a, b), lambda: BinOp("==", Var("a"), Var("b"))),
    (lambda: logic.Implies(logic.Implies(a, b), c), lambda: BinOp("or", Not(BinOp("or", Not(Var("a")), Var("b"))), Var("c"))),
    (lambda: logic.Not(logic.Iff(a, logic.Const(True))), lambda: Not(BinOp("==", Var("a"), BoolLit(True)))),
]


@pytest.mark.parametrize("f,expected", SHAPES, ids=[str(i) for i in range(len(SHAPES))])
def test_from_formula_has_the_exact_documented_shape(f, expected):
    """Each connective maps to one fixed Calc shape (implication is `not x or y`, iff is `==` on Bools), so other code can rely on the structure."""
    assert from_formula(f()) == expected()


@pytest.mark.parametrize("name", ["and", "or", "not", "let", "in", "if", "then", "else"])
def test_keyword_named_logic_variables_are_rejected(name):
    """`Var("not")` is a legal logic variable but not a legal Calc one: from_formula raises ValueError instead of producing a broken term."""
    with pytest.raises(ValueError):
        from_formula(logic.And(logic.Var("a"), logic.Var(name)))


@pytest.mark.parametrize("bad", ["a", 1, None, [1]])
def test_from_formula_requires_a_logic_formula(bad):
    """Strings, numbers and None are not Formulas: TypeError."""
    with pytest.raises(TypeError):
        from_formula(bad)


def test_from_formula_rejects_calc_nodes():
    """Calc nodes are not logic Formulas even though they look alike (Var, Not): TypeError."""
    for bad in (BoolLit(True), Var("a"), Not(Var("a"))):
        with pytest.raises(TypeError):
            from_formula(bad)


def test_from_formula_translation_is_a_closed_bool_fragment():
    """The result typechecks as Bool whenever its variables are declared Bool, and its free variables are exactly the formula's."""
    f = logic.Iff(logic.Var("B11"), logic.Or(logic.Var("P12"), logic.Var("P21")))
    e = from_formula(f)
    assert free_vars(e) == logic.variables(f) == {"B11", "P12", "P21"}
    assert typecheck(e, {v: Type.BOOL for v in free_vars(e)}).value is Type.BOOL


@given(formulas())
def test_translation_is_well_typed_bool_and_keeps_variables(f):
    """For every formula: free_vars preserved and type Bool under an all-Bool environment."""
    e = from_formula(f)
    assert free_vars(e) == logic.variables(f)
    j = typecheck(e, {v: Type.BOOL for v in logic.variables(f)})
    assert j.status is Status.KNOWN and j.value is Type.BOOL


# ------------------------------------------------------------------ bind_assignment
def test_bind_assignment_wraps_in_sorted_lets_first_name_outermost():
    """Names ascending, smallest outermost, each bound to a BoolLit; the exact nesting is the cross-language encoding."""
    body = BinOp("and", Var("a"), Var("b"))
    got = bind_assignment(body, {"b": False, "a": True})
    assert got == Let("a", BoolLit(True), Let("b", BoolLit(False), body))
    assert bind_assignment(body, {"a": True, "b": False}) == got, "dict insertion order must not matter"
    assert bind_assignment(body, {"P2": True, "P12": False}) == Let("P12", BoolLit(False), Let("P2", BoolLit(True), body)), "plain str order: 'P12' < 'P2'"


def test_bind_assignment_empty_returns_the_same_expression():
    """No names, no wrapping."""
    body = Var("a")
    assert bind_assignment(body, {}) is body


@pytest.mark.parametrize("bad", [1, 0, None, "True"])
def test_bind_assignment_requires_real_bools(bad):
    """Like logic.evaluate: 1 and None are not truth values here (TypeError)."""
    with pytest.raises(TypeError):
        bind_assignment(Var("a"), {"a": bad})


# ------------------------------------------------------------------ agreement with dsdk.logic
@given(formulas(), st.fixed_dictionaries({"a": st.booleans(), "b": st.booleans(), "c": st.booleans()}))
def test_calc_evaluation_agrees_with_logic_evaluation(f, assignment):
    """THE BRIDGE LAW: calc.evaluate(lets(a) around from_formula(f)) is logic.evaluate(f, a) for every formula and total assignment (a real bool, not 1/0)."""
    want = logic.evaluate(f, assignment)
    e = bind_assignment(from_formula(f), assignment)
    assert typecheck(e).value is Type.BOOL, "a fully bound translation is a closed Bool program"
    got = evaluate(e)
    assert got is want, f"{logic.to_str(f)} under {assignment}: calc {got!r} vs logic {want!r}"


@given(formulas(max_leaves=6), st.fixed_dictionaries({"a": st.booleans(), "b": st.booleans(), "c": st.booleans()}))
def test_small_step_trace_also_reaches_the_logic_value(f, assignment):
    """The small-step trace of the bridged program ends in the same BoolLit as logic.evaluate: the three evaluators (logic, big-step, small-step) agree."""
    e = bind_assignment(from_formula(f), assignment)
    final = trace(e)[-1]
    assert final == BoolLit(logic.evaluate(f, assignment))


CASES = json.loads((LOGIC_FIX / "formulas.json").read_text(encoding="utf-8"))["cases"]


@pytest.mark.parametrize("case", CASES, ids=[c["name"] for c in CASES])
def test_calc_reproduces_every_row_of_the_logic_fixture_truth_tables(case):
    """Parse each canonical fixture string (A2 parser), embed it (bridge), evaluate with Calc: every row equals the A1 fixture's independently computed truth table."""
    f = parse_formula(case["string"])
    e = from_formula(f)
    for row in case["truth_table"]:
        assert evaluate(bind_assignment(e, row["assignment"])) is row["value"], f"{case['string']} under {row['assignment']}"


def test_calc_counts_the_three_wumpus_models():
    """The Russell & Norvig corner KB has exactly 3 models in the A1 fixture; Calc, evaluating the conjunction of the premises on all 128 assignments, finds the same 3 (the A3 numbers 4/9, 4/9, 1/9 start here)."""
    kb = json.loads((LOGIC_FIX / "wumpus_kb.json").read_text(encoding="utf-8"))
    premises = [parse_formula(p["string"]) for p in kb["premises"]]
    conj = premises[0]
    for p in premises[1:]:
        conj = logic.And(conj, p)
    e = from_formula(conj)
    names = sorted(kb["variables"])
    found = []
    for combo in itertools.product([False, True], repeat=len(names)):
        assignment = dict(zip(names, combo))
        if evaluate(bind_assignment(e, assignment)) is True:
            found.append(assignment)
    assert found == kb["models"], "same models in the same enumeration order as the fixture"
    assert len(found) == kb["model_count"] == 3


def test_a_missing_variable_is_unassigned_in_logic_and_stuck_in_calc():
    """The same mistake has two faces: logic raises UnassignedVariableError, Calc reports the term as INVALID statically (unbound variable) and STUCK dynamically."""
    f = logic.And(logic.Var("a"), logic.Var("b"))
    with pytest.raises(logic.UnassignedVariableError):
        logic.evaluate(f, {"a": True})
    e = bind_assignment(from_formula(f), {"a": True})
    j = typecheck(e)
    assert j.status is Status.INVALID and j.reason == "unbound variable: b"
    assert classify(trace(e)[-1]) is calc.Outcome.STUCK
    with pytest.raises(StuckError):
        evaluate(e)


def test_calc_short_circuits_where_logic_insists_on_a_total_assignment():
    """The bridge law needs a TOTAL assignment: `false and x` evaluates in Calc without x (short-circuit) but logic.evaluate rejects the missing variable."""
    f = logic.And(logic.Const(False), logic.Var("x"))
    with pytest.raises(logic.UnassignedVariableError):
        logic.evaluate(f, {})
    assert evaluate(from_formula(f)) is False


def test_source_round_trip_through_the_parser():
    """The embedded program prints and re-parses to itself: parse_formula -> from_formula -> to_source -> parse_calc is the identity on the Calc side."""
    f = parse_formula("(a | b) & ~c -> a <-> b", relaxed=True)
    e = from_formula(f)
    assert parse_calc(to_source(e)) == e


def test_deep_formula_embeds_and_evaluates():
    """200 nested negations bridge without recursion errors: even depth gives the same value."""
    f = logic.Var("a")
    for _ in range(200):
        f = logic.Not(f)
    e = bind_assignment(from_formula(f), {"a": True})
    assert evaluate(e) is True


# ------------------------------------------------------------------ trace_into_pxc
def records(store, prefix, n):
    return [store.get(f"px.{prefix}.{i}").value for i in range(n + 1)]


def lineage(head):
    """Walk the `prev` chain iteratively from the head to the step-0 Part; returns the Parts head-first."""
    out = [head]
    while "prev" in out[-1].composition.inputs:
        out.append(out[-1].composition.inputs["prev"])
    return out


def test_trace_is_recorded_as_one_part_per_step_with_exact_records():
    """`(1+2)+(3+4)` has 3 steps, so 4 Parts at px.run.0..3 holding index/source/outcome records that match calc.trace."""
    store = PxC()
    e = T("((1 + 2) + (3 + 4))")
    head = trace_into_pxc(e, store, "run")
    t = trace(e)
    assert [addr for addr, _ in store.entries()] == ["px.run.0", "px.run.1", "px.run.2", "px.run.3"]
    assert records(store, "run", 3) == [
        {"index": 0, "source": "((1 + 2) + (3 + 4))", "outcome": "step"},
        {"index": 1, "source": "(3 + (3 + 4))", "outcome": "step"},
        {"index": 2, "source": "(3 + 7)", "outcome": "step"},
        {"index": 3, "source": "10", "outcome": "value"},
    ]
    assert [r["source"] for r in records(store, "run", 3)] == [show(x) for x in t]
    assert head is store.get("px.run.3"), "the returned Part is the very object bound at the last address"


def test_parts_form_a_lineage_chain_through_prev_inputs():
    """Each step's composition has the single input `prev` = the Part of the previous step (identity), down to step 0 whose only input is `program`."""
    store = PxC()
    e = T("((1 + 2) + (3 + 4))")
    head = trace_into_pxc(e, store, "run")
    chain = lineage(head)
    assert [p.value["index"] for p in chain] == [3, 2, 1, 0]
    for i, part in enumerate(reversed(chain)):
        assert part is store.get(f"px.run.{i}"), f"chain element {i} must be the stored Part itself"
    for part in chain[:-1]:
        assert list(part.composition.inputs) == ["prev"]
    root = chain[-1]
    assert list(root.composition.inputs) == ["program"]
    program = root.composition.inputs["program"]
    assert program.composition is None and program.value == "((1 + 2) + (3 + 4))"


def test_all_later_steps_share_one_calculation_part_and_it_is_callable():
    """Steps >= 1 are produced by the same calculation Part (one rule applied repeatedly); every calculation Part holds a callable."""
    store = PxC()
    head = trace_into_pxc(T("((1 + 2) + (3 + 4))"), store, "run")
    chain = lineage(head)
    steps_calc = {id(p.composition.calculation) for p in chain[:-1]}
    assert len(steps_calc) == 1
    assert all(callable(p.composition.calculation.value) for p in chain)


def test_the_calculations_really_compute_from_their_inputs():
    """Feeding the calculations different inputs gives different, correct outputs: they parse their input and apply calc.step, they do not replay stored answers."""
    store = PxC()
    head = trace_into_pxc(T("(1 + 2)"), store, "run")
    step_fn = head.composition.calculation.value
    load_fn = store.get("px.run.0").composition.calculation.value
    assert step_fn({"prev": {"index": 5, "source": "(10 * 10)", "outcome": "step"}}) == {"index": 6, "source": "100", "outcome": "value"}
    assert step_fn({"prev": {"index": 0, "source": "(if true then (1 + 1) else 0)", "outcome": "step"}}) == {"index": 1, "source": "(1 + 1)", "outcome": "step"}
    assert load_fn({"program": "(not true)"}) == {"index": 0, "source": "(not true)", "outcome": "step"}
    assert load_fn({"program": "(1 + true)"}) == {"index": 0, "source": "(1 + true)", "outcome": "stuck"}


def test_receipts_are_produced_in_one_tick_named_by_the_prefix():
    """One tick: n+1 PRODUCED receipts, all with tick == prefix, in step order (that is dsdk.core tick semantics showing through)."""
    store = PxC()
    trace_into_pxc(T("((1 + 2) + (3 + 4))"), store, "run")
    rs = store.receipts()
    assert [r.into for r in rs] == ["px.run.0", "px.run.1", "px.run.2", "px.run.3"]
    assert all(r.status is ReceiptStatus.PRODUCED and r.tick == "run" for r in rs)


def test_a_value_program_is_a_single_part_whose_input_is_the_program():
    """A value has an empty step list: one Part, outcome 'value', returned and bound at px.<prefix>.0, with only the `program` input."""
    store = PxC()
    head = trace_into_pxc(T("42"), store, "v")
    assert head is store.get("px.v.0") and len(store.entries()) == 1
    assert head.value == {"index": 0, "source": "42", "outcome": "value"}
    assert list(head.composition.inputs) == ["program"]


def test_a_stuck_program_is_traced_up_to_the_stuck_term():
    """`(1+1)+true` steps once then is stuck: two Parts, the last has outcome 'stuck' (a stuck run is data too, not an error)."""
    store = PxC()
    head = trace_into_pxc(T("((1 + 1) + true)"), store, "s")
    assert records(store, "s", 1) == [
        {"index": 0, "source": "((1 + 1) + true)", "outcome": "step"},
        {"index": 1, "source": "(2 + true)", "outcome": "stuck"},
    ]
    assert head is store.get("px.s.1")


def test_nothing_else_is_written_to_the_store():
    """Only px.<prefix>.<i> addresses are bound; no fn.* or sc.* bookkeeping."""
    store = PxC()
    trace_into_pxc(T("(let x = 1 in (x + x))"), store, "t")
    assert all(addr.startswith("px.t.") for addr, _ in store.entries())


def test_two_runs_with_different_prefixes_coexist_and_stay_separate():
    """Different prefixes do not collide; each chain stays internally linked."""
    store = PxC()
    h1 = trace_into_pxc(T("(1 + 2)"), store, "one")
    h2 = trace_into_pxc(T("(3 * 4)"), store, "two")
    assert len(store.entries()) == 4
    assert h1.value["source"] == "3" and h2.value["source"] == "12"
    assert {id(p) for p in lineage(h1)}.isdisjoint({id(p) for p in lineage(h2)})


def test_reusing_a_prefix_fails_and_leaves_the_first_trace_intact():
    """Write-once store: a second run with the same prefix raises AddressOccupiedError; the first trace is untouched."""
    store = PxC()
    trace_into_pxc(T("(1 + 2)"), store, "run")
    before = store.entries()
    with pytest.raises(AddressOccupiedError):
        trace_into_pxc(T("(1 + 2)"), store, "run")
    assert store.entries() == before


def test_the_trace_is_atomic_a_collision_midway_binds_nothing():
    """If px.run.2 is already taken, steps 0 and 1 must NOT remain bound, and their receipts must be FAILED: the single tick rolled back."""
    store = PxC()
    store.set("px.run.2", Part("squatter"))
    with pytest.raises(AddressOccupiedError):
        trace_into_pxc(T("((1 + 2) + (3 + 4))"), store, "run")
    assert [addr for addr, _ in store.entries()] == ["px.run.2"]
    rs = store.receipts()
    assert [r.into for r in rs] == ["px.run.0", "px.run.1"]
    assert all(r.status is ReceiptStatus.FAILED and r.tick == "run" and r.output is None for r in rs)
    store.set("px.other", Part(1))  # the store is usable again: the tick was closed


@pytest.mark.parametrize("prefix,exc", [("", ValueError), (5, TypeError), (None, TypeError)])
def test_bad_prefix_is_rejected_before_touching_the_store(prefix, exc):
    """Prefix validation happens first: no Parts, no receipts, no open tick left behind."""
    store = PxC()
    with pytest.raises(exc):
        trace_into_pxc(T("(1 + 2)"), store, prefix)
    assert store.entries() == () and store.receipts() == ()
    store.set("px.ok", Part(1))


def test_argument_types_are_checked():
    """store must be a PxC and expr an Expr."""
    with pytest.raises(TypeError):
        trace_into_pxc(T("1"), object(), "p")
    with pytest.raises(TypeError):
        trace_into_pxc("1 + 2", PxC(), "p")


def test_calling_inside_an_open_tick_propagates_the_stores_own_error():
    """The bridge does not work around dsdk.core: with a tick already open, opening its own tick raises TickInProgressError."""
    store = PxC()
    with store.tick("outer"):
        with pytest.raises(TickInProgressError):
            trace_into_pxc(T("(1 + 2)"), store, "inner")


def test_a_long_trace_is_a_long_chain_and_values_are_plain_strings():
    """A 100-step trace gives 101 Parts linked by identity; because records hold source STRINGS (not 100-deep ASTs) nothing blows up in the store's deep copies."""
    store = PxC()
    head = trace_into_pxc(right_sum(100), store, "long")
    chain = lineage(head)
    assert len(chain) == 101 and chain[0].value["source"] == "101" and chain[-1].value["index"] == 0
    assert all(p is store.get(f"px.long.{100 - i}") for i, p in enumerate(chain))


@given(any_exprs(max_leaves=10))
def test_records_always_match_calc_trace_and_chain_length(e):
    """For ANY term (stuck or not): n+1 records equal [index, to_source, outcome] of calc.trace(e), and the lineage has n+1 Parts."""
    store = PxC()
    head = trace_into_pxc(e, store, "p")
    t = trace(e)
    assert records(store, "p", len(t) - 1) == [{"index": i, "source": to_source(x), "outcome": classify(x).value} for i, x in enumerate(t)]
    assert len(lineage(head)) == len(t)
    assert len(store.receipts()) == len(t)
