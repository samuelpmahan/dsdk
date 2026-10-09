"""Seeded sampling and Monte Carlo error, to be compared against exact enumeration (track A3).

Everything here is DETERMINISTIC given ``seed``: the generator is ``random.Random(seed)`` and the ONLY draw primitive is
``rng.random()`` (the uniform float in [0, 1)). No other ``random`` method is used, so results do not depend on the Python
version's implementation of ``choices``/``sample``.

The draw algorithm (inverse CDF), shared by every sampler in dsdk.prob, see :func:`inverse_cdf_draws`::

    cum[i] = float( (w[0] + ... + w[i]) / (w[0] + ... + w[-1]) )         # exact Fractions first, ONE float() at the end
    u = rng.random();   index = bisect.bisect_right(cum, u)

Because ``u < 1.0 == cum[-1]``, ``index`` is a valid position, and a zero-weight outcome is never chosen.

Monte Carlo error. An :class:`Estimate` of a probability from ``trials`` Bernoulli trials with ``successes`` hits has
``p_hat = successes / trials``, standard error ``sqrt(p_hat * (1 - p_hat) / trials)`` and a 95% Wilson score interval
(``Z95``). The Wilson interval is used because the plain ``p_hat +/- 1.96*se`` interval collapses to a point when
``p_hat`` is 0 or 1.
"""
from __future__ import annotations

import bisect
import math
import random
from dataclasses import dataclass
from fractions import Fraction
from typing import Sequence

from dsdk.core import Judgment, Status
from dsdk.graph import topological_order
from dsdk.logic import Formula, evaluate, variables

from .bayesnet import BayesNet
from .worlds import Belief, probability

Z95 = 1.96
"""z-score of the two-sided 95% interval used by :func:`wilson_interval` and :class:`Estimate`."""


def _check_int(x: object, name: str, minimum: int) -> None:
    if isinstance(x, bool) or not isinstance(x, int):
        raise TypeError(f"{name} must be an int, not {type(x).__name__}")
    if x < minimum:
        raise ValueError(f"{name} must be >= {minimum}, got {x}")


def standard_error(successes: int, trials: int) -> float:
    """``sqrt(p_hat * (1 - p_hat) / trials)`` with ``p_hat = successes / trials``. ``trials`` must be an int >= 1 and
    ``0 <= successes <= trials`` (``TypeError`` for bool/non-int, ``ValueError`` for range). Example: (50, 100) -> 0.05."""
    raise NotImplementedError


def wilson_interval(successes: int, trials: int, z: float = Z95) -> tuple[float, float]:
    """Wilson score interval ``(low, high)`` for a binomial proportion::

        p = successes / trials
        centre = (p + z*z / (2*trials)) / (1 + z*z / trials)
        half   = z * sqrt(p*(1-p)/trials + z*z / (4*trials*trials)) / (1 + z*z / trials)
        (low, high) = (centre - half, centre + half)

    clamped into [0, 1]; additionally ``low`` is set to exactly 0.0 when ``successes == 0`` and ``high`` to exactly 1.0 when
    ``successes == trials`` (floating-point rounding must not put ``p_hat`` outside its own interval). Argument checks as in :func:`standard_error`; ``z`` must be a positive finite float/int
    (``TypeError`` / ``ValueError``). Example: (50, 100) -> (0.4038, 0.5962) to 4 decimals. For 0 successes the low end is
    exactly 0.0 and the high end is positive (the interval does not collapse); symmetric for ``successes == trials``.
    """
    raise NotImplementedError


@dataclass(frozen=True)
class Estimate:
    """A Monte Carlo estimate of a probability.

    * ``successes`` / ``trials``  the hits and the number of trials that count (for a conditional estimate ``trials`` is the number
                                  of draws that satisfied the evidence).
    * ``drawn``                   how many draws were made in total (``drawn >= trials``; equal when nothing was rejected).
    * ``p_hat``                   ``successes / trials`` as a float.
    * ``stderr``                  :func:`standard_error`.
    * ``low`` / ``high``          :func:`wilson_interval` at ``Z95``.
    """

    successes: int
    trials: int
    drawn: int
    p_hat: float
    stderr: float
    low: float
    high: float


def make_estimate(successes: int, trials: int, drawn: int) -> Estimate:
    """Build an :class:`Estimate` from the counts (``trials >= 1``; ``drawn >= trials`` else ``ValueError``)."""
    raise NotImplementedError


@dataclass(frozen=True)
class Comparison:
    """Exact value next to a Monte Carlo estimate of it.

    * ``exact``    the exact ``Fraction``.
    * ``estimate`` the :class:`Estimate`.
    * ``error``    ``abs(estimate.p_hat - float(exact))``.
    * ``z_score``  ``error / estimate.stderr``; if ``stderr == 0`` it is ``0.0`` when ``error == 0`` and ``math.inf`` otherwise.
    * ``covered``  ``estimate.low <= float(exact) <= estimate.high``.
    """

    exact: Fraction
    estimate: Estimate
    error: float
    z_score: float
    covered: bool


def make_comparison(exact: Fraction, estimate: Estimate) -> Comparison:
    """Fill a :class:`Comparison` from an exact value and an estimate (formulas in the class docstring)."""
    raise NotImplementedError


def inverse_cdf_draws(weights: Sequence[Fraction], n: int, seed: int) -> tuple[int, ...]:
    """``n`` indices drawn with probability proportional to ``weights`` by the algorithm in the module docstring.

    ``weights`` is a non-empty sequence of non-negative ``Fraction`` with a positive sum (``ValueError`` otherwise;
    non-Fraction elements: ``TypeError``). ``n`` an int >= 0 and ``seed`` an int (bool is rejected; ``TypeError``/``ValueError``).
    ``n == 0`` gives ``()``. The same ``(weights, n, seed)`` always gives the same tuple, and the first ``m`` draws of
    ``n`` draws equal the ``m`` draws made with the same seed (draws are consumed one ``rng.random()`` at a time).
    """
    raise NotImplementedError


def sample_worlds(b: Belief, n: int, seed: int) -> Judgment:
    """``n`` worlds drawn from the normalised belief, as ``KNOWN`` with a tuple of ``world.values`` tuples (so
    ``((("A", True), ("B", False)), ...)``), using :func:`inverse_cdf_draws` over ``[w.weight for w in b.worlds]``.
    ``INVALID`` (reason mentions "zero total weight") if ``b.total == 0`` (nothing to sample). A belief with total > 0 never
    yields a zero-weight world. ``TypeError`` for a non-Belief, bad ``n``/``seed`` as in ``inverse_cdf_draws``
    (checked even when the belief is INVALID: argument errors first).
    """
    raise NotImplementedError


def estimate_probability(b: Belief, query: Formula, n: int, seed: int, given: Formula | None = None) -> Judgment:
    """Estimate ``P(query)`` (or ``P(query | given)`` by REJECTION: draw ``n`` worlds from the prior belief ``b``, keep those
    where ``given`` holds) with a Monte Carlo :class:`Estimate`.

    Draws come from :func:`sample_worlds` (same ``n`` and ``seed``). ``trials`` = number of kept draws (``n`` if ``given`` is
    None), ``successes`` = kept draws where ``query`` is true, ``drawn`` = ``n``. Judgment:

    * ``INVALID``  ``b.total == 0``.
    * ``UNKNOWN``  query/given mention unmodelled variables (reason lists them, like ``probability``), OR no draw is kept
      (``trials == 0``, includes ``n == 0``): the reason says the sampler cannot tell impossible evidence from rare evidence.
      A sampler NEVER reports INVALID for "nothing accepted": only the exact computation can prove the evidence impossible.
    * ``KNOWN``   the Estimate.
    ``TypeError`` for wrong argument types (including ``given``).
    """
    raise NotImplementedError


def compare_with_exact(b: Belief, query: Formula, n: int, seed: int, given: Formula | None = None) -> Judgment:
    """Exact answer next to the sampled one: ``KNOWN`` with a :class:`Comparison`.

    The exact side is ``probability(b, query, given)`` and the sampled side is ``estimate_probability(b, query, n, seed, given)``.
    If the EXACT judgment is not KNOWN it is returned unchanged (exact failures win: impossible evidence stays INVALID even
    though the sampler would say UNKNOWN). Else if the SAMPLED judgment is not KNOWN it is returned unchanged.
    """
    raise NotImplementedError


def forward_sample(net: BayesNet, n: int, seed: int) -> tuple[tuple[tuple[str, bool], ...], ...]:
    """``n`` samples from a Bayes net by FORWARD (ancestral) sampling. Each sample is ``((name, bool), ...)`` with names in
    ``sorted`` order.

    One generator ``random.Random(seed)`` is used for all samples. For each sample, visit the nodes in
    ``dsdk.graph.topological_order(net.structure)`` order; for each node draw ``u = rng.random()`` and set the node true iff
    ``u < float(p)`` where ``p = cpt[node][parent values in structure.predecessors(node) order]``. (So a probability-0 node is
    never true and a probability-1 node always is.) Exactly one ``rng.random()`` per node per sample, in that order.
    ``n`` int >= 0, ``seed`` int (bool rejected); ``TypeError`` for a non-BayesNet.
    """
    raise NotImplementedError
