"""Bridges: dsdk.graph applied to the other tracks' data (the diagonal-reuse rule in action).

* ``lineage_graph`` / ``store_lineage_graph``: the lineage DAG of ``dsdk.core`` Parts (A0).
* ``formula_graph`` / ``formula_labels``: the syntax tree of a ``dsdk.logic`` formula (A1).
* ``import_graph``: dsdk's own package import graph, so dsdk can check its own reuse rule with its own graph code.

Everything is iterative (no recursion): lineage chains and formulas can be deeper than the recursion limit.
"""
from __future__ import annotations

from collections import deque
from pathlib import Path
from typing import Hashable

from dsdk.core import Part, PxC
from dsdk.logic import And, Const, Formula, Iff, Implies, Not, Or, Var

from .model import Edge, Graph

CALCULATION_LABEL = "<calculation>"
"""Edge label of the edge from a calculation Part to the Part it produced (input edges carry the input NAME)."""

FORMULA_CHILD_LABELS: dict[type, tuple[str, ...]] = {
    Not: ("operand",),
    And: ("left", "right"),
    Or: ("left", "right"),
    Implies: ("left", "right"),
    Iff: ("left", "right"),
}
"""Child field names, in child order, of each non-leaf formula class. ``Const`` and ``Var`` are leaves."""


def _lineage_walk(start: Part, seen: set, nodes: list, edges: list) -> None:
    """Breadth-first walk backwards from ``start``, appending new Parts to ``nodes`` and new edges to ``edges``.

    ``seen`` is shared between walks so that a Part reached again is not listed or expanded twice.
    """
    if start in seen:
        return
    seen.add(start)
    nodes.append(start)
    queue: deque[Part] = deque([start])
    while queue:
        out = queue.popleft()
        comp = out.composition
        if comp is None:
            continue
        upstream = [comp.calculation, *comp.inputs.values()]
        edges.append(Edge(comp.calculation, out, label=CALCULATION_LABEL))
        for name, inp in comp.inputs.items():
            edges.append(Edge(inp, out, label=name))
        for p in upstream:
            if p not in seen:
                seen.add(p)
                nodes.append(p)
                queue.append(p)


def _formula_preorder(f: Formula) -> list[tuple[Formula, int | None, str | None]]:
    """Preorder rows ``(node, parent_id, field_label)``; the index in the list is the node id.

    Iterative (explicit stack): children are pushed in reverse so the left child is numbered first.
    """
    rows: list[tuple[Formula, int | None, str | None]] = []
    stack: list[tuple[Formula, int | None, str | None]] = [(f, None, None)]
    while stack:
        node, parent, label = stack.pop()
        my_id = len(rows)
        rows.append((node, parent, label))
        for name in reversed(FORMULA_CHILD_LABELS.get(type(node), ())):
            stack.append((getattr(node, name), my_id, name))
    return rows


def lineage_graph(part: Part) -> Graph:
    """The lineage DAG of ``part``: every Part and calculation reachable BACKWARDS through ``.composition``.

    Node identity: the nodes ARE the ``Part`` objects themselves (``Part`` equality/hash is by identity, so two
    Parts holding equal values are two different nodes, and a Part shared by two compositions is ONE node). A
    calculation Part is a node like any other. Raw Parts (``composition is None``) are the leaves.

    Edges point from DEPENDENCY to DEPENDENT (the direction data flows), all with evidence ``Status.KNOWN``:
      * for each composed Part ``out`` and each ``(name, p)`` in ``out.composition.inputs.items()``: an edge
        ``p -> out`` with ``label=name``;
      * for each composed Part ``out``: an edge ``out.composition.calculation -> out`` with
        ``label=CALCULATION_LABEL``.
    If the same Part is passed under two input names the two edges merge and the label becomes
    ``"x,y"`` (sorted, per the duplicate rule of ``Graph``).

    Node ORDER (the deterministic tie-break): breadth-first discovery starting at ``part``; when a Part is
    expanded its calculation is discovered first, then its inputs in mapping order; each Part is listed once at
    its first discovery. So ``nodes[0] is part``. The graph is directed, acyclic and ``closed_world=True``
    (the composition record is complete). A raw Part gives a one-node graph with no edges.
    ``TypeError`` if ``part`` is not a ``Part``.
    """
    if not isinstance(part, Part):
        raise TypeError(f"expected a Part, got {type(part).__name__}")
    nodes: list = []
    edges: list = []
    _lineage_walk(part, set(), nodes, edges)
    return Graph.from_edges(edges, nodes, directed=True, closed_world=True)


def store_lineage_graph(store: PxC) -> Graph:
    """The union of ``lineage_graph(p)`` over every Part bound in ``store`` (``store.entries()``, in binding
    order). Node order: the nodes of the first bound Part's lineage in that function's order, then the
    not-yet-listed nodes of the second's, and so on. A store with nothing bound gives the EMPTY graph (no nodes, no
    edges, still directed and closed_world) -- e.g. after a tick that failed and so bound nothing: Parts that were
    only staged, or whose compose failed, are not in the store and not in the graph. ``TypeError`` for a
    non-``PxC``.
    """
    if not isinstance(store, PxC):
        raise TypeError(f"expected a PxC, got {type(store).__name__}")
    seen: set = set()
    nodes: list = []
    edges: list = []
    for _, part in store.entries():
        _lineage_walk(part, seen, nodes, edges)
    return Graph.from_edges(edges, nodes, directed=True, closed_world=True)


def formula_graph(f: Formula) -> Graph:
    """The syntax TREE of ``f`` as a directed graph.

    Nodes are the integers ``0 .. size(f) - 1``: the PREORDER index of each AST node (root = 0; for a binary node,
    the whole left subtree is numbered before the right subtree). Integers (not the sub-formulas) are the node
    identities because equal sub-formulas such as the two ``a`` in ``And(a, a)`` are different positions of the
    tree. Node order is ``0, 1, 2, ...``. Edges go parent -> child, evidence KNOWN, labelled with the field names
    from :data:`FORMULA_CHILD_LABELS` (``"operand"``, ``"left"``, ``"right"``). ``closed_world=True``.

    Properties (tested): ``len(g.nodes) == dsdk.logic.size(f)``; it has ``size(f) - 1`` edges; every non-root node
    has exactly one predecessor; every node is reachable from 0 (it is a tree); the largest BFS distance from 0
    equals the height of the formula (a leaf has height 0, ``Not(x)`` has height ``1 + height(x)``, a binary node
    ``1 + max`` of its children). ``TypeError`` if ``f`` is not a ``Formula``. Must handle 2,000-deep formulas.
    """
    if not isinstance(f, Formula):
        raise TypeError(f"expected a Formula, got {type(f).__name__}")
    rows = _formula_preorder(f)
    edges = [Edge(parent, my_id, label=label) for my_id, (_, parent, label) in enumerate(rows) if parent is not None]
    return Graph.from_edges(edges, range(len(rows)), directed=True, closed_world=True)


def formula_labels(f: Formula) -> tuple[str, ...]:
    """Human-readable label of each node of :func:`formula_graph`, indexed by node id: the class name for
    operators (``"And"``, ``"Not"``, ...), ``"Var:a"`` for ``Var("a")``, ``"Const:True"`` / ``"Const:False"`` for
    constants. ``len(result) == size(f)``."""
    if not isinstance(f, Formula):
        raise TypeError(f"expected a Formula, got {type(f).__name__}")
    labels: list[str] = []
    for node, _, _ in _formula_preorder(f):
        if isinstance(node, Var):
            labels.append(f"Var:{node.name}")
        elif isinstance(node, Const):
            labels.append(f"Const:{node.value}")
        else:
            labels.append(type(node).__name__)
    return tuple(labels)


def _import_targets(path: Path, pkg: list[str], top: str, subs: set[str]) -> set[str]:
    """Names of the subpackages (members of ``subs``) that the file ``path`` imports, anywhere in the file.

    ``pkg`` is the file's package path, e.g. ``["dsdk", "a", "deep"]`` for ``dsdk/a/deep/mod.py``. Resolution follows
    the rules in :func:`import_graph`. The caller removes the importing subpackage itself.
    """
    import ast

    tree = ast.parse(path.read_text())
    targets: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                parts = alias.name.split(".")
                if parts[0] == top and len(parts) >= 2:
                    targets.add(parts[1])
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0:
                full = (node.module or "").split(".")
            else:
                drop = node.level - 1
                if drop >= len(pkg):
                    continue
                full = pkg[: len(pkg) - drop] + (node.module.split(".") if node.module else [])
            if full[0] != top:
                continue
            if len(full) >= 2:
                targets.add(full[1])
            else:
                targets.update(alias.name for alias in node.names)
    return {name for name in targets if name in subs}


def import_graph(package_root: str | Path) -> Graph:
    """The import graph between the immediate subpackages of one package, e.g. ``dsdk.core``, ``dsdk.logic``.

    ``package_root`` is the DIRECTORY of the top-level package (``.../src/dsdk``); its ``name`` (``"dsdk"``)
    prefixes node names. Nodes: ``"dsdk.<sub>"`` for each immediate subdirectory containing ``__init__.py``,
    sorted by name (``__pycache__`` and plain modules are not nodes). ``FileNotFoundError`` if the directory does
    not exist.

    Edge ``A -> B`` (``A`` imports ``B``, so the arrow points at the dependency) iff some ``*.py`` file under
    ``package_root/<A>`` (recursively) contains, ANYWHERE in the file (use ``ast.walk``: function-level and
    ``TYPE_CHECKING`` imports count; comments and strings do not), an import that resolves to subpackage ``B != A``.
    Edges have evidence KNOWN, no label, and the graph is directed and ``closed_world=True``.

    Resolving an import to a subpackage (``top`` = ``package_root.name``):
      * ``import top.B`` / ``import top.B.x as y``                     -> ``top.B``
      * ``from top.B import x`` / ``from top.B.x import y``           -> ``top.B``
      * ``from top import B``  (a name that is a subpackage)          -> ``top.B`` (one edge per such name)
      * RELATIVE ``from .x import y`` (level 1) stays inside the importing file's own package -- no edge;
        ``from ..B import y`` (level 2) from ``top/A/mod.py`` resolves to ``top.B``; ``from .. import B`` likewise.
        Generally: take the importing file's package path (``[top, A, <dirs below A>]``), drop ``level - 1``
        trailing parts, append the ``module`` parts; if the result has >= 2 parts its second part is the target;
        if it is exactly ``[top]`` look at the imported names as in the ``from top import B`` case. A relative
        import that climbs above ``top`` is ignored.
      * anything else (standard library, third-party, other top-level names) is ignored.
    Imports of a name that is not a subpackage node are ignored (never an error). A ``SyntaxError`` in a file
    propagates.
    """
    root = Path(package_root)
    if not root.is_dir():
        raise FileNotFoundError(f"no such package directory: {root}")
    top = root.name
    subs = sorted(p.name for p in root.iterdir() if p.is_dir() and (p / "__init__.py").exists())
    sub_set = set(subs)
    edges: set[tuple[str, str]] = set()
    for a in subs:
        for path in (root / a).rglob("*.py"):
            pkg = [top, *path.parent.relative_to(root).parts]
            for b in _import_targets(path, pkg, top, sub_set):
                if b != a:
                    edges.add((a, b))
    nodes = [f"{top}.{name}" for name in subs]
    return Graph.from_edges(
        [Edge(f"{top}.{a}", f"{top}.{b}") for a, b in sorted(edges)],
        nodes,
        directed=True,
        closed_world=True,
    )
