"""dsdk.prob must GENUINELY build on logic, core and graph (diagonal scaling), not merely import them.

Structural checks use dsdk.graph.import_graph (the A5 tool) plus an AST scan; behavioural proofs of use live in the other test files
(worlds ARE logic.models, answers ARE core.Judgment, updates ARE core ticks with lineage, nets ARE graph DAGs).
"""
import ast
import tomllib
from pathlib import Path

import pytest

from dsdk.graph import import_graph
from dsdk.logic import Var, models
from dsdk.prob import prior_belief

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src" / "dsdk"
REGISTRY = tomllib.loads((ROOT / "tracks.toml").read_text())["packages"]


def imported_packages(module_file):
    tree = ast.parse((SRC / "prob" / module_file).read_text())
    found = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.level == 0 and node.module and node.module.startswith("dsdk."):
            found.add(".".join(node.module.split(".")[:2]))
        elif isinstance(node, ast.Import):
            found |= {".".join(a.name.split(".")[:2]) for a in node.names if a.name.startswith("dsdk.")}
    return found


def test_prob_is_registered_after_graph_and_lang():
    meta = REGISTRY["dsdk.prob"]
    assert meta["track"] == "A3" and meta["order"] == 4 and meta["min_imports"] == 3
    assert REGISTRY["dsdk.graph"]["order"] == 3 and REGISTRY["dsdk.lang"]["order"] == 2
    assert not meta.get("waiver"), "prob needs no waiver: it has three earlier tracks to build on"


def test_import_graph_shows_edges_to_logic_core_and_graph_only_backwards():
    g = import_graph(SRC)
    out = {e.target for e in g.edges if e.source == "dsdk.prob"}
    assert {"dsdk.logic", "dsdk.core", "dsdk.graph"} <= out
    assert all(REGISTRY[t]["order"] < REGISTRY["dsdk.prob"]["order"] for t in out)
    assert not any(e.target == "dsdk.prob" and REGISTRY[e.source]["order"] <= REGISTRY["dsdk.prob"]["order"] for e in g.edges)


@pytest.mark.parametrize(
    "module,needs",
    [
        ("worlds.py", {"dsdk.logic", "dsdk.core"}),
        ("bayesnet.py", {"dsdk.logic", "dsdk.graph", "dsdk.core"}),
        ("sampling.py", {"dsdk.logic", "dsdk.graph", "dsdk.core"}),
        ("updates.py", {"dsdk.logic", "dsdk.core"}),
        ("transitions.py", {"dsdk.graph", "dsdk.core"}),
    ],
)
def test_each_module_imports_the_tracks_it_is_documented_to_use(module, needs):
    assert needs <= imported_packages(module)


def test_worlds_are_exactly_the_logic_models_not_a_second_enumeration():
    """Whatever prior_belief builds, its worlds are dsdk.logic.models of the constraint in the same order."""
    f = Var("a")
    b = prior_belief({"a": 0.5, "b": 0.5}, f)
    assert [w.assignment() for w in b.worlds] == list(models(f, over=["a", "b"]))
