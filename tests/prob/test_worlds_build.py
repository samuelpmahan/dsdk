"""Contract tests for building beliefs: WeightedWorld, Belief, prior_belief (possible worlds = logic models, weights = priors)."""
import dataclasses
from fractions import Fraction

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from dsdk import logic
from dsdk.logic import And, Const, Iff, Implies, Not, Or, Var
from dsdk.prob import MAX_VARIABLES, Belief, UnmodelledVariableError, WeightedWorld, prior_belief

from prob_helpers import Fr, formulas, prior_maps, ref_eval, ref_vars, ref_worlds, total_of

A, B, C = Var("A"), Var("B"), Var("C")


# ------------------------------------------------------------------ WeightedWorld / Belief validation
def test_weighted_world_basic_and_assignment_is_a_fresh_dict():
    w = WeightedWorld((("A", False), ("B", True)), Fr(1, 4))
    assert w.assignment() == {"A": False, "B": True}
    w.assignment()["A"] = True
    assert w.assignment() == {"A": False, "B": True}, "mutating the returned dict must not change the world"
    assert hash(w) == hash(WeightedWorld((("A", False), ("B", True)), Fr(1, 4)))


def test_weighted_world_is_frozen():
    w = WeightedWorld((("A", True),), Fr(1))
    with pytest.raises(dataclasses.FrozenInstanceError):
        w.weight = Fr(2)


@pytest.mark.parametrize(
    "values,weight,exc",
    [
        ([("A", True)], Fr(1), TypeError),  # list, not tuple
        ((("A", 1),), Fr(1), TypeError),  # 1 is not exactly bool
        (((1, True),), Fr(1), TypeError),  # name not str
        ((("A", True, 3),), Fr(1), TypeError),  # not a pair
        (("A",), Fr(1), TypeError),
        ((("B", True), ("A", True)), Fr(1), ValueError),  # not increasing
        ((("A", True), ("A", False)), Fr(1), ValueError),  # duplicate
        ((("A", True),), 0.5, TypeError),  # float weight
        ((("A", True),), 1, TypeError),  # int weight
        ((("A", True),), Fr(-1, 2), ValueError),
    ],
)
def test_weighted_world_validation(values, weight, exc):
    with pytest.raises(exc):
        WeightedWorld(values, weight)


def test_empty_world_is_legal():
    """A belief over no variables has one world with the empty assignment."""
    assert WeightedWorld((), Fr(1)).assignment() == {}


def test_belief_validation():
    w = WeightedWorld((("A", True),), Fr(1))
    Belief(("A",), (w,))
    with pytest.raises(TypeError):
        Belief(["A"], (w,))
    with pytest.raises(TypeError):
        Belief((1,), ())
    with pytest.raises(ValueError):
        Belief(("B", "A"), ())
    with pytest.raises(ValueError):
        Belief(("A", "A"), ())
    with pytest.raises(TypeError):
        Belief(("A",), [w])
    with pytest.raises(TypeError):
        Belief(("A",), ("not a world",))
    with pytest.raises(ValueError):
        Belief(("A", "B"), (w,))  # world ranges over A only
    with pytest.raises(ValueError):
        Belief(("B",), (w,))


def test_belief_total_and_mass():
    b = prior_belief({"A": Fr(1, 2), "B": Fr(1, 2)})
    assert b.total == 1
    assert b.mass(A) == Fr(1, 2)
    assert b.mass(And(A, B)) == Fr(1, 4)
    assert b.mass(Const(False)) == 0
    assert b.mass(Const(True)) == 1
    empty = Belief((), ())
    assert empty.total == 0 and isinstance(empty.total, Fraction)


def test_mass_rejects_non_formulas_and_unmodelled_variables():
    b = prior_belief({"A": Fr(1, 2)})
    with pytest.raises(TypeError):
        b.mass("A")
    with pytest.raises(UnmodelledVariableError) as info:
        b.mass(And(Var("A"), Or(Var("Z"), Var("Y"))))
    assert info.value.names == ("Y", "Z"), "names are sorted"
    assert isinstance(info.value, ValueError)


# ------------------------------------------------------------------ prior_belief
def test_docstring_example_order_and_weights():
    """Order is logic.models order: A=False before A=True, first variable slowest; weights 4/25, 4/25, 1/25."""
    b = prior_belief({"A": 0.2, "B": 0.2}, Or(A, B))
    assert b.variables == ("A", "B")
    assert [w.values for w in b.worlds] == [(("A", False), ("B", True)), (("A", True), ("B", False)), (("A", True), ("B", True))]
    assert [w.weight for w in b.worlds] == [Fr(4, 25), Fr(4, 25), Fr(1, 25)]
    assert b.total == Fr(9, 25)


def test_no_constraint_gives_all_worlds_summing_to_one():
    b = prior_belief({"A": Fr(1, 5), "B": Fr(1, 3), "C": Fr(3, 4)})
    assert len(b.worlds) == 8
    assert b.total == 1
    # independence: the world A=T,B=F,C=T has weight (1/5)(2/3)(3/4)
    w = {x.values: x.weight for x in b.worlds}
    assert w[(("A", True), ("B", False), ("C", True))] == Fr(1, 5) * Fr(2, 3) * Fr(3, 4)


def test_priors_may_be_floats_ints_or_fractions_mixed():
    b = prior_belief({"A": 0.25, "B": 1, "C": Fr(1, 2)})
    assert b.total == 1
    assert b.mass(B) == 1


def test_zero_weight_worlds_are_kept():
    """A prior of 0 does not remove worlds: 'possible' (logic) and 'probable' (weight) are different questions."""
    b = prior_belief({"A": 0, "B": Fr(1, 2)})
    assert len(b.worlds) == 4
    assert sum(1 for w in b.worlds if w.weight == 0) == 2
    assert b.total == 1


def test_certain_prior_zeroes_the_other_branch():
    b = prior_belief({"A": 1})
    assert [w.weight for w in b.worlds] == [Fr(0), Fr(1)]


def test_variable_without_prior_contributes_factor_one():
    """Percepts determined by the constraint (like breezes) need no prior: B <-> A has two worlds, each weighted by A's prior only."""
    b = prior_belief({"A": Fr(1, 5)}, Iff(Var("B"), A))
    assert b.variables == ("A", "B")
    assert [w.values for w in b.worlds] == [(("A", False), ("B", False)), (("A", True), ("B", True))]
    assert [w.weight for w in b.worlds] == [Fr(4, 5), Fr(1, 5)]


def test_prior_for_variable_absent_from_constraint_still_enumerated():
    """A prior on a variable the constraint never mentions is a free variable: it doubles the worlds."""
    b = prior_belief({"A": Fr(1, 2), "Z": Fr(1, 4)}, A)
    assert b.variables == ("A", "Z")
    assert len(b.worlds) == 2
    assert b.total == Fr(1, 2)


def test_unsatisfiable_constraint_gives_no_worlds_and_zero_total():
    b = prior_belief({"A": Fr(1, 2)}, And(A, Not(A)))
    assert b.worlds == () and b.total == 0 and b.variables == ("A",)


def test_empty_priors_and_no_constraint_is_one_empty_world():
    b = prior_belief({})
    assert b.variables == () and len(b.worlds) == 1 and b.worlds[0].weight == 1


def test_constant_constraint_only():
    assert prior_belief({}, Const(False)).worlds == ()
    assert len(prior_belief({}, Const(True)).worlds) == 1


@pytest.mark.parametrize("bad", [[("A", 0.5)], None, "A", [0.5]])
def test_priors_must_be_a_mapping(bad):
    with pytest.raises(TypeError):
        prior_belief(bad)


def test_prior_names_must_be_str():
    with pytest.raises(TypeError):
        prior_belief({1: 0.5})


@pytest.mark.parametrize("bad", ["A", Var, 3, [A]])
def test_constraint_must_be_a_formula_or_none(bad):
    with pytest.raises(TypeError):
        prior_belief({"A": 0.5}, bad)


@pytest.mark.parametrize("p,exc", [(1.5, ValueError), (-0.1, ValueError), (float("nan"), ValueError), (True, TypeError), ("0.5", TypeError)])
def test_bad_prior_values_raise(p, exc):
    with pytest.raises(exc):
        prior_belief({"A": p})


def test_variable_limit_is_enforced_before_enumeration():
    ok = {f"v{i:02d}": Fr(1, 2) for i in range(MAX_VARIABLES)}
    too_many = dict(ok, extra=Fr(1, 2))
    with pytest.raises(ValueError):
        prior_belief(too_many)
    # constraint variables count too
    with pytest.raises(ValueError):
        prior_belief(ok, Var("another"))
    # the boundary itself is accepted; use a constraint that keeps only one world so it stays fast
    b = prior_belief(ok, logic.Var("v00"))
    assert len(b.variables) == MAX_VARIABLES


def test_priors_mapping_is_not_mutated():
    priors = {"B": 0.5, "A": 0.25}
    prior_belief(priors, Or(A, B))
    assert priors == {"B": 0.5, "A": 0.25}


def test_world_values_are_hashable_keys_and_assignments_work_with_logic_evaluate():
    b = prior_belief({"A": Fr(1, 2), "B": Fr(1, 2)}, Implies(A, B))
    for w in b.worlds:
        assert logic.evaluate(Implies(A, B), w.assignment())
    assert len({w.values for w in b.worlds}) == len(b.worlds)


def test_worlds_are_exactly_logic_models():
    """Possible worlds ARE the models from dsdk.logic, in the same order."""
    f = Iff(Var("B11"), Or(Var("P12"), Var("P21")))
    priors = {"P12": Fr(1, 5), "P21": Fr(1, 5)}
    b = prior_belief(priors, f)
    expected = list(logic.models(f, over=sorted(set(priors) | logic.variables(f))))
    assert [w.assignment() for w in b.worlds] == expected


@settings(max_examples=60)
@given(prior_maps(), formulas())
def test_weights_match_the_brute_force_oracle(priors, constraint):
    """Against an independent itertools oracle: same variables, same worlds in the same order, same exact weights."""
    b = prior_belief(priors, constraint)
    expected = ref_worlds(priors, constraint)
    names = tuple(sorted(set(priors) | ref_vars(constraint)))
    assert b.variables == names
    assert [w.assignment() for w in b.worlds] == [env for env, _ in expected]
    assert [w.weight for w in b.worlds] == [wt for _, wt in expected]
    assert b.total == total_of(b)


@settings(max_examples=60)
@given(prior_maps(), formulas())
def test_every_world_satisfies_the_constraint_and_every_model_appears(priors, constraint):
    b = prior_belief(priors, constraint)
    assert all(ref_eval(constraint, w.assignment()) for w in b.worlds)
    count = len(list(logic.models(constraint, over=b.variables)))
    assert len(b.worlds) == count


@settings(max_examples=40)
@given(prior_maps())
def test_unconstrained_total_is_one(priors):
    assert prior_belief(priors).total == 1


@settings(max_examples=40)
@given(prior_maps(), formulas())
def test_total_equals_probability_of_constraint_under_independence(priors, constraint):
    """total = P(constraint) when the constraint only mentions variables that have priors (it is then the mass of the independent prior)."""
    if not ref_vars(constraint) <= set(priors):
        return
    full = prior_belief(priors)
    constrained = prior_belief(priors, constraint)
    assert constrained.total == full.mass(constraint)
