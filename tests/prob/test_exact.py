"""Contract tests for dsdk.prob.exact: every probability is an exact Fraction, converted by documented rules."""
import math
from decimal import Decimal
from fractions import Fraction

import pytest
from hypothesis import given
from hypothesis import strategies as st

from dsdk.prob import to_prob, to_weight


@pytest.mark.parametrize("x,expected", [(0, Fraction(0)), (1, Fraction(1)), (Fraction(1, 3), Fraction(1, 3)), (0.5, Fraction(1, 2)), (0.25, Fraction(1, 4))])
def test_exact_inputs_convert_to_themselves(x, expected):
    """Ints, Fractions and floats that are binary-exact convert to the obvious Fraction, and the result is a real Fraction."""
    for fn in (to_prob, to_weight):
        out = fn(x)
        assert type(out) is Fraction and out == expected


@pytest.mark.parametrize("x,expected", [(0.2, Fraction(1, 5)), (0.1, Fraction(1, 10)), (0.05, Fraction(1, 20)), (0.3, Fraction(3, 10)), (0.9, Fraction(9, 10)), (1e-07, Fraction(1, 10_000_000))])
def test_floats_go_through_their_shortest_decimal_not_their_binary_value(x, expected):
    """0.2 is exactly 1/5, not the binary neighbour of 0.2: this is what lets the Wumpus posterior be exactly 4/9."""
    assert to_prob(x) == expected
    assert to_prob(x) != Fraction(x) or x in (0.5, 0.25)  # Fraction(0.2) is NOT 1/5


def test_wumpus_numbers_are_exact_only_because_of_the_repr_rule():
    """With the oracle's own prior 0.2: p(1-p)/(1-(1-p)^2) must be exactly 4/9 (it would be 0.4444...01 with binary 0.2)."""
    p = to_prob(0.2)
    assert p * (1 - p) / (1 - (1 - p) ** 2) == Fraction(4, 9)


@pytest.mark.parametrize("bad", [True, False])
def test_bool_is_rejected_even_though_it_is_an_int(bad):
    """True is 1 in Python; a probability of True is a bug in the caller, so it is a TypeError."""
    for fn in (to_prob, to_weight):
        with pytest.raises(TypeError):
            fn(bad)


@pytest.mark.parametrize("bad", ["0.5", None, Decimal("0.5"), 1 + 0j, [0.5], b"1"])
def test_other_types_are_a_type_error(bad):
    for fn in (to_prob, to_weight):
        with pytest.raises(TypeError):
            fn(bad)


@pytest.mark.parametrize("bad", [math.nan, math.inf, -math.inf])
def test_non_finite_floats_are_a_value_error(bad):
    for fn in (to_prob, to_weight):
        with pytest.raises(ValueError):
            fn(bad)


@pytest.mark.parametrize("bad", [-1, -0.001, Fraction(-1, 2)])
def test_negative_values_are_a_value_error_for_both(bad):
    for fn in (to_prob, to_weight):
        with pytest.raises(ValueError):
            fn(bad)


@pytest.mark.parametrize("big", [2, 1.0000001, Fraction(3, 2), 100])
def test_to_prob_rejects_values_above_one_but_to_weight_accepts_them(big):
    """Weights are unnormalised masses (any non-negative), probabilities are capped at 1."""
    with pytest.raises(ValueError):
        to_prob(big)
    assert to_weight(big) >= 1


def test_zero_and_one_are_legal_probabilities():
    assert to_prob(0) == 0 and to_prob(1) == 1 and to_prob(1.0) == 1 and to_prob(0.0) == 0


def test_negative_zero_is_zero():
    assert to_prob(-0.0) == 0


def test_error_message_uses_the_name_argument():
    """The name given by the caller appears in the message so users can find which prior was bad."""
    with pytest.raises(ValueError, match="my_prior"):
        to_prob(7, "my_prior")
    with pytest.raises(TypeError, match="my_weight"):
        to_weight("x", "my_weight")


def test_type_error_wins_over_value_error():
    """A bool is a TypeError even though True == 1 is also in range; a string is never range-checked."""
    with pytest.raises(TypeError):
        to_prob(True)


@given(st.fractions(min_value=0, max_value=1, max_denominator=1000))
def test_fractions_in_range_round_trip(fr):
    assert to_prob(fr) == fr and to_weight(fr) == fr


@given(st.floats(min_value=0, max_value=1, allow_nan=False))
def test_float_conversion_is_the_repr_fraction(x):
    assert to_prob(x) == Fraction(repr(x))
    assert 0 <= to_prob(x) <= 1


@given(st.integers(min_value=-10, max_value=10))
def test_int_range_rule(n):
    if n < 0:
        with pytest.raises(ValueError):
            to_weight(n)
    else:
        assert to_weight(n) == n
        if n > 1:
            with pytest.raises(ValueError):
                to_prob(n)
        else:
            assert to_prob(n) == n
