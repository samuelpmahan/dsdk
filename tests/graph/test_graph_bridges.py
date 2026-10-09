"""Contract tests for dsdk.graph.bridges: lineage of PxC Parts, formula syntax trees, package import graphs."""
import pytest
from hypothesis import given
from hypothesis import strategies as st

from dsdk.core import Part, PxC, ReceiptStatus, Status
from dsdk.graph import (
    CALCULATION_LABEL, CycleError, Graph, bfs, find_cycle, formula_graph, formula_labels, import_graph, lineage_graph,
    store_lineage_graph, topological_order,
)
from dsdk.logic import And, Const, Iff, Implies, Not, Or, Var, size

from graph_oracles import formula_height, formulas, preorder_nodes


def add(values):
    return sum(values.values())


def make_store():
    store = PxC()
    store.set("fn.add", Part(add))
    store.set("px.x", Part(1))
    store.set("px.y", Part(2))
    return store


# ============================================================================== lineage_graph
def test_lineage_of_a_raw_part_is_a_single_node():
    """A Part with no composition has no history: one node, no edges."""
    p = Part(5)
    g = lineage_graph(p)
    assert g.nodes == (p,) and g.edges == ()


def test_lineage_nodes_are_part_objects_identified_by_identity():
    """Two Parts holding equal values are TWO nodes; a Part shared by two compositions is ONE node."""
    a, b = Part(1), Part(1)
    calc = Part(add)
    out = PxC().compose("px.o", calc, {"p": a, "q": b})
    g = lineage_graph(out)
    assert len(g.nodes) == 4, "out, calc, a, b: equal values do not merge nodes"
    assert a in g.nodes and b in g.nodes and a is not b


def test_lineage_diamond_exact_nodes_edges_and_labels():
    """x feeds both s and t: it is one node with two out-edges; edges carry the INPUT NAME as label."""
    store = make_store()
    x, y = store.get("px.x"), store.get("px.y")
    s = store.compose("px.s", "fn.add", {"x": x, "y": y})
    t = store.compose("px.t", "fn.add", {"x": s, "y": x})
    calc = store.get("fn.add")
    g = lineage_graph(t)
    assert g.nodes == (t, calc, s, x, y), "BFS discovery from t; calculation before inputs; inputs in mapping order"
    assert g.directed and g.closed_world
    expect = {(calc, t): CALCULATION_LABEL, (s, t): "x", (x, t): "y",
              (calc, s): CALCULATION_LABEL, (x, s): "x", (y, s): "y"}
    got = {(e.source, e.target): e.label for e in g.edges}
    assert got == expect
    assert all(e.evidence is Status.KNOWN for e in g.edges), "lineage is recorded history: every edge is KNOWN"


def test_lineage_edges_point_from_dependency_to_dependent_so_topological_order_is_a_valid_run_order():
    """Topological order of the lineage graph lists inputs before the Parts computed from them; the target is last."""
    store = make_store()
    x, y = store.get("px.x"), store.get("px.y")
    s = store.compose("px.s", "fn.add", {"x": x, "y": y})
    t = store.compose("px.t", "fn.add", {"x": s, "y": x})
    order = topological_order(lineage_graph(t))
    pos = {n: i for i, n in enumerate(order)}
    assert order[-1] is t
    assert pos[x] < pos[s] < pos[t] and pos[y] < pos[s] and pos[store.get("fn.add")] < pos[s]


def test_lineage_same_part_under_two_input_names_merges_edges_and_joins_labels():
    """Passing x as both 'p' and 'q' leaves ONE edge x->out labelled 'p,q' (the duplicate-label rule)."""
    x = Part(3)
    out = PxC().compose("px.o", Part(add), {"q": x, "p": x})
    e = lineage_graph(out).get_edge(x, out)
    assert e.label == "p,q"


def test_lineage_shared_calculation_is_one_node():
    """The same calculation Part used for two composes appears once, with two outgoing edges."""
    store = make_store()
    a = store.compose("px.a", "fn.add", {"x": "px.x"})
    b = store.compose("px.b", "fn.add", {"a": a, "y": "px.y"})
    g = lineage_graph(b)
    assert sum(1 for n in g.nodes if n is store.get("fn.add")) == 1
    assert len(g.neighbors(store.get("fn.add"))) == 2


def test_lineage_through_a_committed_tick():
    """Parts composed inside a tick (reading staged Parts by address) have normal lineage once committed."""
    store = make_store()
    with store.tick("t1") as tx:
        a = tx.compose("px.a", "fn.add", {"v": "px.x"})
        b = tx.compose("px.b", "fn.add", {"v": "px.a"})
    assert store.get("px.b") is b
    g = lineage_graph(b)
    assert g.nodes == (b, store.get("fn.add"), a, store.get("px.x"))
    assert g.get_edge(a, b).label == "v" and g.get_edge(store.get("px.x"), a).label == "v"


def test_lineage_after_a_failed_tick_has_nothing_to_graph():
    """A rolled-back tick binds nothing: the store's lineage graph is EMPTY, even though FAILED receipts exist."""
    store = PxC()
    calc = Part(add)
    orphan = None
    with pytest.raises(RuntimeError):
        with store.tick("bad") as tx:
            orphan = tx.compose("px.a", calc, {"v": Part(1)})
            raise RuntimeError("abort the tick")
    assert store.entries() == () and all(r.status is ReceiptStatus.FAILED for r in store.receipts())
    g = store_lineage_graph(store)
    assert g.nodes == () and g.edges == () and g.directed and g.closed_world, "nothing bound, nothing to graph"
    assert len(lineage_graph(orphan).nodes) == 3, "the orphaned Part object still has lineage if you hold it"


def test_lineage_after_a_failed_compose_has_nothing_to_graph():
    """A calculation that raises leaves its address free and the store without lineage."""
    store = PxC()

    def boom(values):
        raise ValueError("no")

    with pytest.raises(ValueError):
        store.compose("px.a", Part(boom), {"v": Part(1)})
    assert store_lineage_graph(store).nodes == ()


def test_store_lineage_graph_unions_all_bound_parts_in_binding_order():
    """The store graph contains every bound Part's history once; node order follows binding order."""
    store = make_store()
    s = store.compose("px.s", "fn.add", {"x": "px.x"})
    g = store_lineage_graph(store)
    add_part, x, y = store.get("fn.add"), store.get("px.x"), store.get("px.y")
    assert g.nodes == (add_part, x, y, s)
    assert g.has_edge(x, s) and g.has_edge(add_part, s) and not g.has_edge(y, s)


def test_lineage_graph_rejects_non_parts():
    """Plain values and address strings are not Parts."""
    for bad in (5, "px.x", None):
        with pytest.raises(TypeError):
            lineage_graph(bad)
    with pytest.raises(TypeError):
        store_lineage_graph("not a store")


def test_lineage_of_a_1500_deep_chain_needs_no_recursion():
    """Deep derivations (a long pipeline) must not hit the recursion limit."""
    store = PxC()
    inc = Part(lambda v: v["v"] + 1)
    prev = Part(0)
    n = 1500
    for i in range(n):
        prev = store.compose(f"px.v{i}", inc, {"v": prev})
    g = lineage_graph(prev)
    assert len(g.nodes) == n + 2, "n composed Parts + the raw seed + the shared calculation"
    assert find_cycle(g) is None and len(topological_order(g)) == n + 2


@given(st.lists(st.lists(st.integers(min_value=0, max_value=30), max_size=3), min_size=1, max_size=12))
def test_lineage_graph_matches_a_manual_walk_of_composition_on_random_dags(spec):
    """Property: node set and edge set equal an independent traversal of `.composition`; the graph is acyclic."""
    calc = Part(add)
    store = PxC()
    parts = [Part(1), Part(2)]
    for i, picks in enumerate(spec):
        inputs = {f"in{k}": parts[p % len(parts)] for k, p in enumerate(picks)}
        parts.append(store.compose(f"px.p{i}", calc, inputs))
    root = parts[-1]
    g = lineage_graph(root)
    seen, edges, todo = {id(root): root}, set(), [root]
    while todo:
        p = todo.pop()
        c = p.composition
        if c is None:
            continue
        for dep in (c.calculation, *c.inputs.values()):
            edges.add((id(dep), id(p)))
            if id(dep) not in seen:
                seen[id(dep)] = dep
                todo.append(dep)
    assert {id(n) for n in g.nodes} == set(seen), "node set must be exactly what composition reaches"
    assert {(id(e.source), id(e.target)) for e in g.edges} == edges
    assert g.nodes[0] is root
    order = topological_order(g)
    pos = {id(n): i for i, n in enumerate(order)}
    assert all(pos[id(e.source)] < pos[id(e.target)] for e in g.edges)


# ============================================================================== formula_graph
def test_formula_graph_of_a_variable_is_one_node():
    """A leaf formula is a one-node tree."""
    g = formula_graph(Var("a"))
    assert g.nodes == (0,) and g.edges == ()


def test_formula_graph_preorder_numbering_and_labels_on_a_small_formula():
    """And(Not(a), b): ids 0=And 1=Not 2=a 3=b (left subtree fully numbered before the right)."""
    f = And(Not(Var("a")), Var("b"))
    g = formula_graph(f)
    assert g.nodes == (0, 1, 2, 3)
    assert {(e.source, e.target): e.label for e in g.edges} == {(0, 1): "left", (1, 2): "operand", (0, 3): "right"}
    assert formula_labels(f) == ("And", "Not", "Var:a", "Var:b")


def test_formula_graph_repeated_subformulas_are_distinct_nodes():
    """And(a, a) has THREE nodes: the two 'a' are different positions in the tree, so identity must be positional."""
    f = And(Var("a"), Var("a"))
    g = formula_graph(f)
    assert len(g.nodes) == size(f) == 3 and len(g.edges) == 2
    assert formula_labels(f) == ("And", "Var:a", "Var:a")


def test_formula_labels_for_constants_and_every_operator():
    """Constants print as Const:True/False; operators by class name; length equals size."""
    f = Iff(Implies(Const(True), Const(False)), Or(Var("p"), Not(Var("q"))))
    assert formula_labels(f) == ("Iff", "Implies", "Const:True", "Const:False", "Or", "Var:p", "Not", "Var:q")
    assert len(formula_labels(f)) == size(f)


def test_formula_graph_rejects_non_formulas():
    """Strings and Parts are not formulas."""
    for bad in ("a & b", 3, None):
        with pytest.raises(TypeError):
            formula_graph(bad)


def test_formula_graph_2000_deep_not_chain():
    """Iterative construction: a 2,000-deep formula has height 2000 and no recursion error."""
    f = Var("a")
    for _ in range(2000):
        f = Not(f)
    g = formula_graph(f)
    assert len(g.nodes) == size(f) == 2001
    assert max(bfs(g, 0).distance.values()) == 2000 == formula_height(f)


@given(formulas(max_leaves=10))
def test_formula_graph_is_a_tree_with_size_nodes_and_formula_height(f):
    """Property: node count == logic.size(f); n-1 edges; unique parent per non-root; all reachable from 0;
    BFS height from the root == formula height; edges and labels equal an independent preorder walk."""
    g = formula_graph(f)
    n = size(f)
    assert len(g.nodes) == n and g.nodes == tuple(range(n)), "nodes are the preorder indices 0..size-1"
    assert len(g.edges) == n - 1, "a tree on n nodes has n-1 edges"
    assert g.predecessors(0) == (), "the root has no parent"
    assert all(len(g.predecessors(v)) == 1 for v in range(1, n)), "every other node has exactly one parent"
    dist = bfs(g, 0).distance
    assert len(dist) == n, "every node is reachable from the root"
    assert max(dist.values()) == formula_height(f), "tree height == formula depth"
    expected = {(parent, i): slot for i, (_, parent, slot) in enumerate(preorder_nodes(f)) if parent is not None}
    assert {(e.source, e.target): e.label for e in g.edges} == expected
    assert find_cycle(g) is None
    assert len(formula_labels(f)) == n


# ================================================================================== import_graph
def make_tree(root, files):
    for rel, text in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    return root / "dsdk"


def edges_of(g):
    return {(e.source, e.target) for e in g.edges}


def test_import_graph_nodes_are_sorted_subpackages_only(tmp_path):
    """Nodes: immediate subdirectories with __init__.py, sorted; plain modules, __pycache__, non-packages excluded."""
    root = make_tree(tmp_path, {
        "dsdk/__init__.py": "", "dsdk/top_module.py": "", "dsdk/zeta/__init__.py": "", "dsdk/alpha/__init__.py": "",
        "dsdk/plain/readme.py": "", "dsdk/__pycache__/x.py": "",
    })
    g = import_graph(root)
    assert g.nodes == ("dsdk.alpha", "dsdk.zeta") and g.edges == ()
    assert g.directed and g.closed_world


def test_import_graph_absolute_imports_point_from_importer_to_dependency(tmp_path):
    """`from dsdk.b import x` and `import dsdk.c.sub as s` inside package a give edges a->b and a->c."""
    root = make_tree(tmp_path, {
        "dsdk/__init__.py": "", "dsdk/a/__init__.py": "from dsdk.b import x\nimport dsdk.c.sub as s\n",
        "dsdk/b/__init__.py": "", "dsdk/c/__init__.py": "", "dsdk/c/sub.py": "",
    })
    g = import_graph(root)
    assert edges_of(g) == {("dsdk.a", "dsdk.b"), ("dsdk.a", "dsdk.c")}
    assert all(e.evidence is Status.KNOWN and e.label is None for e in g.edges)


def test_import_graph_resolves_relative_imports_and_skips_own_package(tmp_path):
    """Level-1 relative imports stay inside the package (no edge); level-2 climbs to a sibling; `from .. import c` too."""
    root = make_tree(tmp_path, {
        "dsdk/__init__.py": "",
        "dsdk/a/__init__.py": "from .inner import q\nfrom . import inner\n",
        "dsdk/a/inner.py": "from ..b import y\nfrom .. import c\n",
        "dsdk/b/__init__.py": "", "dsdk/c/__init__.py": "",
    })
    assert edges_of(import_graph(root)) == {("dsdk.a", "dsdk.b"), ("dsdk.a", "dsdk.c")}


def test_import_graph_relative_import_depth_counts_from_the_files_own_package(tmp_path):
    """In dsdk/a/deep/mod.py: `from ..b` resolves to dsdk.a.b (own package: no edge); `from ... import b` reaches dsdk.b."""
    root = make_tree(tmp_path, {
        "dsdk/__init__.py": "", "dsdk/a/__init__.py": "", "dsdk/a/deep/__init__.py": "",
        "dsdk/a/deep/mod.py": "from ..b import q\n",
        "dsdk/a/deep/mod2.py": "from ... import b\n",
        "dsdk/b/__init__.py": "", "dsdk/c/__init__.py": "",
    })
    g = import_graph(root)
    assert edges_of(g) == {("dsdk.a", "dsdk.b")}, "mod2 gives a->b; mod's ..b is dsdk.a.b, inside a"


def test_import_graph_from_top_import_subpackage_and_non_package_names(tmp_path):
    """`from dsdk import b, notapkg`: b is a subpackage (edge), notapkg is not (ignored, no error)."""
    root = make_tree(tmp_path, {
        "dsdk/__init__.py": "", "dsdk/a/__init__.py": "from dsdk import b, notapkg\n", "dsdk/b/__init__.py": "",
    })
    assert edges_of(import_graph(root)) == {("dsdk.a", "dsdk.b")}


def test_import_graph_counts_function_level_and_type_checking_imports_but_not_comments_or_strings(tmp_path):
    """ast.walk semantics: nested imports count; text that merely looks like an import does not."""
    root = make_tree(tmp_path, {
        "dsdk/__init__.py": "",
        "dsdk/a/__init__.py": (
            "# from dsdk.b import x\n"
            "DOC = 'import dsdk.c'\n"
            "def f():\n    from dsdk.d import y\n"
            "from typing import TYPE_CHECKING\n"
            "if TYPE_CHECKING:\n    import dsdk.e\n"
        ),
        "dsdk/b/__init__.py": "", "dsdk/c/__init__.py": "", "dsdk/d/__init__.py": "", "dsdk/e/__init__.py": "",
    })
    assert edges_of(import_graph(root)) == {("dsdk.a", "dsdk.d"), ("dsdk.a", "dsdk.e")}


def test_import_graph_ignores_stdlib_third_party_other_tops_and_self_imports(tmp_path):
    """Only imports of sibling subpackages of the SAME top package count."""
    root = make_tree(tmp_path, {
        "dsdk/__init__.py": "",
        "dsdk/a/__init__.py": "import os\nimport numpy\nfrom other.b import x\nimport dsdkextra.b\nfrom dsdk.a import y\n",
        "dsdk/b/__init__.py": "",
    })
    assert import_graph(root).edges == ()


def test_import_graph_accepts_str_or_path_and_rejects_missing_directory(tmp_path):
    """The argument may be a str; a directory that does not exist is FileNotFoundError."""
    root = make_tree(tmp_path, {"dsdk/__init__.py": "", "dsdk/a/__init__.py": ""})
    assert import_graph(str(root)) == import_graph(root)
    with pytest.raises(FileNotFoundError):
        import_graph(tmp_path / "nope")


def test_import_graph_syntax_error_propagates(tmp_path):
    """A broken file is reported, not skipped silently (silently skipping would hide an import)."""
    root = make_tree(tmp_path, {"dsdk/__init__.py": "", "dsdk/a/__init__.py": "def (:\n", "dsdk/b/__init__.py": ""})
    with pytest.raises(SyntaxError):
        import_graph(root)


def test_import_graph_detects_an_import_cycle(tmp_path):
    """The reason this graph exists: two packages importing each other is a cycle with a topological-sort failure."""
    root = make_tree(tmp_path, {
        "dsdk/__init__.py": "", "dsdk/a/__init__.py": "import dsdk.b\n", "dsdk/b/__init__.py": "import dsdk.a\n",
    })
    g = import_graph(root)
    assert find_cycle(g) == ("dsdk.a", "dsdk.b", "dsdk.a")
    with pytest.raises(CycleError):
        topological_order(g)
