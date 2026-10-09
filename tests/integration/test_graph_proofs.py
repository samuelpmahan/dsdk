"""Integration tests: graph reachability as checked logic proofs (dsdk.graph x dsdk.logic x dsdk.core).

Every test runs two or more layers together on REAL output of the lower one: the graph package's breadth-first search, evidence rules and
lineage graphs on one side, the logic package's proof checker, entailment and countermodel search on the other. Exhaustive over all small
graphs (every directed graph on up to 3 nodes, every undirected one on up to 3, a regular sample of the 4-node loop-free ones) plus
Hypothesis for 5-node graphs with mixed edge evidence. The independent expectations are: the logic package's own proof checker (which
rejects tampered proofs), `logic.entails` (a second, brute-force route to reachability) and hand-computed paths.
"""
import itertools
from fractions import Fraction

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from dsdk.core import Part, PxC, Status
from dsdk.graph import Edge, Graph, MissingNodeError, bfs, known_subgraph, lineage_graph, reachable, shortest_path
from dsdk.graph.proofs import (
    MAX_ENUM_NODES, Countermodel, GraphProof, entailed_by_known_edges, known_premises, node_var, unreachability_countermodel, witness_proof,
)
from dsdk.logic import Implies, Not, Rule, Step, Var, check, entails, evaluate


def known(j):
    assert j.status is Status.KNOWN, j
    return j.value


def digraphs(n, loops=True):
    pairs = [(i, j) for i in range(n) for j in range(n) if loops or i != j]
    for mask in range(1 << len(pairs)):
        yield [pairs[k] for k in range(len(pairs)) if mask >> k & 1]


def undirected(n):
    pairs = [(i, j) for i in range(n) for j in range(i, n)]
    for mask in range(1 << len(pairs)):
        yield [pairs[k] for k in range(len(pairs)) if mask >> k & 1]


def small_graphs():
    """(n, edges, directed) for every graph in the exhaustive set."""
    for n in (1, 2, 3):
        for e in digraphs(n):
            yield n, e, True
        for e in undirected(n):
            yield n, e, False
    for k, e in enumerate(digraphs(4, loops=False)):
        if k % 9 == 0:
            yield 4, e, True


def mk(n, edges, directed=True, **kw):
    return Graph.from_edges(edges, list(range(n)), directed=directed, **kw)


# ==== A witness path becomes a proof the logic checker accepts ====
def test_every_reachable_pair_on_every_small_graph_gets_a_proof_that_the_logic_checker_accepts():
    """For each small graph and each source and target joined by known edges, witness_proof returns KNOWN, the proof passes dsdk.logic.check against its premises, and it concludes exactly the target's variable."""
    pairs = 0
    for n, e, d in small_graphs():
        g = mk(n, e, d)
        for s in range(n):
            reach = bfs(g, s).distance
            for t in reach:
                p = known(witness_proof(g, s, t))
                result = check(p.steps, p.premises)
                assert result.ok and result.bad_step is None, (e, d, s, t, result)
                assert p.steps[-1].formula == node_var(g, t)
                pairs += 1
    assert pairs > 5000


def test_the_proof_is_exactly_the_documented_modus_ponens_chain():
    """On the chain a to b to c the proof is premise a, premise a-implies-b, modus ponens, premise b-implies-c, modus ponens, with the citations in implication-first order."""
    g = Graph.from_edges([("a", "b"), ("b", "c")])
    p = known(witness_proof(g, "a", "c"))
    a, b, c = (node_var(g, x) for x in "abc")
    assert p.path == ("a", "b", "c")
    assert p.steps == (
        Step(a, Rule.PREMISE, ()), Step(Implies(a, b), Rule.PREMISE, ()), Step(b, Rule.MODUS_PONENS, (1, 0)),
        Step(Implies(b, c), Rule.PREMISE, ()), Step(c, Rule.MODUS_PONENS, (3, 2)),
    )


def test_the_proof_length_is_twice_the_distance_plus_one_and_the_path_is_the_breadth_first_witness():
    """The number of steps is 2*distance + 1 and the path is the shortest_path witness of the known subgraph, so the proof inherits the tie-break of the graph package."""
    for n, e, d in small_graphs():
        g = mk(n, e, d)
        for s in range(n):
            dist = bfs(g, s).distance
            for t, k in dist.items():
                p = known(witness_proof(g, s, t))
                assert len(p.steps) == 2 * k + 1 and p.path == shortest_path(g, s, t)


def test_a_node_reaches_itself_with_a_single_premise_step():
    """When the source is the target the proof is the single premise step, even for a node with a self-loop."""
    g = Graph.from_edges([("a", "a"), ("a", "b")])
    for node in ("a", "b"):
        p = known(witness_proof(g, node, node))
        assert p.path == (node,) and p.steps == (Step(node_var(g, node), Rule.PREMISE, ()),)
        assert check(p.steps, p.premises).ok


def test_diamond_tie_break_decides_which_branch_the_proof_uses():
    """On the diamond a to b, a to c, b to d, c to d the proof goes through b, and listing the nodes as a, c, b, d moves it to c, the same tie-break as shortest_path."""
    edges = [("a", "b"), ("a", "c"), ("b", "d"), ("c", "d")]
    assert known(witness_proof(Graph.from_edges(edges, list("abcd")), "a", "d")).path == ("a", "b", "d")
    assert known(witness_proof(Graph.from_edges(edges, list("acbd")), "a", "d")).path == ("a", "c", "d")


def test_undirected_edges_give_proofs_in_both_directions():
    """An undirected edge is two implications: a proof exists from either end and the logic checker accepts both."""
    g = Graph.from_edges([("a", "b"), ("b", "c")], directed=False)
    for s, t in (("a", "c"), ("c", "a")):
        p = known(witness_proof(g, s, t))
        assert check(p.steps, p.premises).ok and p.path[0] == s and p.path[-1] == t


def test_premises_are_one_implication_per_known_arrow_in_edge_order():
    """known_premises lists one implication per directed known edge in the graph's edge order, both directions for undirected edges, once for a self-loop, and nothing for uncertain edges."""
    g = Graph.from_edges([Edge("a", "b"), Edge("b", "c", evidence=Status.UNKNOWN), Edge("c", "c"), Edge("c", "a", evidence=Status.NOT_OBSERVED)], list("abc"))
    a, b, c = (node_var(g, x) for x in "abc")
    assert known_premises(g) == (Implies(a, b), Implies(c, c))
    u = Graph.from_edges([("a", "b"), ("b", "b")], list("ab"), directed=False)
    assert known_premises(u) == (Implies(node_var(u, "a"), node_var(u, "b")), Implies(node_var(u, "b"), node_var(u, "a")), Implies(node_var(u, "b"), node_var(u, "b")))


def test_variables_are_index_based_so_any_hashable_node_works():
    """Nodes that are ints, strings, tuples and a core Part all get distinct variables n0, n1, ... by position, and a mixed-type graph still gets a checked proof."""
    part = Part("x")
    g = Graph.from_edges([(1, "1"), ("1", (1, 1)), ((1, 1), part)])
    assert [node_var(g, n).name for n in g.nodes] == ["n0", "n1", "n2", "n3"]
    p = known(witness_proof(g, 1, part))
    assert check(p.steps, p.premises).ok and len(p.steps) == 7


# ==== The logic checker really rejects tampered graph proofs ====
def tampered_cases(p):
    s = list(p.steps)
    yield "swapped citations", [*s[:2], Step(s[2].formula, Rule.MODUS_PONENS, (0, 1)), *s[3:]], 2
    yield "wrong conclusion", [*s[:2], Step(Var("n99"), Rule.MODUS_PONENS, (1, 0)), *s[3:]], 2
    yield "forward citation", [*s[:2], Step(s[2].formula, Rule.MODUS_PONENS, (1, 5)), *s[3:]], 2
    yield "invented premise", [Step(Var("n99"), Rule.PREMISE, ()), *s[1:]], 0
    yield "affirming the consequent", [*s[:2], Step(s[0].formula, Rule.MODUS_PONENS, (1, 0)), *s[3:]], 2


def test_tampered_proofs_are_rejected_at_the_first_bad_step():
    """Swapping the citations, concluding a different variable, citing a later step, inventing a premise or affirming the consequent in a witness proof is rejected by dsdk.logic.check at exactly the corrupted step."""
    g = Graph.from_edges([("a", "b"), ("b", "c")])
    p = known(witness_proof(g, "a", "c"))
    for name, steps, bad in tampered_cases(p):
        result = check(steps, p.premises)
        assert not result.ok and result.bad_step == bad, name


def test_the_proof_is_only_valid_against_the_premises_it_was_built_for():
    """Checking the same proof against the premises of a graph without that edge fails at the premise step that is no longer a premise."""
    g = Graph.from_edges([("a", "b"), ("b", "c")])
    p = known(witness_proof(g, "a", "c"))
    fewer = [f for f in p.premises if f != Implies(node_var(g, "b"), node_var(g, "c"))]
    result = check(p.steps, fewer)
    assert not result.ok and result.bad_step == 3


def test_a_proof_cannot_be_reused_for_a_different_graph_with_the_wrong_direction():
    """Reversing the arrows makes the old proof invalid: its implications are no longer premises."""
    g = Graph.from_edges([("a", "b"), ("b", "c")])
    p = known(witness_proof(g, "a", "c"))
    assert not check(p.steps, (node_var(g, "a"),) + known_premises(g.reverse())).ok


# ==== Uncertain, hidden and missing edges never become premises ====
def uncertain_graph(**kw):
    return Graph.from_edges([Edge("a", "b"), Edge("b", "c", evidence=Status.UNKNOWN), Edge("a", "d", evidence=Status.NOT_OBSERVED)], list("abcd"), **kw)


def test_a_path_that_needs_an_inferred_edge_gets_no_proof_and_the_reachable_verdict():
    """When only an UNKNOWN edge connects the nodes there is no proof, and the answer is exactly reachable's UNKNOWN verdict with its reason naming the uncertain edge."""
    g = uncertain_graph()
    j = witness_proof(g, "a", "c")
    assert j.status is Status.UNKNOWN and j.value is None
    assert j == reachable(g, "a", "c") and "b->c (unknown)" in j.reason


def test_a_proof_never_uses_an_uncertain_edge_even_when_it_would_be_shorter():
    """A direct but only inferred edge is ignored: the proof takes the longer observed route and none of its steps mention the inferred edge."""
    g = Graph.from_edges([Edge("a", "x"), Edge("x", "t"), Edge("a", "t", evidence=Status.UNKNOWN)], list("axt"))
    p = known(witness_proof(g, "a", "t"))
    assert p.path == ("a", "x", "t") and Implies(node_var(g, "a"), node_var(g, "t")) not in p.premises
    assert check(p.steps, p.premises).ok


def test_in_a_closed_world_with_no_connection_there_is_no_proof_by_definition():
    """In a closed world where nothing connects the nodes even counting uncertain edges, witness_proof answers NOT_APPLICABLE and says to ask for the countermodel."""
    g = Graph.from_edges([("a", "b")], list("abc"), closed_world=True)
    j = witness_proof(g, "a", "c")
    assert j.status is Status.NOT_APPLICABLE and j.reason.startswith("no proof exists:")


def test_in_an_open_world_with_no_connection_the_verdict_is_unknown():
    """In an open world a missing edge proves nothing, so witness_proof is UNKNOWN with the reachability reason."""
    g = Graph.from_edges([("a", "b")], list("abc"))
    j = witness_proof(g, "a", "c")
    assert j.status is Status.UNKNOWN and j == reachable(g, "a", "c")


@pytest.mark.parametrize("source,target", [("zz", "a"), ("a", "zz"), ("yy", "zz")])
def test_missing_nodes_are_invalid_with_the_reachable_wording(source, target):
    """A node that is not in the graph gives INVALID with the same words as dsdk.graph.reachable (source named first), for the proof, the countermodel and the logic route."""
    g = Graph.from_edges([("a", "b")])
    expected = reachable(g, source, target)
    for fn in (witness_proof, unreachability_countermodel, entailed_by_known_edges):
        j = fn(g, source, target)
        assert j.status is Status.INVALID and j == expected


@pytest.mark.parametrize("fn", [witness_proof, unreachability_countermodel, entailed_by_known_edges])
def test_a_non_graph_is_a_type_error(fn):
    """Passing something that is not a Graph is a Python TypeError for every function in the module."""
    with pytest.raises(TypeError):
        fn("graph", "a", "b")


# ==== Non-reachability becomes a countermodel the logic package confirms ====
def test_every_unreachable_pair_gets_a_countermodel_that_satisfies_the_premises_and_falsifies_the_target():
    """For each small graph and each source and target NOT joined by known edges, the countermodel makes the source and every known-edge implication true and the target false when evaluated with dsdk.logic.evaluate, and logic.entails agrees there is no entailment."""
    count = 0
    for n, e, d in small_graphs():
        g = mk(n, e, d)
        for s in range(n):
            reach = set(bfs(g, s).distance)
            for t in range(n):
                if t in reach:
                    continue
                cm = known(unreachability_countermodel(g, s, t))
                assert all(evaluate(f, cm.assignment) for f in cm.premises)
                assert evaluate(node_var(g, s), cm.assignment) and not evaluate(node_var(g, t), cm.assignment)
                assert cm.cross_checked and not entails(cm.premises, node_var(g, t))
                assert cm.reached == tuple(x for x in g.nodes if x in reach)
                count += 1
    assert count > 2000


def test_the_logics_own_first_countermodel_also_satisfies_the_graph_premises():
    """The countermodel the logic package finds by brute force (first in its enumeration order) is carried along, and it too satisfies the premises and falsifies the target."""
    g = Graph.from_edges([("a", "b"), ("c", "d")])
    cm = known(unreachability_countermodel(g, "a", "d"))
    assert cm.logic_countermodel is not None
    assert all(evaluate(f, cm.logic_countermodel) for f in cm.premises) and not evaluate(node_var(g, "d"), cm.logic_countermodel)


def test_reachable_pairs_have_no_countermodel_and_unreachable_pairs_have_no_proof_or_the_reverse():
    """For every pair exactly one of proof and countermodel exists over known edges: a countermodel request for a reachable pair is NOT_APPLICABLE and vice versa."""
    for n, e, d in small_graphs():
        g = mk(n, e, d, closed_world=True)
        for s in range(n):
            reach = set(bfs(g, s).distance)
            for t in range(n):
                p, cm = witness_proof(g, s, t), unreachability_countermodel(g, s, t)
                if t in reach:
                    assert p.status is Status.KNOWN and cm.status is Status.NOT_APPLICABLE and cm.reason.startswith("no countermodel exists:")
                else:
                    assert p.status is Status.NOT_APPLICABLE and cm.status is Status.KNOWN


def test_the_unreachable_flag_follows_the_world_and_the_uncertain_edges():
    """In a closed world with no uncertain connection the countermodel is flagged unreachable, but with an inferred edge that could connect them, or in an open world, it only says not derivable from the observed edges."""
    closed_gap = Graph.from_edges([("a", "b")], list("abc"), closed_world=True)
    assert known(unreachability_countermodel(closed_gap, "a", "c")).unreachable is True
    open_gap = Graph.from_edges([("a", "b")], list("abc"))
    assert known(unreachability_countermodel(open_gap, "a", "c")).unreachable is False
    closed_uncertain = uncertain_graph(closed_world=True)
    cm = known(unreachability_countermodel(closed_uncertain, "a", "c"))
    assert cm.unreachable is False and "n2" in cm.assignment and cm.assignment["n2"] is False


def test_the_countermodel_marks_exactly_the_nodes_reached_over_known_edges():
    """The true variables of the countermodel are the nodes the graph package reaches on the known subgraph; an inferred edge does not make its endpoint true."""
    g = uncertain_graph()
    cm = known(unreachability_countermodel(g, "a", "c"))
    assert cm.reached == ("a", "b") and cm.assignment == {"n0": True, "n1": True, "n2": False, "n3": False}
    assert set(cm.reached) == set(bfs(known_subgraph(g), "a").distance)


def test_a_graph_larger_than_the_enumeration_limit_skips_the_brute_force_routes_but_is_still_checked():
    """With more nodes than MAX_ENUM_NODES the countermodel is still built and evaluated against the premises, but logic.entails is not run (cross_checked False, no logic countermodel) and the logic route answers UNKNOWN."""
    n = MAX_ENUM_NODES + 3
    g = Graph.from_edges([(i, i + 1) for i in range(n - 2)], list(range(n)))
    cm = known(unreachability_countermodel(g, 0, n - 1))
    assert cm.cross_checked is False and cm.logic_countermodel is None
    assert all(evaluate(f, cm.assignment) for f in cm.premises) and not evaluate(node_var(g, n - 1), cm.assignment)
    j = entailed_by_known_edges(g, 0, 1)
    assert j.status is Status.UNKNOWN and j.reason.startswith("too many nodes to enumerate")


def test_a_long_path_needs_no_recursion_and_its_proof_still_checks():
    """A 2000-node path gives a 3999-step proof that the logic checker accepts, without recursion errors."""
    g = Graph.from_edges([(i, i + 1) for i in range(1999)], list(range(2000)))
    p = known(witness_proof(g, 0, 1999))
    assert len(p.steps) == 3999 and check(p.steps, p.premises).ok


# ==== The logic route and the graph route agree on reachability ====
def test_entailment_by_known_edges_equals_breadth_first_reachability_on_every_small_graph():
    """For every small graph and every pair, logic.entails of the source plus the known-edge implications gives exactly the answer of breadth-first search on the known subgraph."""
    for n, e, d in small_graphs():
        g = mk(n, e, d)
        for s in range(n):
            reach = set(bfs(g, s).distance)
            for t in range(n):
                assert known(entailed_by_known_edges(g, s, t)) is (t in reach), (e, d, s, t)


edge_evidence = st.sampled_from([Status.KNOWN, Status.KNOWN, Status.UNKNOWN, Status.NOT_OBSERVED])


@st.composite
def evidence_graphs(draw):
    n = draw(st.integers(min_value=1, max_value=5))
    directed = draw(st.booleans())
    pairs = [(i, j) for i in range(n) for j in range(n)]
    chosen = draw(st.lists(st.sampled_from(pairs), max_size=10))
    edges = [Edge(a, b, evidence=draw(edge_evidence)) for a, b in chosen]
    return Graph.from_edges(edges, list(range(n)), directed=directed, closed_world=draw(st.booleans()))


@settings(max_examples=80)
@given(evidence_graphs(), st.data())
def test_random_graphs_with_mixed_evidence_agree_across_graph_logic_and_core_layers(g, data):
    """For random graphs with known, inferred and candidate edges: a proof exists exactly when reachable says KNOWN True, it passes the logic checker and uses only known-edge premises, a countermodel exists exactly when the known edges do not connect the pair, and entailment agrees with both."""
    s, t = data.draw(st.sampled_from(g.nodes)), data.draw(st.sampled_from(g.nodes))
    verdict = reachable(g, s, t)
    proof = witness_proof(g, s, t)
    by_known = t in bfs(known_subgraph(g), s).distance
    assert (proof.status is Status.KNOWN) == (verdict.status is Status.KNOWN and verdict.value is True) == by_known
    if by_known:
        p = proof.value
        assert check(p.steps, p.premises).ok and set(p.premises[1:]) == set(known_premises(g))
        assert unreachability_countermodel(g, s, t).status is Status.NOT_APPLICABLE
    else:
        cm = known(unreachability_countermodel(g, s, t))
        assert all(evaluate(f, cm.assignment) for f in cm.premises) and not evaluate(node_var(g, t), cm.assignment)
        assert cm.unreachable == (verdict.status is Status.KNOWN and verdict.value is False)
    assert known(entailed_by_known_edges(g, s, t)) is by_known


# ==== Proofs across the kernel: lineage of belief and calculation Parts ====
def test_a_proof_that_one_part_feeds_another_is_built_from_the_lineage_graph():
    """For a chain of PxC compositions, the lineage graph (core x graph) lets witness_proof build a checked proof that the first Part reaches the last, and the reverse direction has no proof."""
    store = PxC()
    double = store.set("fn.double", Part(lambda inputs: inputs["x"] * 2))
    x = store.set("px.x", Part(3))
    y = store.compose("px.y", double, {"x": x})
    z = store.compose("px.z", double, {"x": y})
    g = lineage_graph(z)
    p = known(witness_proof(g, x, z))
    assert p.path == (x, y, z) and check(p.steps, p.premises).ok
    assert witness_proof(g, z, x).status is Status.NOT_APPLICABLE, "lineage graphs are closed worlds and point forward only"
    assert known(unreachability_countermodel(g, z, x)).unreachable is True


def test_the_calculation_part_is_also_a_node_that_can_be_proved_to_reach_the_output():
    """The calculation Part used by a composition reaches the output in the lineage graph, and the proof for it is accepted by the checker."""
    store = PxC()
    fn = store.set("fn.inc", Part(lambda inputs: inputs["x"] + 1))
    out = store.compose("px.out", fn, {"x": store.set("px.x", Part(1))})
    p = known(witness_proof(lineage_graph(out), fn, out))
    assert p.path == (fn, out) and check(p.steps, p.premises).ok


def test_a_proof_value_is_a_frozen_record_of_the_documented_fields():
    """GraphProof and Countermodel are frozen records with the documented fields."""
    g = Graph.from_edges([("a", "b")])
    p = known(witness_proof(g, "a", "b"))
    assert isinstance(p, GraphProof) and (p.path, len(p.premises), len(p.steps)) == (("a", "b"), 2, 3)
    cm = known(unreachability_countermodel(g, "b", "a"))
    assert isinstance(cm, Countermodel) and cm.reached == ("b",)
    with pytest.raises(Exception):
        p.path = ()
