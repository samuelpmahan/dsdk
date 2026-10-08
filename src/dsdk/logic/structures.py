"""Discrete structures: binary trees and triangular numbers.

These are the executable counterparts of the two induction proofs written in
``tracks/A1/PROOFS.md``. Tests can only sample behaviour; the proofs establish
it for all inputs.

Naming note: the tree measures are ``tree_size`` / ``tree_height`` (not
``size`` / ``height``) so ``dsdk.logic`` can export them next to
``formula.size`` without a name clash.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


class Tree:
    """Base class for binary trees. Never instantiate directly."""

    def __post_init__(self) -> None:
        raise NotImplementedError


@dataclass(frozen=True)
class Leaf(Tree):
    """A leaf carrying any value. (Nothing is validated about ``value``.)"""

    value: Any


@dataclass(frozen=True)
class Node(Tree):
    """An internal node; ``left`` and ``right`` must be :class:`Tree` (else
    ``TypeError``, checked in ``__post_init__``). Every Node has exactly two
    children: there is no empty tree."""

    left: Tree
    right: Tree


def mirror(t: Tree) -> Tree:
    """Swap left and right at EVERY node, recursively; leaves are unchanged.
    ``mirror(Leaf(v)) == Leaf(v)``; ``mirror(Node(l, r)) == Node(mirror(r), mirror(l))``.
    Returns a new tree; the input is immutable anyway. ``TypeError`` for
    non-trees. Must handle depth 200 under the default recursion limit."""
    raise NotImplementedError


def tree_size(t: Tree) -> int:
    """Total number of nodes, leaves included. ``tree_size(Leaf(_)) == 1``;
    ``tree_size(Node(l, r)) == 1 + tree_size(l) + tree_size(r)``."""
    raise NotImplementedError


def tree_height(t: Tree) -> int:
    """Edges on the longest root-to-leaf path. ``tree_height(Leaf(_)) == 0``;
    ``tree_height(Node(l, r)) == 1 + max(tree_height(l), tree_height(r))``."""
    raise NotImplementedError


def triangular(n: int) -> int:
    """``1 + 2 + ... + n`` (``triangular(0) == 0``), computed by ITERATION
    (a loop adding 1..n). It MUST NOT use the closed form ``n*(n+1)//2``: the
    test suite compares the two, and the proof in PROOFS.md is what links them.
    ``TypeError`` if ``n`` is not an ``int`` (``bool`` and ``float`` rejected);
    ``ValueError`` if ``n < 0``."""
    raise NotImplementedError
