"""Bayes-net structure as a ``dsdk.graph`` DAG, with exact joint distributions (track A3 x A5).

A :class:`BayesNet` is a directed ``dsdk.graph.Graph`` (an edge ``parent -> child``) plus a conditional probability table
(CPT) for every node. All variables are Boolean; the node IDs ARE the variable names (``str``).

CPT format: ``cpts[node]`` maps a tuple of parent values to ``P(node is true | parents)``. The parent tuple lists the parents
in ``structure.predecessors(node)`` order (the graph's node order), each ``True``/``False``. A root has the single key ``()``.
A node with ``k`` parents needs all ``2**k`` keys.

Graph semantics used on purpose: every edge must have evidence ``Status.KNOWN``. An edge that is only inferred (``UNKNOWN``) or a
candidate (``NOT_OBSERVED``) is a structural claim nobody has verified, so an exact joint distribution built on it would be
fabricated certainty: it is a ``ValueError``.
"""
from __future__ import annotations

import itertools
from dataclasses import dataclass
from fractions import Fraction
from typing import Mapping

from dsdk.core import Status
from dsdk.graph import CycleError, Edge, Graph, bfs, find_cycle
from dsdk.logic import Const, models

from .exact import to_prob
from .worlds import MAX_VARIABLES, Belief, WeightedWorld


@dataclass(frozen=True)
class BayesNet:
    """Validated network. Build it with :func:`bayes_net`; direct construction bypasses validation.

    * ``structure``  the DAG (``Graph``, directed, acyclic, all edges ``KNOWN``).
    * ``cpts``       ``{node: {parent_values_tuple: Fraction}}`` as described in the module docstring. Treat as read-only.
    """

    structure: Graph
    cpts: Mapping[str, Mapping[tuple[bool, ...], Fraction]]


def bayes_net(structure: Graph, cpts: Mapping[str, Mapping[tuple[bool, ...], object]]) -> BayesNet:
    """Validate and build a :class:`BayesNet`. Checks run in this order; the first violated one raises.

    1. ``structure`` must be a ``Graph`` (``TypeError``); ``cpts`` a ``Mapping`` (``TypeError``).
    2. ``structure.directed`` must be true (``ValueError``).
    3. Every node is a ``str`` (``TypeError``).
    4. Every edge has evidence ``Status.KNOWN`` (``ValueError``; the message names the edge).
    5. No cycle: ``dsdk.graph.find_cycle`` must return ``None``, else raise ``dsdk.graph.CycleError(witness)``
       (a self-loop is a cycle).
    6. ``cpts`` has exactly one entry per node: a missing or extra node is a ``ValueError`` naming it.
    7. Each CPT is a ``Mapping`` (``TypeError``) whose keys are tuples of exactly ``len(parents)`` values that are each
       exactly ``bool`` (``ValueError`` for wrong length or non-bool element) and cover all ``2**k`` combinations with no
       missing key (``ValueError``). Each value goes through ``to_prob`` (``TypeError``/``ValueError``).

    The returned net stores its own copies: later changes to the caller's dicts do not affect it.
    """
    if not isinstance(structure, Graph):
        raise TypeError(f"structure must be a Graph, not {type(structure).__name__}")
    if not isinstance(cpts, Mapping):
        raise TypeError(f"cpts must be a Mapping, not {type(cpts).__name__}")
    if not structure.directed:
        raise ValueError("a Bayes net needs a directed graph")
    for node in structure.nodes:
        if not isinstance(node, str):
            raise TypeError(f"Bayes net node ids are variable names (str), not {type(node).__name__}: {node!r}")
    for edge in structure.edges:
        if edge.evidence is not Status.KNOWN:
            raise ValueError(
                f"edge {edge.source!r} -> {edge.target!r} has evidence {edge.evidence.name}; a Bayes net needs KNOWN edges"
            )
    cycle = find_cycle(structure)
    if cycle is not None:
        raise CycleError(cycle)
    nodes = set(structure.nodes)
    given = set(cpts.keys())
    missing = sorted(nodes - given, key=repr)
    extra = sorted(given - nodes, key=repr)
    if missing:
        raise ValueError(f"no CPT for node(s): {', '.join(map(repr, missing))}")
    if extra:
        raise ValueError(f"CPT given for node(s) not in the graph: {', '.join(map(repr, extra))}")
    cleaned: dict[str, dict[tuple[bool, ...], Fraction]] = {}
    for node in structure.nodes:
        table = cpts[node]
        if not isinstance(table, Mapping):
            raise TypeError(f"CPT of {node!r} must be a Mapping, not {type(table).__name__}")
        k = len(structure.predecessors(node))
        for key in table.keys():
            if not isinstance(key, tuple) or len(key) != k:
                raise ValueError(f"CPT key {key!r} of {node!r} must be a tuple of {k} parent value(s)")
            if not all(type(v) is bool for v in key):
                raise ValueError(f"CPT key {key!r} of {node!r} must hold only True/False")
        expected = set(itertools.product([False, True], repeat=k))
        if set(table.keys()) != expected:
            raise ValueError(f"CPT of {node!r} must have exactly the {2 ** k} parent combinations of True/False")
        cleaned[node] = {tuple(key): to_prob(table[key], f"CPT[{node!r}]") for key in table.keys()}
    return BayesNet(structure=structure, cpts=cleaned)


def joint_belief(net: BayesNet) -> Belief:
    """The exact joint distribution as a :class:`Belief` over ``sorted(net.structure.nodes)``.

    Worlds: ``dsdk.logic.models(Const(True), over=variables)`` order (all assignments). The weight of a world is the product
    over nodes of ``P(node = its value | its parents' values in this world)`` read from the CPT. The weights sum to exactly
    ``Fraction(1)``. More than ``MAX_VARIABLES`` nodes: ``ValueError``. ``TypeError`` for a non-BayesNet.
    """
    if not isinstance(net, BayesNet):
        raise TypeError(f"joint_belief takes a BayesNet, not {type(net).__name__}")
    names = tuple(sorted(net.structure.nodes))
    if len(names) > MAX_VARIABLES:
        raise ValueError(f"a joint over {len(names)} variables exceeds the limit of {MAX_VARIABLES}")
    parents = {n: net.structure.predecessors(n) for n in names}
    worlds = []
    for model in models(Const(True), over=names):
        weight = Fraction(1)
        for n in names:
            p = net.cpts[n][tuple(model[q] for q in parents[n])]
            weight *= p if model[n] else 1 - p
        worlds.append(WeightedWorld(values=tuple((n, model[n]) for n in names), weight=weight))
    return Belief(variables=names, worlds=tuple(worlds))


def ancestors(net: BayesNet, node: str) -> frozenset[str]:
    """All proper ancestors of ``node`` (parents, their parents, ...; ``node`` itself is NOT included, and in a DAG it cannot
    be its own ancestor). Computed with ``dsdk.graph.bfs`` on ``structure.reverse()``. ``dsdk.graph.MissingNodeError`` for a
    node not in the net; ``TypeError`` for a non-BayesNet."""
    if not isinstance(net, BayesNet):
        raise TypeError(f"ancestors takes a BayesNet, not {type(net).__name__}")
    reached = bfs(net.structure.reverse(), node).distance
    return frozenset(k for k in reached if k != node)


def ancestral_net(net: BayesNet, nodes: set[str] | frozenset[str]) -> BayesNet:
    """The sub-network on ``nodes`` plus all their ancestors (the *ancestral set*). It keeps those nodes in the original node
    order, the edges among them, and their CPTs unchanged (a kept node keeps all its parents, because the set is closed under
    ancestors). Key fact (tested): the marginal of any kept variable under :func:`joint_belief` of this smaller net equals its
    marginal under the full net, so barren descendants never need to be enumerated. ``MissingNodeError`` for a node not in
    the net; ``TypeError`` for a non-BayesNet or a ``nodes`` that is not a set/frozenset of str.
    """
    if not isinstance(net, BayesNet):
        raise TypeError(f"ancestral_net takes a BayesNet, not {type(net).__name__}")
    if not isinstance(nodes, (set, frozenset)):
        raise TypeError(f"nodes must be a set or frozenset of str, not {type(nodes).__name__}")
    for n in nodes:
        if not isinstance(n, str):
            raise TypeError(f"nodes must hold only str, not {type(n).__name__}: {n!r}")
    keep = set(nodes)
    for n in nodes:
        keep |= ancestors(net, n)
    order = [n for n in net.structure.nodes if n in keep]
    edges = [
        Edge(e.source, e.target, weight=e.weight, evidence=e.evidence, label=e.label)
        for e in net.structure.edges
        if e.source in keep and e.target in keep
    ]
    sub = Graph.from_edges(edges, order, directed=True, closed_world=net.structure.closed_world)
    cpts = {n: dict(net.cpts[n]) for n in order}
    return BayesNet(sub, cpts)
