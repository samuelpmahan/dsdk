"""Contract tests for dsdk.graph.model: construction rules, duplicates, self-loops, views, relabelling."""
import dataclasses
import math

import pytest
from hypothesis import given
from hypothesis import strategies as st

from dsdk.core import Status
from dsdk.graph import Edge, Graph, GraphError, MissingNodeError

from graph_oracles import edge_lists, pair_set


def build(edges, nodes=None, directed=True, closed_world=False):
    return Graph.from_edges(edges, nodes, directed=directed, closed_world=closed_world)


# ----------------------------------------------------------------------------- node set and order
def test_nodes_are_inferred_in_first_appearance_order():
    """Without `nodes=`, order is source-then-target per edge as listed; it fixes every later tie-break."""
    g = build([("c", "a"), ("a", "b")])
    assert g.nodes == ("c", "a", "b"), "first-appearance order: c, a (edge 1) then b (edge 2)"


def test_declared_nodes_fix_the_order_and_drop_repeats():
    """`nodes=` is the whole node set in the given order; a repeated declaration is dropped after its first use."""
    g = build([("b", "a")], nodes=["a", "b", "a", "z"])
    assert g.nodes == ("a", "b", "z"), "declared order wins over edge order; the second 'a' is dropped"


def test_declared_isolated_node_exists_with_no_neighbours():
    """An isolated node can only be introduced through `nodes=`; it must show up in the views with no edges."""
    g = build([("a", "b")], nodes=["a", "b", "lonely"])
    assert g.has_node("lonely") and g.neighbors("lonely") == ()
    assert g.adjacency()["lonely"] == (), "isolated nodes map to an empty tuple, they are not omitted"


def test_missing_endpoint_raises_unless_declared():
    """An edge to an undeclared node is an error (typo protection) unless the caller lists the node."""
    with pytest.raises(MissingNodeError):
        build([("a", "ghost")], nodes=["a"])
    g = build([("a", "ghost")], nodes=["a", "ghost"])
    assert g.has_edge("a", "ghost"), "declaring the node makes the same edge legal"


def test_missing_endpoint_message_names_the_node():
    """The error text must name the offending node so a data error can be found in a long edge list."""
    with pytest.raises(MissingNodeError, match="ghost"):
        build([("a", "ghost")], nodes=["a"])


def test_missing_node_error_is_a_graph_error_and_value_error():
    """Callers may catch ValueError generically; the class hierarchy is part of the contract."""
    with pytest.raises(ValueError):
        build([("a", "b")], nodes=[])
    with pytest.raises(GraphError):
        build([("a", "b")], nodes=["a"])


def test_empty_graph():
    """No edges and no nodes is a legal graph with empty views (boundary case for every algorithm)."""
    g = build([])
    assert g.nodes == () and g.edges == () and g.adjacency() == {} and g.adjacency_matrix() == ()


def test_one_shot_iterables_are_consumed_once():
    """`edges` and `nodes` may be generators; the constructor must not iterate them twice."""
    g = build(((i, i + 1) for i in range(3)), nodes=(i for i in range(4)))
    assert g.nodes == (0, 1, 2, 3) and len(g.edges) == 3


def test_edge_input_forms_are_equivalent():
    """Edge objects, (u, v) and (u, v, w) tuples build equal graphs when they describe the same edges."""
    assert build([Edge("a", "b"), Edge("b", "c", 2.5)]) == build([("a", "b"), ("b", "c", 2.5)])


@pytest.mark.parametrize("bad", [("a",), ("a", "b", 1, 2), "ab", 5, None, ["a", "b"]])
def test_malformed_edge_items_are_type_errors(bad):
    """Only Edge or 2/3-tuples are edges; anything else is a TypeError, not a silent skip."""
    with pytest.raises(TypeError):
        build([bad])


# ----------------------------------------------------------------------------------- canonical form
def test_edges_are_sorted_by_node_order_and_independent_of_input_order():
    """Normalisation: equal edge sets give EQUAL graphs regardless of listing order (needed for determinism)."""
    nodes = ["a", "b", "c"]
    g1 = build([("a", "b"), ("c", "a"), ("b", "c")], nodes)
    g2 = build([("b", "c"), ("a", "b"), ("c", "a")], nodes)
    assert g1 == g2
    assert [(e.source, e.target) for e in g1.edges] == [("a", "b"), ("b", "c"), ("c", "a")], \
        "edges must be sorted by (index of source, index of target)"


def test_undirected_edges_are_stored_low_index_first():
    """Undirected storage orientation is canonical (lower node index first), so (b, a) and (a, b) coincide."""
    g = build([("b", "a")], nodes=["a", "b"], directed=False)
    assert [(e.source, e.target) for e in g.edges] == [("a", "b")]


def test_graph_is_immutable():
    """Graphs are frozen so they can be shared and hashed safely."""
    g = build([("a", "b")])
    with pytest.raises(dataclasses.FrozenInstanceError):
        g.directed = False
    assert isinstance(hash(g), int), "a Graph of hashable nodes must be hashable"


def test_flags_are_stored():
    """directed defaults to True and closed_world to False (the open-world default is deliberate)."""
    g = build([("a", "b")])
    assert g.directed is True and g.closed_world is False
    h = build([("a", "b")], directed=False, closed_world=True)
    assert h.directed is False and h.closed_world is True


# --------------------------------------------------------------------------------------- duplicates
def test_duplicate_directed_edges_merge_into_one():
    """Repeated (u, v) rows collapse to a single edge, so multiplicity never leaks into the graph."""
    g = build([("a", "b"), ("a", "b"), ("a", "b")])
    assert len(g.edges) == 1 and g.neighbors("a") == ("b",)


def test_antiparallel_edges_are_distinct_when_directed():
    """a->b and b->a are two different directed edges; merging them would erase direction."""
    g = build([("a", "b"), ("b", "a")])
    assert len(g.edges) == 2 and g.has_edge("a", "b") and g.has_edge("b", "a")


def test_antiparallel_edges_merge_when_undirected():
    """In an undirected graph (a, b) and (b, a) are the same edge, stored once."""
    g = build([("a", "b"), ("b", "a")], directed=False)
    assert len(g.edges) == 1


@pytest.mark.parametrize(
    "first,second,expected",
    [
        (Status.UNKNOWN, Status.KNOWN, Status.KNOWN),
        (Status.KNOWN, Status.NOT_OBSERVED, Status.KNOWN),
        (Status.NOT_OBSERVED, Status.UNKNOWN, Status.UNKNOWN),
        (Status.UNKNOWN, Status.NOT_OBSERVED, Status.UNKNOWN),
        (Status.NOT_OBSERVED, Status.NOT_OBSERVED, Status.NOT_OBSERVED),
    ],
)
def test_duplicate_edges_keep_the_strongest_evidence(first, second, expected):
    """A KNOWN observation must not be weakened by an extra uncertain claim, in either listing order."""
    for pair in ([Edge("a", "b", evidence=first), Edge("a", "b", evidence=second)],
                 [Edge("a", "b", evidence=second), Edge("a", "b", evidence=first)]):
        assert build(pair).get_edge("a", "b").evidence is expected, \
            "strength order is KNOWN > UNKNOWN > NOT_OBSERVED, independent of listing order"


def test_duplicate_edges_with_equal_weights_merge_and_unequal_weights_raise():
    """Conflicting weights cannot be merged honestly, so they are an error; equal ones are fine."""
    assert build([("a", "b", 2), ("a", "b", 2)]).get_edge("a", "b").weight == 2
    with pytest.raises(GraphError):
        build([("a", "b", 2), ("a", "b", 3)])
    with pytest.raises(GraphError):
        build([("a", "b", 2), ("a", "b")])  # a weight and "no weight" are different


def test_duplicate_labels_are_joined_sorted_and_distinct():
    """Merged labels become 'x,y' (sorted, distinct), so lineage keeps both input names; None stays None."""
    g = build([Edge("a", "b", label="y"), Edge("a", "b", label="x"), Edge("a", "b", label="y")])
    assert g.get_edge("a", "b").label == "x,y"
    assert build([("a", "b"), ("a", "b")]).get_edge("a", "b").label is None


# ----------------------------------------------------------------------------------------- self-loops
def test_directed_self_loop_is_kept_and_is_its_own_successor():
    """A self-loop is a real edge: it must survive construction and show in neighbours and the matrix diagonal."""
    g = build([("a", "a"), ("a", "b")])
    assert g.has_edge("a", "a") and g.neighbors("a") == ("a", "b")
    assert g.adjacency_matrix() == ((1, 1), (0, 0))


def test_undirected_self_loop_appears_once():
    """Undirected self-loop: ONE edge, listed once in the neighbour list, and 1 (not 2) on the diagonal."""
    g = build([("a", "a")], directed=False)
    assert len(g.edges) == 1 and g.neighbors("a") == ("a",) and g.adjacency_matrix() == ((1,),)


# ------------------------------------------------------------------------------------ value validation
@pytest.mark.parametrize("w", [True, "1", [1]])
def test_non_numeric_weights_are_type_errors(w):
    """bool is not a weight (True == 1 would hide bugs); strings and lists are not numbers."""
    with pytest.raises(TypeError):
        build([("a", "b", w)])


@pytest.mark.parametrize("w", [math.nan, math.inf, -math.inf])
def test_non_finite_weights_are_value_errors(w):
    """nan/inf weights break comparisons, so they are rejected up front."""
    with pytest.raises(ValueError):
        build([("a", "b", w)])


def test_zero_and_negative_weights_are_legal():
    """0 and negative numbers are numbers; absence is expressed by None in weight_matrix, not by 0."""
    g = build([("a", "b", 0), ("b", "a", -2.5)])
    assert g.get_edge("a", "b").weight == 0 and g.get_edge("b", "a").weight == -2.5


@pytest.mark.parametrize("status", [Status.INVALID, Status.NOT_APPLICABLE])
def test_only_three_statuses_may_label_an_edge(status):
    """INVALID / NOT_APPLICABLE do not describe an edge's evidence, so they are rejected with ValueError."""
    with pytest.raises(ValueError):
        build([Edge("a", "b", evidence=status)])


@pytest.mark.parametrize("bad", ["known", 1, None])
def test_evidence_must_be_a_status_member(bad):
    """A plain string is NOT a Status (same rule as Judgment): TypeError."""
    with pytest.raises(TypeError):
        build([Edge("a", "b", evidence=bad)])


def test_label_must_be_str_or_none():
    """Labels are text; a number is a TypeError."""
    with pytest.raises(TypeError):
        build([Edge("a", "b", label=3)])


# --------------------------------------------------------------------------------------------- views
def test_neighbors_are_in_node_order_not_insertion_order():
    """Neighbour lists follow node order so BFS/DFS tie-breaks do not depend on how edges were listed."""
    g = build([("a", "d"), ("a", "b"), ("a", "c")], nodes=["a", "b", "c", "d"])
    assert g.neighbors("a") == ("b", "c", "d")


def test_predecessors_directed_and_undirected():
    """Directed predecessors are in-neighbours (node order); undirected predecessors equal neighbours."""
    g = build([("c", "a"), ("b", "a")], nodes=["a", "b", "c"])
    assert g.predecessors("a") == ("b", "c") and g.predecessors("b") == ()
    u = build([("c", "a"), ("b", "a")], nodes=["a", "b", "c"], directed=False)
    assert u.predecessors("a") == u.neighbors("a") == ("b", "c")


def test_adjacency_matrix_directed_is_asymmetric_and_undirected_is_symmetric():
    """Direction shows up as asymmetry; an undirected edge fills both cells."""
    d = build([("a", "b")], nodes=["a", "b"])
    u = build([("a", "b")], nodes=["a", "b"], directed=False)
    assert d.adjacency_matrix() == ((0, 1), (0, 0))
    assert u.adjacency_matrix() == ((0, 1), (1, 0))


def test_weight_matrix_distinguishes_zero_weight_from_no_edge_and_defaults_to_one():
    """None marks 'no edge'; an unweighted edge reads as 1; a real weight 0 stays 0."""
    g = build([("a", "b"), ("b", "c", 0), ("c", "a", 2.5)], nodes=["a", "b", "c"])
    assert g.weight_matrix() == ((None, 1, None), (None, None, 0), (2.5, None, None))


def test_undirected_weight_matrix_is_symmetric():
    """An undirected weighted edge reports its weight in both cells."""
    g = build([("a", "b", 7)], nodes=["a", "b"], directed=False)
    assert g.weight_matrix() == ((None, 7), (7, None))


def test_has_edge_respects_direction_and_get_edge_never_raises():
    """Directed has_edge is one-way; undirected is symmetric; unknown nodes simply give None/False."""
    d = build([("a", "b")])
    assert d.has_edge("a", "b") and not d.has_edge("b", "a")
    u = build([("a", "b")], directed=False)
    assert u.has_edge("b", "a")
    assert d.get_edge("a", "zzz") is None and not d.has_edge("zzz", "a")


def test_queries_about_absent_nodes_raise_missing_node_error():
    """index_of / neighbors / predecessors treat an absent node as a contract violation."""
    g = build([("a", "b")])
    for call in (g.index_of, g.neighbors, g.predecessors):
        with pytest.raises(MissingNodeError):
            call("zzz")


def test_index_of_returns_position_in_node_order():
    """index_of is the position in `nodes` (the tie-break key)."""
    g = build([("x", "y")], nodes=["y", "x"])
    assert (g.index_of("y"), g.index_of("x")) == (0, 1)


def test_reverse_flips_directed_edges_and_keeps_attributes():
    """reverse() transposes the edges (weights, evidence, labels travel with them); reversing twice restores g."""
    g = build([Edge("a", "b", 3, Status.UNKNOWN, "lab"), ("b", "c")], nodes=["a", "b", "c"], closed_world=True)
    r = g.reverse()
    assert r.nodes == g.nodes and r.closed_world is True
    e = r.get_edge("b", "a")
    assert (e.weight, e.evidence, e.label) == (3, Status.UNKNOWN, "lab") and not r.has_edge("a", "b")
    assert r.reverse() == g, "reverse is an involution"


def test_reverse_of_undirected_graph_is_equal():
    """Without direction there is nothing to flip."""
    g = build([("a", "b")], directed=False)
    assert g.reverse() == g


def test_relabel_renames_nodes_and_keeps_positions():
    """relabel is an isomorphism preserving node order, edges and their attributes."""
    g = build([Edge("a", "b", 2, Status.UNKNOWN)], nodes=["a", "b", "c"])
    h = g.relabel({"a": 10, "b": 20, "c": 30})
    assert h.nodes == (10, 20, 30) and h.get_edge(10, 20).weight == 2 and h.get_edge(10, 20).evidence is Status.UNKNOWN


def test_relabel_requires_total_injective_mapping():
    """A partial mapping is MissingNodeError; two nodes mapped to one name is GraphError (no silent merge)."""
    g = build([("a", "b")])
    with pytest.raises(MissingNodeError):
        g.relabel({"a": 1})
    with pytest.raises(GraphError):
        g.relabel({"a": 1, "b": 1})


# ------------------------------------------------------------------------------------ from_records
RECORDS = [
    {"source": "a", "target": "b", "w": 2, "ev": "unknown", "tag": "t1", "junk": object()},
    {"source": "b", "target": "c", "w": 5, "ev": Status.KNOWN, "tag": "t2", "junk": 0},
]


def test_from_records_reads_default_keys_and_ignores_extras():
    """Plain {'source', 'target'} rows work with no options; unrelated keys are ignored."""
    g = Graph.from_records([{"source": "a", "target": "b", "other": 1}])
    assert g.nodes == ("a", "b") and g.has_edge("a", "b") and g.get_edge("a", "b").evidence is Status.KNOWN


def test_from_records_custom_key_names():
    """source=/target= name the columns, so tables with 'src'/'dst' headers load without renaming."""
    g = Graph.from_records([{"src": 1, "dst": 2}], source="src", target="dst")
    assert g.has_edge(1, 2)


def test_from_records_optional_columns_weight_evidence_label():
    """weight/evidence/label columns are read when named; evidence accepts Status members and their string values."""
    g = Graph.from_records(RECORDS, weight="w", evidence="ev", label="tag")
    ab, bc = g.get_edge("a", "b"), g.get_edge("b", "c")
    assert (ab.weight, ab.evidence, ab.label) == (2, Status.UNKNOWN, "t1")
    assert (bc.weight, bc.evidence, bc.label) == (5, Status.KNOWN, "t2")


def test_from_records_bad_evidence_string_is_value_error():
    """'maybe' is not a Status value; 'invalid' parses as a Status but is not allowed on an edge. Both: ValueError."""
    for cell in ("maybe", "invalid"):
        with pytest.raises(ValueError):
            Graph.from_records([{"source": "a", "target": "b", "ev": cell}], evidence="ev")


@pytest.mark.parametrize("record", [{"source": "a"}, {"target": "b"}, {}])
def test_from_records_missing_required_key_is_graph_error(record):
    """A row without a source or target cannot be an edge: GraphError, not KeyError and not a skipped row."""
    with pytest.raises(GraphError):
        Graph.from_records([record])


def test_from_records_missing_optional_column_value_is_graph_error():
    """If you name a weight column, every row must have it."""
    with pytest.raises(GraphError):
        Graph.from_records([{"source": "a", "target": "b"}], weight="w")


def test_from_records_duplicate_rows_merge_and_nodes_can_declare_isolates():
    """Duplicate rows merge exactly like duplicate edges; `nodes=` adds nodes that appear in no row."""
    g = Graph.from_records([{"source": "a", "target": "b"}] * 3, nodes=["a", "b", "iso"])
    assert len(g.edges) == 1 and g.has_node("iso")


def test_from_records_missing_endpoint_with_declared_nodes():
    """The missing-reference rule holds for records too."""
    with pytest.raises(MissingNodeError):
        Graph.from_records([{"source": "a", "target": "b"}], nodes=["a"])


# ---------------------------------------------------------------------------------------- properties
@given(edge_lists(), st.booleans())
def test_matrix_and_list_views_agree(case, directed):
    """The adjacency matrix and the adjacency lists describe the same relation (both views are derived from it)."""
    nodes, edges = case
    g = build(edges, nodes, directed)
    adj, mat = g.adjacency(), g.adjacency_matrix()
    assert list(adj) == list(g.nodes), "adjacency keys are in node order"
    for i, a in enumerate(g.nodes):
        for j, b in enumerate(g.nodes):
            assert (mat[i][j] == 1) == (b in adj[a]), f"matrix[{a}][{b}] disagrees with the adjacency list"
            assert mat[i][j] in (0, 1)
    expected = pair_set(edges, directed)
    assert {(a, b) for a in g.nodes for b in adj[a]} == expected, "the relation must be exactly the input edges"
    if not directed:
        assert mat == tuple(zip(*mat)), "undirected adjacency matrix must be symmetric"


@given(edge_lists(), st.booleans(), st.randoms(use_true_random=False))
def test_edge_listing_order_never_changes_the_graph(case, directed, rnd):
    """Shuffling and duplicating the input edges (with fixed nodes) yields an EQUAL graph."""
    nodes, edges = case
    shuffled = list(edges) + list(edges)
    rnd.shuffle(shuffled)
    assert build(edges, nodes, directed) == build(shuffled, nodes, directed)


@given(edge_lists(), st.booleans())
def test_reverse_swaps_predecessors_and_neighbors(case, directed):
    """For directed graphs reverse() exchanges successor and predecessor lists."""
    nodes, edges = case
    g = build(edges, nodes, directed)
    r = g.reverse()
    for n in g.nodes:
        assert r.neighbors(n) == g.predecessors(n)
