"""dsdk.worlds must GENUINELY consume dsdk.core and dsdk.graph (tracks.toml: order 5, min_imports 2).

An import that nothing uses would satisfy tests/test_reuse.py; this file checks that specific names from earlier
packages are imported AND used, so the diagonal-reuse rule cannot be met by decoration.
"""
import ast
from pathlib import Path

from dsdk.graph import import_graph

SRC = Path(__file__).resolve().parents[2] / "src" / "dsdk"


def used_names(package_file: str, module: str) -> set[str]:
    tree = ast.parse((SRC / "worlds" / package_file).read_text())
    imported = {a.asname or a.name for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.level == 0 and n.module == module for a in n.names}
    loaded = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)}
    return imported & loaded


def test_worlds_imports_core_and_graph_in_the_import_graph():
    g = import_graph(SRC)
    assert g.has_edge("dsdk.worlds", "dsdk.core") and g.has_edge("dsdk.worlds", "dsdk.graph")
    assert not any(e.source != "dsdk.worlds" and e.target == "dsdk.worlds" for e in g.edges), "nothing earlier imports worlds"


def test_lostlands_uses_core_parts_and_judgments():
    assert {"Part", "PxC", "Judgment", "Status"} <= used_names("lostlands.py", "dsdk.core")


def test_networks_uses_core_status_judgment_and_graph_machinery():
    assert {"Judgment", "Status"} <= used_names("networks.py", "dsdk.core")
    assert {"Graph", "Edge", "known_subgraph"} <= used_names("networks.py", "dsdk.graph")


def test_buildlog_uses_judgment_for_its_answer():
    assert {"Judgment", "Status"} <= used_names("buildlog.py", "dsdk.core")
