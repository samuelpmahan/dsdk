"""Exact numbers for dsdk.prob: every probability and weight is a ``fractions.Fraction``.

Why exact: the Wumpus oracle says the posterior is 4/9, 4/9, 1/9, not 0.4444...; a test can compare ``Fraction(4, 9)``
for equality, and sampler error is then measured against a true value instead of another float.

Accepted inputs for :func:`to_weight` / :func:`to_prob`:

* ``int`` (but NOT ``bool``: ``True`` is a ``TypeError``) and ``Fraction``;
* ``float`` that is finite, converted through its SHORTEST DECIMAL REPRESENTATION: ``Fraction(repr(x))``. So ``0.2`` becomes
  exactly ``1/5`` (not the 53-bit binary neighbour of 0.2) and ``1e-07`` becomes ``1/10000000``. ``nan``/``inf`` are a ``ValueError``.

Everything else (``str``, ``Decimal``, ``None``, ``complex``, numpy scalars) is a ``TypeError``. Check order: type
(``TypeError``), finiteness (``ValueError``), range (``ValueError``).
"""
from __future__ import annotations

import math
from fractions import Fraction


def to_weight(x: object, name: str = "weight") -> Fraction:
    """Convert ``x`` to a non-negative ``Fraction`` (no upper bound). ``name`` is used in the error message.

    ``TypeError`` for bool and unsupported types; ``ValueError`` for nan, inf and negative values.
    """
    raise NotImplementedError


def to_prob(x: object, name: str = "probability") -> Fraction:
    """Like :func:`to_weight` but the value must also be <= 1 (``ValueError`` otherwise). ``0`` and ``1`` are legal."""
    raise NotImplementedError
