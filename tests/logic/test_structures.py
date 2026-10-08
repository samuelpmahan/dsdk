"""Contract tests for dsdk.logic.structures: binary trees (mirror/size/height) and triangular numbers."""
import ast
import inspect

import pytest
from hypothesis import given, strategies as st

from dsdk.logic import Leaf, Node, Tree, mirror, tree_height, tree_size, triangular

DEPTH = 200


def trees():
    return st.recursive(st.integers(-5, 5).map(Leaf), lambda c: st.builds(Node, c, c), max_leaves=20)


def leaves(t):
    """Reference: leaf values left to right."""
    return [t.value] if isinstance(t, Leaf) else leaves(t.left) + leaves(t.right)


def left_comb(n):
    """A left-leaning chain with n Node levels and n+1 leaves."""
    t = Leaf(0)
    for i in range(n):
        t = Node(t, Leaf(i + 1))
    return t


# =========================== construction ===================================
def test_leaf_and_node_are_trees_with_value_equality():
    """Structural equality/hash so mirror(mirror(t)) == t is meaningful."""
    t1, t2 = Node(Leaf(1), Leaf(2)), Node(Leaf(1), Leaf(2))
    assert isinstance(t1, Tree) and isinstance(Leaf(1), Tree)
    assert t1 == t2 and hash(t1) == hash(t2) and t1 != Node(Leaf(2), Leaf(1))
    assert Leaf(1) != Leaf(2) and Leaf(1) != Node(Leaf(1), Leaf(1))


@pytest.mark.parametrize("bad", [1, None, "x", [(1,)]])
def test_node_children_must_be_trees(bad):
    """Every Node has exactly two Tree children; a raw value is a TypeError."""
    with pytest.raises(TypeError):
        Node(bad, Leaf(1))
    with pytest.raises(TypeError):
        Node(Leaf(1), bad)


def test_leaf_accepts_any_value_including_none():
    """Leaf stores anything (the proofs never inspect it)."""
    assert Leaf(None).value is None and Leaf([1]).value == [1]


# =========================== mirror =========================================
def test_mirror_base_and_step_cases():
    """Mirrors the two cases of the structural induction: leaf unchanged; node swaps and recurses."""
    assert mirror(Leaf(7)) == Leaf(7)
    assert mirror(Node(Leaf(1), Leaf(2))) == Node(Leaf(2), Leaf(1))
    t = Node(Node(Leaf(1), Leaf(2)), Leaf(3))
    assert mirror(t) == Node(Leaf(3), Node(Leaf(2), Leaf(1))), "swap must apply at EVERY level, not just the root"


def test_mirror_of_symmetric_tree_is_itself():
    """A palindromic tree is a fixed point (rules out a mirror that returns a constant)."""
    t = Node(Node(Leaf(1), Leaf(1)), Node(Leaf(1), Leaf(1)))
    assert mirror(t) == t


def test_mirror_is_not_identity_on_asymmetric_trees():
    """Guards against a do-nothing mirror."""
    t = Node(Leaf(1), Leaf(2))
    assert mirror(t) != t


@pytest.mark.parametrize("bad", [1, None, "x"])
def test_mirror_rejects_non_trees(bad):
    """Non-trees are a TypeError."""
    with pytest.raises(TypeError):
        mirror(bad)


def test_mirror_deep_tree_depth_200():
    """Depth 200 must not overflow the default recursion limit; double mirror restores it."""
    t = left_comb(DEPTH)
    m = mirror(t)
    assert tree_height(m) == DEPTH and leaves(m) == list(reversed(leaves(t)))
    assert mirror(m) == t


@given(trees())
def test_property_mirror_is_an_involution(t):
    """mirror(mirror(t)) == t for every tree. Sampling is evidence; PROOFS.md proves it by structural induction."""
    assert mirror(mirror(t)) == t


@given(trees())
def test_property_mirror_preserves_shape_measures_and_reverses_leaves(t):
    """mirror keeps size and height and reverses the left-to-right leaf order."""
    m = mirror(t)
    assert tree_size(m) == tree_size(t) and tree_height(m) == tree_height(t)
    assert leaves(m) == list(reversed(leaves(t)))


# =========================== size / height ==================================
def test_size_and_height_base_cases():
    """A single Leaf: size 1, height 0."""
    assert tree_size(Leaf(None)) == 1 and tree_height(Leaf(None)) == 0


def test_size_and_height_small_trees():
    """Hand-computed values: size counts internal nodes too; height counts edges on the longest path."""
    t = Node(Node(Leaf(1), Leaf(2)), Leaf(3))
    assert tree_size(t) == 5 and tree_height(t) == 2
    assert tree_size(Node(Leaf(1), Leaf(2))) == 3 and tree_height(Node(Leaf(1), Leaf(2))) == 1


def test_height_uses_the_longer_side():
    """Height is a max, not a sum or the left side only."""
    deep_right = Node(Leaf(0), Node(Leaf(0), Node(Leaf(0), Leaf(0))))
    assert tree_height(deep_right) == 3 and tree_height(mirror(deep_right)) == 3


def test_size_and_height_deep_tree():
    """Depth-200 comb: 2n+1 nodes, height n."""
    t = left_comb(DEPTH)
    assert tree_size(t) == 2 * DEPTH + 1 and tree_height(t) == DEPTH


@pytest.mark.parametrize("bad", [1, None, "x"])
def test_size_height_reject_non_trees(bad):
    """Non-trees are a TypeError."""
    with pytest.raises(TypeError):
        tree_size(bad)
    with pytest.raises(TypeError):
        tree_height(bad)


@given(trees())
def test_property_full_binary_tree_counts(t):
    """In a full binary tree nodes = 2*leaves - 1 and height < size; ties tree_size to an independent leaf count."""
    n = len(leaves(t))
    assert tree_size(t) == 2 * n - 1
    assert 0 <= tree_height(t) <= n - 1


# =========================== triangular =====================================
@pytest.mark.parametrize("n, expected", [(0, 0), (1, 1), (2, 3), (3, 6), (4, 10), (5, 15), (10, 55), (100, 5050)])
def test_triangular_known_values(n, expected):
    """Base case n=0 is 0 (the empty sum); then 1, 3, 6, ..."""
    assert triangular(n) == expected


def test_triangular_matches_closed_form_for_0_to_2000():
    """SAMPLES n(n+1)/2 for n in 0..2000. This test does NOT prove the claim for all n -- tracks/A1/PROOFS.md does (by induction)."""
    for n in range(2001):
        assert triangular(n) == n * (n + 1) // 2, f"triangular({n}) disagrees with n(n+1)/2"


@given(st.integers(1, 2000))
def test_property_triangular_satisfies_the_recurrence(n):
    """T(n) = T(n-1) + n: the inductive step, checked on samples (not a proof)."""
    assert triangular(n) == triangular(n - 1) + n


def test_triangular_large_n_is_exact_integer():
    """Big n stays an exact int (no float drift)."""
    assert triangular(200_000) == 200_000 * 200_001 // 2 and type(triangular(5)) is int


@pytest.mark.parametrize("bad", [1.0, "3", None, True, 2.5])
def test_triangular_rejects_non_ints(bad):
    """Only real ints (not bool, not float) are accepted: TypeError."""
    with pytest.raises(TypeError):
        triangular(bad)


@pytest.mark.parametrize("bad", [-1, -100])
def test_triangular_rejects_negative(bad):
    """The sum 1..n is undefined for negative n: ValueError."""
    with pytest.raises(ValueError):
        triangular(bad)


def test_triangular_is_computed_by_iteration_not_the_closed_form():
    """If triangular used n*(n+1)//2, comparing it with that formula would be circular. Source must loop/sum and avoid *, /, //."""
    triangular(3)  # surfaces NotImplementedError for the stub before the structural check
    tree = ast.parse(inspect.getsource(triangular).lstrip())
    banned = [n for n in ast.walk(tree) if isinstance(n, ast.BinOp) and isinstance(n.op, (ast.Mult, ast.Div, ast.FloorDiv))]
    iterates = any(isinstance(n, (ast.For, ast.While, ast.ListComp, ast.GeneratorExp, ast.SetComp)) for n in ast.walk(tree)) or any(
        isinstance(n, ast.Call) and getattr(n.func, "id", "") == "sum" for n in ast.walk(tree)
    )
    assert not banned, "triangular must not use * / // (closed form)"
    assert iterates, "triangular must iterate (for/while/comprehension/sum)"
