"""Reachability as logic: graph witness paths become CHECKED proofs and non-reachability becomes a COUNTERMODEL (graph x logic x core).

Reading a graph as a set of implications
----------------------------------------
Node ``g.nodes[i]`` is the propositional variable ``Var(f"n{i}")`` (index based, so ANY hashable node works and two different nodes can
never share a variable). A KNOWN arrow ``u -> v`` is the premise ``Implies(var(u), var(v))``. An undirected KNOWN edge ``{u, v}`` gives both
arrows (one premise for a self-loop). Premises are listed in ``g.edges`` order (undirected: the stored orientation first, then the reverse).
"``target`` is reachable from ``source``" then means exactly: the premises together with ``var(source)`` ENTAIL ``var(target)``.

Uncertain edges
---------------
ONLY edges with evidence ``Status.KNOWN`` become premises (the same rule as ``dsdk.graph.reachable``'s "KNOWN True"). An UNKNOWN (inferred) or
NOT_OBSERVED (candidate) edge is never a premise, so a proof can never rest on a guess, and a countermodel only says "not derivable from the
OBSERVED edges". Whether that means "unreachable" depends on the world flag and on the uncertain edges; see :class:`Countermodel.unreachable`.

All functions return a ``dsdk.core.Judgment`` for questions about nodes and never raise for them (only ``TypeError`` for a non-Graph).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Hashable

from dsdk.core import Judgment, Status
from dsdk.logic import CheckResult, Formula, Implies, Rule, Step, Var, check, countermodel, entails, evaluate

from .evidence import known_subgraph, reachable
from .model import Graph
from .traverse import bfs, shortest_path

MAX_ENUM_NODES = 10
"""Largest node count for which the brute-force logic routes (``entails`` / ``countermodel`` enumerate 2**n assignments) are run."""


@dataclass(frozen=True)
class GraphProof:
    """A checked proof that ``target`` is reachable from ``source`` using KNOWN edges only.

    * ``path``      the breadth-first witness ``(source, ..., target)`` (``dsdk.graph.shortest_path`` of the KNOWN subgraph).
    * ``premises``  the premises the proof is checked against: ``var(source)`` first, then :func:`known_premises` ``(g)``.
    * ``steps``     the proof, ``2 * (len(path) - 1) + 1`` steps (see :func:`witness_proof`).
    """

    path: tuple[Hashable, ...]
    premises: tuple[Formula, ...]
    steps: tuple[Step, ...]


@dataclass(frozen=True)
class Countermodel:
    """A truth assignment showing ``target`` is NOT derivable from ``source`` using the KNOWN edges.

    * ``reached``       the nodes reachable from ``source`` over KNOWN edges, in graph node order (these are the true variables).
    * ``assignment``    ``{variable name: bool}`` for EVERY node of the graph (true exactly for ``reached``).
    * ``premises``      as in :class:`GraphProof` (``var(source)`` first).
    * ``unreachable``   True iff ``dsdk.graph.reachable(g, source, target)`` is KNOWN False (a closed world where not even uncertain edges connect them).
                        False means only "not derivable from the observed edges": either the world is open or an uncertain edge could connect them.
    * ``logic_countermodel``  the FIRST countermodel in ``dsdk.logic`` enumeration order, found by ``logic.countermodel(premises, var(target))``,
                        or ``None`` when the graph has more than ``MAX_ENUM_NODES`` nodes (``cross_checked`` is then False).
    * ``cross_checked`` True iff the brute-force logic routes were run and agreed (``entails`` False and a countermodel exists).
    """

    reached: tuple[Hashable, ...]
    assignment: dict[str, bool]
    premises: tuple[Formula, ...]
    unreachable: bool
    logic_countermodel: dict[str, bool] | None
    cross_checked: bool


def node_var(g: Graph, node: Hashable) -> Var:
    """The variable of ``node``: ``Var(f"n{g.index_of(node)}")``. ``dsdk.graph.MissingNodeError`` for an absent node; ``TypeError`` for a non-Graph."""
    if not isinstance(g, Graph):
        raise TypeError(f"expected a Graph, got {type(g).__name__}")
    return Var(f"n{g.index_of(node)}")


def known_premises(g: Graph) -> tuple[Formula, ...]:
    """One ``Implies(var(u), var(v))`` per KNOWN arrow, in ``g.edges`` order; an undirected KNOWN edge ``{u, v}`` contributes ``u -> v`` then
    ``v -> u`` (just one premise when ``u == v``). Edges with evidence other than ``Status.KNOWN`` contribute nothing. ``TypeError`` for a non-Graph."""
    if not isinstance(g, Graph):
        raise TypeError(f"expected a Graph, got {type(g).__name__}")
    out: list[Formula] = []
    for e in g.edges:
        if e.evidence is not Status.KNOWN:
            continue
        out.append(Implies(node_var(g, e.source), node_var(g, e.target)))
        if not g.directed and e.source != e.target:
            out.append(Implies(node_var(g, e.target), node_var(g, e.source)))
    return tuple(out)


def _missing(g: Graph, source: Hashable, target: Hashable) -> Judgment | None:
    for node in (source, target):
        if not g.has_node(node):
            return Judgment(Status.INVALID, None, f"node {node!r} is not in the graph")
    return None


def witness_proof(g: Graph, source: Hashable, target: Hashable) -> Judgment:
    """A checked modus-ponens proof of "target is reachable from source" over KNOWN edges.

    * ``TypeError`` for a non-Graph. A node that is not in the graph: ``INVALID`` with the reason ``f"node {node!r} is not in the graph"``
      (the source is named first), exactly like ``dsdk.graph.reachable``.
    * ``dsdk.graph.reachable(g, source, target)`` decides the status. KNOWN True -> ``KNOWN`` with a :class:`GraphProof`. UNKNOWN (only uncertain
      edges would connect them, or an open world) -> ``UNKNOWN`` with the reason of ``reachable`` unchanged and NO proof. KNOWN False (closed
      world, not connected at all) -> ``NOT_APPLICABLE`` with a reason that starts ``"no proof exists:"`` and points to
      :func:`unreachability_countermodel`.
    * The proof, for the path ``p0, p1, ..., pk`` (``p0 = source``, ``pk = target``), is exactly::

          step 0        Step(var(p0), Rule.PREMISE, ())
          step 2i - 1   Step(Implies(var(p_{i-1}), var(p_i)), Rule.PREMISE, ())              for i = 1..k
          step 2i       Step(var(p_i), Rule.MODUS_PONENS, (2i - 1, 2i - 2))                  for i = 1..k

      so ``source == target`` gives the single premise step, and the last step's formula is ``var(target)``. The path is the
      ``shortest_path`` of ``known_subgraph(g)``. Before returning, the function runs ``dsdk.logic.check(steps, premises)``; if that ever fails it
      returns ``INVALID`` with a reason starting ``"proof failed its own check:"`` (it cannot happen for a correct implementation).
    """
    if not isinstance(g, Graph):
        raise TypeError(f"expected a Graph, got {type(g).__name__}")
    missing = _missing(g, source, target)
    if missing is not None:
        return missing
    verdict = reachable(g, source, target)
    if verdict.status is Status.UNKNOWN:
        return verdict
    if verdict.status is Status.KNOWN and verdict.value is False:
        return Judgment(
            Status.NOT_APPLICABLE, None,
            f"no proof exists: {target!r} is not reachable from {source!r}; ask for the countermodel instead",
        )
    path = shortest_path(known_subgraph(g), source, target)
    if path is None:
        return Judgment(Status.INVALID, None, "proof failed its own check: no KNOWN path found for a KNOWN True verdict")
    steps: list[Step] = [Step(node_var(g, path[0]), Rule.PREMISE, ())]
    for i in range(1, len(path)):
        steps.append(Step(Implies(node_var(g, path[i - 1]), node_var(g, path[i])), Rule.PREMISE, ()))
        steps.append(Step(node_var(g, path[i]), Rule.MODUS_PONENS, (2 * i - 1, 2 * i - 2)))
    premises = (node_var(g, source),) + known_premises(g)
    result = check(steps, premises)
    if not result.ok:
        return Judgment(Status.INVALID, None, "proof failed its own check: " + result.reason)
    return Judgment(Status.KNOWN, GraphProof(tuple(path), premises, tuple(steps)), "")


def unreachability_countermodel(g: Graph, source: Hashable, target: Hashable) -> Judgment:
    """A truth assignment under which every KNOWN-edge premise and ``var(source)`` are true but ``var(target)`` is false.

    * ``TypeError`` / missing node: as :func:`witness_proof`.
    * If ``target`` IS reachable from ``source`` over KNOWN edges no countermodel exists: ``NOT_APPLICABLE`` with a reason starting
      ``"no countermodel exists:"``.
    * Otherwise ``KNOWN`` with a :class:`Countermodel`. The assignment is built from the graph side: node ``n`` is true iff it is reached from
      ``source`` by ``dsdk.graph.bfs`` on the KNOWN subgraph (so ``source`` is true, ``target`` false, and every KNOWN arrow ``u -> v`` with ``u``
      true has ``v`` true, i.e. every premise holds). Before returning, every premise is evaluated with ``dsdk.logic.evaluate`` under the assignment
      (they must all be true and ``var(target)`` false, else ``INVALID`` with a reason starting ``"countermodel failed its own check:"``).
    * If the graph has at most ``MAX_ENUM_NODES`` nodes the brute-force logic routes also run: ``entails(premises, var(target))`` must be False and
      ``logic.countermodel(premises, var(target))`` supplies ``logic_countermodel`` (``cross_checked=True``); a disagreement gives ``INVALID``
      with a reason starting ``"logic disagrees:"``. Larger graphs skip this step (``logic_countermodel=None``, ``cross_checked=False``).
    * ``unreachable`` is True iff ``reachable(g, source, target)`` is KNOWN False.
    """
    if not isinstance(g, Graph):
        raise TypeError(f"expected a Graph, got {type(g).__name__}")
    missing = _missing(g, source, target)
    if missing is not None:
        return missing
    reached = set(bfs(known_subgraph(g), source).distance)
    if target in reached:
        return Judgment(
            Status.NOT_APPLICABLE, None,
            f"no countermodel exists: {target!r} is reachable from {source!r} over KNOWN edges",
        )
    assignment = {f"n{i}": node in reached for i, node in enumerate(g.nodes)}
    premises = (node_var(g, source),) + known_premises(g)
    goal = node_var(g, target)
    for f in premises:
        if not evaluate(f, assignment):
            return Judgment(Status.INVALID, None, f"countermodel failed its own check: premise {f!r} is false")
    if evaluate(goal, assignment):
        return Judgment(Status.INVALID, None, "countermodel failed its own check: target is true")
    if len(g.nodes) <= MAX_ENUM_NODES:
        logic_cm = countermodel(premises, goal)
        if entails(premises, goal) or logic_cm is None:
            return Judgment(Status.INVALID, None, "logic disagrees: no countermodel found by dsdk.logic for a non-entailed goal")
        cross_checked = True
    else:
        logic_cm = None
        cross_checked = False
    verdict = reachable(g, source, target)
    unreachable = verdict.status is Status.KNOWN and verdict.value is False
    cm = Countermodel(
        tuple(node for node in g.nodes if node in reached), assignment, premises, unreachable, logic_cm, cross_checked,
    )
    return Judgment(Status.KNOWN, cm, "")


def entailed_by_known_edges(g: Graph, source: Hashable, target: Hashable) -> Judgment:
    """The LOGIC route to reachability, for cross-checking the graph route: ``KNOWN`` with the bool
    ``entails([var(source)] + known_premises(g), var(target))``.

    ``TypeError`` / missing node as in :func:`witness_proof`. More than ``MAX_ENUM_NODES`` nodes: ``UNKNOWN`` with a reason starting
    ``"too many nodes to enumerate"`` (brute force would need 2**n assignments). Equals ``target in bfs(known_subgraph(g), source).distance``
    on every graph this function answers for.
    """
    if not isinstance(g, Graph):
        raise TypeError(f"expected a Graph, got {type(g).__name__}")
    missing = _missing(g, source, target)
    if missing is not None:
        return missing
    if len(g.nodes) > MAX_ENUM_NODES:
        return Judgment(Status.UNKNOWN, None, f"too many nodes to enumerate: {len(g.nodes)} > {MAX_ENUM_NODES}")
    return Judgment(Status.KNOWN, bool(entails((node_var(g, source),) + known_premises(g), node_var(g, target))), "")
