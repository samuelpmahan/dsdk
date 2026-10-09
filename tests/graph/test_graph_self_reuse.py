"""dsdk checks its own diagonal-reuse rule (tracks.toml) with its own graph code.

This complements tests/test_reuse.py (which uses a hand-written AST scan and must not be edited): the same rule is
re-derived here from dsdk.graph.import_graph + topological_order + reverse(). If the two ever disagree, one of
them has a bug.
"""
import tomllib
from pathlib import Path

from dsdk.graph import (
    bfs, find_cycle, import_graph, strongly_connected_components, topological_order,
)

ROOT = Path(__file__).resolve().parents[2]
REGISTRY = tomllib.loads((ROOT / "tracks.toml").read_text())["packages"]
ORDER = {name: meta["order"] for name, meta in REGISTRY.items()}


def test_import_graph_nodes_are_exactly_the_registered_packages():
    """Every package on disk is registered in tracks.toml and vice versa (same check as test_reuse, via the graph)."""
    dsdk_imports = import_graph(ROOT / "src" / "dsdk")
    assert set(dsdk_imports.nodes) == set(REGISTRY)


def test_dsdk_import_graph_is_acyclic():
    """A cycle between dsdk packages would make 'build on earlier work' meaningless; the witness is shown on failure."""
    dsdk_imports = import_graph(ROOT / "src" / "dsdk")
    assert find_cycle(dsdk_imports) is None, f"dsdk packages import each other in a cycle: {find_cycle(dsdk_imports)}"
    assert all(len(c) == 1 for c in strongly_connected_components(dsdk_imports)), "no multi-package SCC either"


def test_every_import_edge_points_backwards_in_tracks_toml_order():
    """The rule: an importer's `order` is strictly greater than each dependency's (dependencies point backwards)."""
    dsdk_imports = import_graph(ROOT / "src" / "dsdk")
    for e in dsdk_imports.edges:
        assert ORDER[e.target] < ORDER[e.source], (
            f"{e.source} (order {ORDER[e.source]}) imports {e.target} (order {ORDER[e.target]}): "
            "dependencies must come from EARLIER tracks"
        )


def test_topological_order_of_dependencies_is_consistent_with_tracks_toml_order():
    """Reverse the arrows (dependency -> importer) and sort topologically: every edge's tail has a smaller `order`,
    so the topological order never contradicts the registry, and the registry order is itself a valid topological order."""
    dsdk_imports = import_graph(ROOT / "src" / "dsdk")
    deps_first = topological_order(dsdk_imports.reverse())
    position = {name: i for i, name in enumerate(deps_first)}
    for e in dsdk_imports.edges:
        assert position[e.target] < position[e.source], f"{e.target} must be built before {e.source}"
        assert ORDER[e.target] < ORDER[e.source]
    by_registry = sorted(REGISTRY, key=ORDER.get)
    registry_position = {name: i for i, name in enumerate(by_registry)}
    assert all(registry_position[e.target] < registry_position[e.source] for e in dsdk_imports.edges), \
        "tracks.toml order is a valid build order for the real import graph"


def test_every_package_builds_on_at_least_min_imports_earlier_packages():
    """Out-degree of each package (distinct dsdk packages it imports) is at least `min_imports`."""
    dsdk_imports = import_graph(ROOT / "src" / "dsdk")
    for name, meta in REGISTRY.items():
        deps = dsdk_imports.neighbors(name)
        assert len(deps) >= meta["min_imports"], (
            f"{name} imports {list(deps)} but tracks.toml requires >= {meta['min_imports']} earlier package(s)"
        )


def test_graph_package_genuinely_consumes_core_and_logic():
    """dsdk.graph (A5) must import dsdk.core AND dsdk.logic; reachability confirms nothing is an island."""
    dsdk_imports = import_graph(ROOT / "src" / "dsdk")
    assert dsdk_imports.has_edge("dsdk.graph", "dsdk.core") and dsdk_imports.has_edge("dsdk.graph", "dsdk.logic")
    reach = bfs(dsdk_imports, "dsdk.graph").distance
    assert {"dsdk.core", "dsdk.logic"} <= set(reach)


def test_core_imports_nothing_and_everything_reaches_core():
    """The kernel is the only root: it has no dependencies, and every other package transitively depends on it."""
    dsdk_imports = import_graph(ROOT / "src" / "dsdk")
    assert dsdk_imports.neighbors("dsdk.core") == ()
    for name in dsdk_imports.nodes:
        assert "dsdk.core" in bfs(dsdk_imports, name).distance, f"{name} does not build on dsdk.core"
