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


def _fold(t: Tree, leaf: Any, combine: Any) -> Any:
    """Iterative post-order fold (no recursion, so depth is not limited by the
    interpreter's recursion limit). ``leaf(Leaf) -> R`` gives a leaf's result;
    ``combine(left_result, right_result) -> R`` gives a node's result."""
    if not isinstance(t, Tree):
        raise TypeError(f"expected a Tree, got {type(t).__name__}")
    results: list[Any] = []
    work: list[tuple[Any, bool]] = [(t, False)]
    while work:
        cur, expanded = work.pop()
        if isinstance(cur, Leaf):
            results.append(leaf(cur))
        elif isinstance(cur, Node):
            if expanded:
                right_res = results.pop()
                left_res = results.pop()
                results.append(combine(left_res, right_res))
            else:
                work.append((cur, True))
                work.append((cur.right, False))
                work.append((cur.left, False))
        else:
            raise TypeError(f"expected a Tree, got {type(cur).__name__}")
    return results[0]


class Tree:
    """Abstract sum type: a Tree is a Leaf or a Node. Never instantiate directly."""

    def __new__(cls, *args: Any, **kwargs: Any) -> Tree:
        # Tree() and Tree.__new__(Tree) must fail; Leaf and Node are subclasses and pass.
        if cls is Tree:
            raise TypeError("Tree is abstract; instantiate Leaf or Node")
        return super().__new__(cls)

    def __post_init__(self) -> None:
        if type(self) is Tree:
            raise TypeError("Tree is abstract; instantiate Leaf or Node")
        # Only Node validates its children; Leaf accepts any value.
        if isinstance(self, Node):
            for child in (self.left, self.right):
                if not isinstance(child, (Leaf, Node)):
                    raise TypeError(f"Node children must be Leaf or Node, got {type(child).__name__}")


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
    return _fold(t, lambda leaf: leaf, lambda left, right: Node(right, left))


def tree_size(t: Tree) -> int:
    """Total number of nodes, leaves included. ``tree_size(Leaf(_)) == 1``;
    ``tree_size(Node(l, r)) == 1 + tree_size(l) + tree_size(r)``."""
    return _fold(t, lambda leaf: 1, lambda left, right: 1 + left + right)


def tree_height(t: Tree) -> int:
    """Edges on the longest root-to-leaf path. ``tree_height(Leaf(_)) == 0``;
    ``tree_height(Node(l, r)) == 1 + max(tree_height(l), tree_height(r))``."""
    return _fold(t, lambda leaf: 0, lambda left, right: 1 + max(left, right))


def triangular(n: int) -> int:
    """``1 + 2 + ... + n`` (``triangular(0) == 0``), computed by ITERATION
    (a loop adding 1..n). It MUST NOT use the closed form ``n*(n+1)//2``: the
    test suite compares the two, and the proof in PROOFS.md is what links them.
    ``TypeError`` if ``n`` is not an ``int`` (``bool`` and ``float`` rejected);
    ``ValueError`` if ``n < 0``."""
    if type(n) is not int:
        raise TypeError(f"triangular expects an int, got {type(n).__name__}")
    if n < 0:
        raise ValueError(f"triangular is undefined for negative n (got {n})")
    total = 0
    for i in range(1, n + 1):
        total += i
    return total
