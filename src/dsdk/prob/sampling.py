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
    _check_int(trials, "trials", 1)
    _check_int(successes, "successes", 0)
    if successes > trials:
        raise ValueError(f"successes ({successes}) must not exceed trials ({trials})")
    p = successes / trials
    return math.sqrt(p * (1 - p) / trials)


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
    _check_int(trials, "trials", 1)
    _check_int(successes, "successes", 0)
    if successes > trials:
        raise ValueError(f"successes ({successes}) must not exceed trials ({trials})")
    if isinstance(z, bool) or not isinstance(z, (int, float)):
        raise TypeError(f"z must be a float, not {type(z).__name__}")
    if not math.isfinite(z) or z <= 0:
        raise ValueError(f"z must be positive and finite, got {z}")
    p = successes / trials
    zz = z * z
    denom = 1 + zz / trials
    centre = (p + zz / (2 * trials)) / denom
    half = z * math.sqrt(p * (1 - p) / trials + zz / (4 * trials * trials)) / denom
    low = max(0.0, min(1.0, centre - half))
    high = max(0.0, min(1.0, centre + half))
    if successes == 0:
        low = 0.0
    if successes == trials:
        high = 1.0
    return (low, high)


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
    _check_int(trials, "trials", 1)
    _check_int(successes, "successes", 0)
    if successes > trials:
        raise ValueError(f"successes ({successes}) must not exceed trials ({trials})")
    _check_int(drawn, "drawn", 0)
    if drawn < trials:
        raise ValueError(f"drawn ({drawn}) must be >= trials ({trials})")
    low, high = wilson_interval(successes, trials)
    return Estimate(successes, trials, drawn, successes / trials, standard_error(successes, trials), low, high)


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
    target = float(exact)
    error = abs(estimate.p_hat - target)
    if estimate.stderr > 0:
        z_score = error / estimate.stderr
    elif error == 0:
        z_score = 0.0
    else:
        z_score = math.inf
    covered = estimate.low <= target <= estimate.high
    return Comparison(exact=exact, estimate=estimate, error=error, z_score=z_score, covered=covered)


def inverse_cdf_draws(weights: Sequence[Fraction], n: int, seed: int) -> tuple[int, ...]:
    """``n`` indices drawn with probability proportional to ``weights`` by the algorithm in the module docstring.

    ``weights`` is a non-empty sequence of non-negative ``Fraction`` with a positive sum (``ValueError`` otherwise;
    non-Fraction elements: ``TypeError``). ``n`` an int >= 0 and ``seed`` an int (bool is rejected; ``TypeError``/``ValueError``).
    ``n == 0`` gives ``()``. The same ``(weights, n, seed)`` always gives the same tuple, and the first ``m`` draws of
    ``n`` draws equal the ``m`` draws made with the same seed (draws are consumed one ``rng.random()`` at a time).
    """
    if not isinstance(weights, Sequence) or isinstance(weights, (str, bytes)):
        raise TypeError("weights must be a sequence of Fraction")
    if len(weights) == 0:
        raise ValueError("weights must be non-empty")
    for w in weights:
        if not isinstance(w, Fraction):
            raise TypeError(f"weights must be Fraction, not {type(w).__name__}")
        if w < 0:
            raise ValueError(f"weights must be non-negative, got {w}")
    _check_int(n, "n", 0)
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise TypeError(f"seed must be an int, not {type(seed).__name__}")
    total = sum(weights, Fraction(0))
    if total <= 0:
        raise ValueError("weights must have a positive sum")
    cum: list[float] = []
    running = Fraction(0)
    for w in weights:
        running += w
        cum.append(float(running / total))
    rng = random.Random(seed)
    return tuple(bisect.bisect_right(cum, rng.random()) for _ in range(n))


def sample_worlds(b: Belief, n: int, seed: int) -> Judgment:
    """``n`` worlds drawn from the normalised belief, as ``KNOWN`` with a tuple of ``world.values`` tuples (so
    ``((("A", True), ("B", False)), ...)``), using :func:`inverse_cdf_draws` over ``[w.weight for w in b.worlds]``.
    ``INVALID`` (reason mentions "zero total weight") if ``b.total == 0`` (nothing to sample). A belief with total > 0 never
    yields a zero-weight world. ``TypeError`` for a non-Belief, bad ``n``/``seed`` as in ``inverse_cdf_draws``
    (checked even when the belief is INVALID: argument errors first).
    """
    if not isinstance(b, Belief):
        raise TypeError(f"sample_worlds() takes a Belief, not {type(b).__name__}")
    _check_int(n, "n", 0)
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise TypeError(f"seed must be an int, not {type(seed).__name__}")
    if b.total == 0:
        return Judgment(Status.INVALID, None, "belief has zero total weight: nothing to sample")
    picks = inverse_cdf_draws([w.weight for w in b.worlds], n, seed)
    return Judgment(Status.KNOWN, tuple(b.worlds[i].values for i in picks), "")


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
    if not isinstance(b, Belief):
        raise TypeError(f"estimate_probability() takes a Belief, not {type(b).__name__}")
    if not isinstance(query, Formula):
        raise TypeError(f"query must be a Formula, not {type(query).__name__}")
    if given is not None and not isinstance(given, Formula):
        raise TypeError(f"given must be a Formula or None, not {type(given).__name__}")
    _check_int(n, "n", 0)
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise TypeError(f"seed must be an int, not {type(seed).__name__}")
    mentioned = set(variables(query))
    if given is not None:
        mentioned |= set(variables(given))
    missing = mentioned - set(b.variables)
    if missing:
        return Judgment(Status.UNKNOWN, None, "unmodelled variables: " + ", ".join(sorted(missing)))
    drawn = sample_worlds(b, n, seed)
    if drawn.status is not Status.KNOWN:
        return drawn
    trials = 0
    successes = 0
    for world in drawn.value:
        a = dict(world)
        if given is not None and not evaluate(given, a):
            continue
        trials += 1
        if evaluate(query, a):
            successes += 1
    if trials == 0:
        return Judgment(
            Status.UNKNOWN,
            None,
            "no draw satisfied the evidence: the sampler cannot tell impossible evidence from rare evidence",
        )
    return Judgment(Status.KNOWN, make_estimate(successes, trials, n), "")


def compare_with_exact(b: Belief, query: Formula, n: int, seed: int, given: Formula | None = None) -> Judgment:
    """Exact answer next to the sampled one: ``KNOWN`` with a :class:`Comparison`.

    The exact side is ``probability(b, query, given)`` and the sampled side is ``estimate_probability(b, query, n, seed, given)``.
    If the EXACT judgment is not KNOWN it is returned unchanged (exact failures win: impossible evidence stays INVALID even
    though the sampler would say UNKNOWN). Else if the SAMPLED judgment is not KNOWN it is returned unchanged.
    """
    exact = probability(b, query, given)
    if exact.status is not Status.KNOWN:
        return exact
    sampled = estimate_probability(b, query, n, seed, given)
    if sampled.status is not Status.KNOWN:
        return sampled
    return Judgment(Status.KNOWN, make_comparison(exact.value, sampled.value), "")


def forward_sample(net: BayesNet, n: int, seed: int) -> tuple[tuple[tuple[str, bool], ...], ...]:
    """``n`` samples from a Bayes net by FORWARD (ancestral) sampling. Each sample is ``((name, bool), ...)`` with names in
    ``sorted`` order.

    One generator ``random.Random(seed)`` is used for all samples. For each sample, visit the nodes in
    ``dsdk.graph.topological_order(net.structure)`` order; for each node draw ``u = rng.random()`` and set the node true iff
    ``u < float(p)`` where ``p = cpt[node][parent values in structure.predecessors(node) order]``. (So a probability-0 node is
    never true and a probability-1 node always is.) Exactly one ``rng.random()`` per node per sample, in that order.
    ``n`` int >= 0, ``seed`` int (bool rejected); ``TypeError`` for a non-BayesNet.
    """
    if not isinstance(net, BayesNet):
        raise TypeError(f"forward_sample() takes a BayesNet, not {type(net).__name__}")
    _check_int(n, "n", 0)
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise TypeError(f"seed must be an int, not {type(seed).__name__}")
    order = topological_order(net.structure)
    rng = random.Random(seed)
    samples = []
    for _ in range(n):
        value: dict[str, bool] = {}
        for node in order:
            p = net.cpts[node][tuple(value[q] for q in net.structure.predecessors(node))]
            value[node] = rng.random() < float(p)
        samples.append(tuple((name, value[name]) for name in sorted(value)))
    return tuple(samples)
