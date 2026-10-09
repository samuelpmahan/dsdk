"""Contract tests for dsdk.graph.relational: the self-join and adjacency composition must agree (as sets)."""
from collections import Counter

import pytest
from hypothesis import given
from hypothesis import strategies as st

from dsdk.graph import Graph, GraphError, two_hop_counts_graph, two_hop_join, two_hop_matrix, two_hop_pairs, \
    two_hop_pairs_graph


def rec(*pairs):
    return [{"source": a, "target": b} for a, b in pairs]


def test_two_hop_join_basic_chain():
    """a->b->c joins into the single pair (a, c); an edge alone joins into nothing."""
    assert two_hop_join(rec(("a", "b"), ("b", "c"))) == [("a", "c")]
    assert two_hop_join(rec(("a", "b"))) == []
    assert two_hop_join([]) == []


def test_two_hop_join_order_is_outer_then_inner_loop():
    """Output order is defined: r1 in input order, r2 in input order."""
    r = rec(("a", "b"), ("a", "c"), ("b", "d"), ("c", "d"), ("b", "e"))
    assert two_hop_join(r) == [("a", "d"), ("a", "e"), ("a", "d")]


def test_duplicate_records_multiply_in_the_join_but_not_in_the_graph():
    """Join multiplication: a->b twice and b->c twice give FOUR (a, c) rows; the graph merges duplicates and counts 1."""
    r = rec(("a", "b"), ("a", "b"), ("b", "c"), ("b", "c"))
    assert Counter(two_hop_join(r)) == {("a", "c"): 4}, "2 rows x 2 rows = 4 joined rows"
    g = Graph.from_records(r)
    assert two_hop_counts_graph(g) == {("a", "c"): 1}, "the graph has one distinct middle node b"
    assert two_hop_pairs(r) == two_hop_pairs_graph(g) == frozenset({("a", "c")}), "but the SETS of pairs agree"


def test_counts_agree_when_there_are_no_duplicate_records():
    """Without duplicate rows every multiplicity is 1, so join counts and graph counts coincide."""
    r = rec(("a", "b"), ("a", "c"), ("b", "d"), ("c", "d"))
    assert Counter(two_hop_join(r)) == two_hop_counts_graph(Graph.from_records(r)) == {("a", "d"): 2}


def test_two_hop_walks_may_return_to_the_start_and_use_self_loops():
    """Walks need not be simple: a->b->a gives (a, a); a self-loop a->a composes with a->c to give (a, c)."""
    assert two_hop_pairs(rec(("a", "b"), ("b", "a"))) == frozenset({("a", "a"), ("b", "b")})
    assert two_hop_pairs(rec(("a", "a"), ("a", "c"))) == frozenset({("a", "a"), ("a", "c")})
    g = Graph.from_records(rec(("a", "a"), ("a", "c")))
    assert two_hop_pairs_graph(g) == two_hop_pairs(rec(("a", "a"), ("a", "c")))


def test_two_hop_custom_key_names():
    """source=/target= select the columns, as in Graph.from_records."""
    r = [{"from": 1, "to": 2}, {"from": 2, "to": 3}]
    assert two_hop_pairs(r, source="from", target="to") == frozenset({(1, 3)})


def test_two_hop_join_missing_key_is_graph_error():
    """A row without the key columns is a GraphError (same contract as from_records)."""
    with pytest.raises(GraphError):
        two_hop_join([{"source": "a"}, {"source": "b", "target": "c"}])


def test_two_hop_matrix_is_the_square_of_the_adjacency_matrix():
    """A 3-chain a->b->c plus a->c: A squared has a single 1 at (a, c) from a->b->c."""
    g = Graph.from_edges([("a", "b"), ("b", "c"), ("a", "c")], ["a", "b", "c"])
    assert two_hop_matrix(g) == ((0, 0, 1), (0, 0, 0), (0, 0, 0))


def test_two_hop_matrix_counts_distinct_middle_nodes():
    """Two different middle nodes give an entry of 2 (this is a count of middles, not of rows)."""
    g = Graph.from_edges([("a", "b"), ("a", "c"), ("b", "d"), ("c", "d")], ["a", "b", "c", "d"])
    assert two_hop_matrix(g)[0][3] == 2 and two_hop_counts_graph(g) == {("a", "d"): 2}


def test_two_hop_on_undirected_graph_includes_return_trips():
    """Undirected a-b: a-b-a is a 2-walk, so (a, a) and (b, b) are 2-hop pairs; the matrix diagonal is the degree."""
    g = Graph.from_edges([("a", "b")], directed=False)
    assert two_hop_pairs_graph(g) == frozenset({("a", "a"), ("b", "b")})
    assert two_hop_matrix(g) == ((1, 0), (0, 1))


def test_empty_inputs():
    """Empty record lists and empty graphs give empty answers (and an empty matrix)."""
    assert two_hop_pairs([]) == frozenset() and two_hop_pairs_graph(Graph.from_edges([])) == frozenset()
    assert two_hop_matrix(Graph.from_edges([])) == () and two_hop_counts_graph(Graph.from_edges([])) == {}


@st.composite
def record_lists(draw):
    n = draw(st.integers(min_value=1, max_value=6))
    node = st.integers(min_value=0, max_value=n - 1)
    return draw(st.lists(st.tuples(node, node), max_size=10))  # repeats allowed on purpose


@given(record_lists())
def test_relational_and_graph_two_hop_pairs_agree_as_sets(pairs):
    """Property (the point of this module): SELECT DISTINCT self-join == adjacency composition, duplicates or not."""
    records = rec(*pairs)
    assert two_hop_pairs(records) == two_hop_pairs_graph(Graph.from_records(records))


@given(record_lists())
def test_join_counts_are_products_of_multiplicities_and_graph_counts_are_middle_nodes(pairs):
    """Property: join count(a,c) = sum_b m(a,b)*m(b,c); graph count(a,c) = #distinct b; they are equal iff no
    duplicate rows are involved."""
    records = rec(*pairs)
    m = Counter(pairs)
    expected_join = Counter()
    middles = Counter()
    for (a, b), m1 in m.items():
        for (b2, c), m2 in m.items():
            if b == b2:
                expected_join[(a, c)] += m1 * m2
                middles[(a, c)] += 1
    assert Counter(two_hop_join(records)) == expected_join
    g = Graph.from_records(records)
    assert two_hop_counts_graph(g) == dict(middles)
    matrix = two_hop_matrix(g)
    for (a, c), count in middles.items():
        assert matrix[g.index_of(a)][g.index_of(c)] == count, "matrix entry must equal the middle-node count"
    assert sum(map(sum, matrix)) == sum(middles.values())
    if len(m) == len(pairs):  # no duplicate rows
        assert Counter(two_hop_join(records)) == dict(middles)
