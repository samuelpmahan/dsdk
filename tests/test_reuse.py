"""Diagonal-scaling guard.

Each dsdk package must visibly build on earlier packages (tracks.toml).
This is the mechanical form of "every track consumes earlier work":
a package that imports nothing earlier is an island and fails here.

TODO(A5): once dsdk.graph exists, compute this with dsdk's own graph code
(topological order + reachability) instead of the ad-hoc dict below.
"""
from __future__ import annotations

import ast
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
REGISTRY = tomllib.loads((ROOT / "tracks.toml").read_text())["packages"]


def _package_of(module: str) -> str | None:
    parts = module.split(".")
    if len(parts) >= 2 and parts[0] == "dsdk":
        return ".".join(parts[:2])
    return None


def _imports_of(package: str) -> set[str]:
    pkg_dir = SRC / Path(*package.split("."))
    found: set[str] = set()
    for path in pkg_dir.rglob("*.py"):
        tree = ast.parse(path.read_text(), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                names = [node.module]
            else:
                continue
            for name in names:
                target = _package_of(name)
                if target and target != package:
                    found.add(target)
    return found


def _on_disk() -> set[str]:
    return {
        f"dsdk.{p.name}"
        for p in (SRC / "dsdk").iterdir()
        if p.is_dir() and (p / "__init__.py").exists()
    }


def test_every_package_is_registered():
    missing = _on_disk() - set(REGISTRY)
    assert not missing, f"Register these in tracks.toml with a track and order: {sorted(missing)}"


def test_registered_packages_exist():
    ghosts = set(REGISTRY) - _on_disk()
    assert not ghosts, f"tracks.toml lists packages that do not exist: {sorted(ghosts)}"


def test_packages_only_import_earlier_packages():
    for package, meta in REGISTRY.items():
        for dep in _imports_of(package):
            assert dep in REGISTRY, f"{package} imports unregistered {dep}"
            assert REGISTRY[dep]["order"] < meta["order"], (
                f"{package} (order {meta['order']}) imports {dep} "
                f"(order {REGISTRY[dep]['order']}): dependencies must point backwards"
            )


def test_packages_build_on_enough_earlier_work():
    for package, meta in REGISTRY.items():
        deps = _imports_of(package)
        need = meta["min_imports"]
        if need < 2:
            assert meta.get("waiver"), f"{package} has min_imports<2 without a waiver"
        assert len(deps) >= need, (
            f"{package} ({meta['track']}) imports {sorted(deps) or 'nothing'} but must build on "
            f"at least {need} earlier package(s). Islands are not allowed."
        )
