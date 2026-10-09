"""Integration tests: a logic proof recorded in the kernel store IS a lineage graph (dsdk.logic x dsdk.core x dsdk.graph).

The recording (dsdk.logic.recorded) binds one composed Part per proof step in one tick. These tests read the store back with the graph package's own
lineage functions and compare it with the proof's citation graph computed independently from the Steps, and also record the witness proofs that the graph
package builds from reachability. Independent expectations: the citation edges read off the Step objects, a transitive closure of the citations, and the
graph package's reachability and topological order.
"""
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from dsdk.core import PxC, Status
from dsdk.graph import (
    CALCULATION_LABEL, Graph, find_cycle, lineage_graph, reachable, shortest_path, store_lineage_graph, topological_order, witness_proof,
)
from dsdk.graph.proofs import node_var
from dsdk.logic import Implies, Rule, Step, Var, check
from dsdk.logic.recorded import StepCalculation, record_proof, replay_proof

p, q, r = Var("p"), Var("q"), Var("r")
PREMISES = [p, Implies(p, q), Implies(q, r)]
CHAIN = [
    Step(p, Rule.PREMISE, ()), Step(Implies(p, q), Rule.PREMISE, ()), Step(q, Rule.MODUS_PONENS, (1, 0)),
    Step(Implies(q, r), Rule.PREMISE, ()), Step(r, Rule.MODUS_PONENS, (3, 2)),
]


def known(j):
    assert j.status is Status.KNOWN, j
    return j.value


def citation_edges(proof):
    """Independent: {(cited index, step index, input name)} read straight off the Step objects."""
    return {(c, i, f"c{j}") for i, s in enumerate(proof) for j, c in enumerate(s.cites)}


def lineage_edges_among_steps(graph, parts):
    """The edges of a lineage graph that join two step Parts, as {(index, index, label)} (a merged label like 'c0,c1' is split back apart)."""
    index = {part: i for i, part in enumerate(parts)}
    out = set()
    for e in graph.edges:
        if e.source in index and e.target in index:
            for label in e.label.split(","):
                out.add((index[e.source], index[e.target], label))
    return out


# ==== The store's lineage graph equals the proof's citation graph ====
def test_the_lineage_graph_of_the_store_has_exactly_the_proofs_citation_edges():
    """After recording the five-step chain, the edges of the store's lineage graph between step Parts are exactly the citation edges (step 2 cites 1 and 0, step 4 cites 3 and 2), labelled c0 and c1 in cite order."""
    store = PxC()
    rec = known(record_proof(store, "c", CHAIN, PREMISES))
    g = store_lineage_graph(store)
    assert lineage_edges_among_steps(g, rec.parts) == citation_edges(CHAIN) == {(1, 2, "c0"), (0, 2, "c1"), (3, 4, "c0"), (2, 4, "c1")}


def test_the_lineage_nodes_are_the_step_parts_plus_one_calculation_per_step():
    """The lineage graph has 2n nodes for an n-step proof: the n step Parts and n calculation Parts, each calculation feeding exactly its own step with the calculation label."""
    store = PxC()
    rec = known(record_proof(store, "c", CHAIN, PREMISES))
    g = store_lineage_graph(store)
    assert len(g.nodes) == 10 and set(rec.parts) <= set(g.nodes)
    calc_edges = [e for e in g.edges if e.label == CALCULATION_LABEL]
    assert len(calc_edges) == 5 and {e.target for e in calc_edges} == set(rec.parts)
    assert all(isinstance(e.source.value, StepCalculation) for e in calc_edges)
    assert g.directed and g.closed_world and find_cycle(g) is None


def test_the_lineage_graph_of_the_conclusion_contains_exactly_the_cited_ancestors():
    """The lineage graph of the conclusion contains the step Parts that the conclusion transitively cites and no others: here steps 0, 1, 2, 3, 4 all; for a proof with an unused step the unused Part is absent."""
    store = PxC()
    rec = known(record_proof(store, "c", CHAIN + [Step(p, Rule.PREMISE, ())], PREMISES))
    g = lineage_graph(rec.parts[4])
    in_graph = {i for i, part in enumerate(rec.parts) if part in set(g.nodes)}
    assert in_graph == {0, 1, 2, 3, 4} and 5 not in in_graph


def test_the_topological_order_of_the_lineage_respects_the_citations():
    """Every cited Part comes before the Part that cites it in the graph package's topological order of the store's lineage."""
    store = PxC()
    rec = known(record_proof(store, "c", CHAIN, PREMISES))
    order = topological_order(store_lineage_graph(store))
    pos = {n: i for i, n in enumerate(order)}
    for i, s in enumerate(CHAIN):
        for c in s.cites:
            assert pos[rec.parts[c]] < pos[rec.parts[i]]


def test_reachability_in_the_lineage_graph_follows_the_derivation():
    """The graph package says the first premise reaches the conclusion (KNOWN True), and the conclusion does not reach back."""
    store = PxC()
    rec = known(record_proof(store, "c", CHAIN, PREMISES))
    g = store_lineage_graph(store)
    assert known(reachable(g, rec.parts[0], rec.parts[4])) is True
    assert known(reachable(g, rec.parts[4], rec.parts[0])) is False


@pytest.mark.parametrize("name", ["tamper_swapped", "tamper_forward", "tamper_conclusion"])
def test_a_failed_recording_leaves_an_empty_lineage_graph(name):
    """When the checker rejects the proof and the tick rolls back, the store's lineage graph is empty: nothing of the rejected proof is visible to the graph package."""
    bad = {
        "tamper_swapped": [*CHAIN[:2], Step(q, Rule.MODUS_PONENS, (0, 1)), *CHAIN[3:]],
        "tamper_forward": [*CHAIN[:2], Step(q, Rule.MODUS_PONENS, (1, 9)), *CHAIN[3:]],
        "tamper_conclusion": [*CHAIN[:4], Step(p, Rule.MODUS_PONENS, (3, 2))],
    }[name]
    store = PxC()
    assert record_proof(store, "c", bad, PREMISES).status is Status.INVALID
    g = store_lineage_graph(store)
    assert g.nodes == () and g.edges == ()


# ==== Random valid proofs: the lineage graph is always the citation graph ====
@st.composite
def valid_proofs(draw):
    a, b, c = Var("a"), Var("b"), Var("c")
    premises = [a, Implies(a, b), Implies(b, c), Implies(a, c)]
    steps = [Step(f, Rule.PREMISE, ()) for f in draw(st.lists(st.sampled_from(premises), min_size=1, max_size=4))]
    for _ in range(draw(st.integers(0, 7))):
        fs = [s.formula for s in steps]
        moves = []
        for i, f in enumerate(fs):
            for j, g in enumerate(fs):
                if isinstance(f, Implies) and f.left == g:
                    moves.append(Step(f.right, Rule.MODUS_PONENS, (i, j)))
                moves.append(Step(Implies(f, g), Rule.PREMISE, ())) if Implies(f, g) in premises else None
        moves = [m for m in moves if m is not None]
        if not moves:
            break
        steps.append(draw(st.sampled_from(moves)))
    return steps, premises


@settings(max_examples=60, deadline=None)
@given(valid_proofs())
def test_for_random_valid_proofs_the_lineage_edges_equal_the_citation_edges_and_the_replay_matches(case):
    """For random valid proofs, the lineage edges between step Parts equal the independent citation edges, the lineage graph is acyclic, and replaying the store returns the original steps which the checker accepts."""
    proof, premises = case
    assert check(proof, premises).ok
    store = PxC()
    rec = known(record_proof(store, "r", proof, premises))
    g = store_lineage_graph(store)
    assert lineage_edges_among_steps(g, rec.parts) == citation_edges(proof)
    assert find_cycle(g) is None and len(g.nodes) == 2 * len(proof)
    steps = known(replay_proof(store, "r"))
    assert steps == tuple(proof) and check(steps, premises).ok


# ==== Graph reachability witnesses recorded and replayed through the kernel ====
def test_a_graph_witness_proof_is_recorded_replayed_and_its_lineage_follows_the_path():
    """The proof the graph package builds for a to d over a chain a to b to c to d is recorded in the kernel store, replays to the same steps, concludes the variable of d, and the lineage graph has a path from the first premise to the conclusion."""
    g = Graph.from_edges([("a", "b"), ("b", "c"), ("c", "d")])
    w = known(witness_proof(g, "a", "d"))
    store = PxC()
    rec = known(record_proof(store, "w", list(w.steps), list(w.premises)))
    assert rec.conclusion.value == node_var(g, "d")
    assert known(replay_proof(store, "w")) == tuple(w.steps)
    lg = store_lineage_graph(store)
    assert shortest_path(lg, rec.parts[0], rec.conclusion) is not None
    assert lineage_edges_among_steps(lg, rec.parts) == citation_edges(w.steps)


def test_every_witness_proof_over_small_graphs_records_and_replays():
    """For every directed graph on 3 nodes and every reachable pair, the graph package's witness proof is accepted by the recorder and replays to itself."""
    import itertools

    pairs = [(i, j) for i in range(3) for j in range(3)]
    count = 0
    for mask in range(1 << 9):
        edges = [pairs[k] for k in range(9) if mask >> k & 1]
        g = Graph.from_edges(edges, [0, 1, 2])
        for s, t in itertools.product(range(3), repeat=2):
            j = witness_proof(g, s, t)
            if j.status is not Status.KNOWN:
                continue
            w = j.value
            store = PxC()
            rec = known(record_proof(store, "w", list(w.steps), list(w.premises)))
            assert known(replay_proof(store, "w")) == tuple(w.steps)
            assert rec.conclusion.value == node_var(g, t)
            count += 1
    assert count > 600


def test_the_graph_package_can_prove_that_a_recorded_step_depends_on_a_premise_and_not_on_an_unused_one():
    """Graph reachability on the lineage tells which premises a conclusion depends on: the premise p reaches the conclusion r, but an extra premise step that nothing cites does not."""
    steps = [*CHAIN, Step(p, Rule.PREMISE, ())]
    store = PxC()
    rec = known(record_proof(store, "c", steps, PREMISES))
    lg = store_lineage_graph(store)
    assert known(reachable(lg, rec.parts[0], rec.parts[4])) is True
    assert known(reachable(lg, rec.parts[5], rec.parts[4])) is False
