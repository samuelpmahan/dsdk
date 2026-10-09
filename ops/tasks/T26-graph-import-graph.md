# T26-graph-import-graph

**Goal.** Implement `import_graph` in `src/dsdk/graph/bridges.py`, then confirm the WHOLE graph test-suite, including the fixtures and dsdk's self-check of the reuse rule.

**Files to edit.** `src/dsdk/graph/bridges.py` only (`import_graph` plus private helpers). Do NOT edit any file under `tests/`, `fixtures/`, `tracks.toml`, `tracks/`, or functions owned by other tasks. Read the whole module docstring and every stub docstring first: they are the spec, including exact strings and tie-breaks. Read the tests named in the done command before coding.

**Done when.** `cd /home/user/dsdk && uv run pytest tests/graph tests/test_reuse.py tests/core tests/logic -q` passes (all 273 graph tests plus the existing ones). (exit 0). Also `cd /home/user/dsdk && uv run pytest tests/core tests/logic tests/test_reuse.py -q` must stay green (it passes today).

**Depends on.** T20, T21, T22, T23, T24, T25

**Pitfalls.**
- Read the `import_graph` docstring twice: the resolution rules (absolute, `from top import B`, relative levels) are the spec.
- Nodes: `sorted(p.name for p in root.iterdir() if p.is_dir() and (p / "__init__.py").exists())`, rendered `f"{top}.{name}"` where `top = Path(package_root).name`. `Path(package_root)` accepts a `str`. Raise `FileNotFoundError` for a directory that does not exist (`Path.is_dir()` is false). `__pycache__` has no `__init__.py` so it is naturally excluded.
- For every `*.py` file under `root / sub` (`rglob`), parse with `ast.parse(path.read_text())` (a `SyntaxError` must propagate) and examine `ast.walk(tree)` so nested/`TYPE_CHECKING` imports count while comments and string literals cannot.
- File package path: `pkg = [top, *path.parent.relative_to(root).parts]` (for `dsdk/a/deep/mod.py` that is `['dsdk', 'a', 'deep']`). `ast.Import`: for each alias split `alias.name` on `.`; when the first part equals `top` and there are at least 2 parts, the target is part `[1]`. `ast.ImportFrom` with `level == 0`: `full = module.split('.')`. With `level >= 1`: `drop = level - 1`; ignore the statement when `drop >= len(pkg)`; `full = pkg[:len(pkg) - drop] + (module.split('.') if module else [])`. Then, when `full[0] == top`: `len(full) >= 2` -> target `full[1]`; `full == [top]` -> every imported alias name is a candidate target (`from dsdk import core, logic`; `from .. import core`).
- Add an edge only when the target is one of the discovered subpackage names AND differs from the importing subpackage. Level 1 imports in `dsdk/a/x.py` resolve to `['dsdk','a', ...]`: same package, no edge (this falls out of the rule above; do not special-case it). Collect edges in a `set`, then `Graph.from_edges(sorted(edges), nodes, directed=True, closed_world=True)` with `nodes=` always passed so packages without imports still appear.
- `tests/graph/test_graph_self_reuse.py` builds the REAL graph of `src/dsdk`. It needs `dsdk.graph` itself to import `dsdk.core` and `dsdk.logic`, which `bridges.py` already does; do not remove those imports.
- The final command also runs the fixture tests (`test_graph_fixtures.py`): they exercise T20-T24 together. Run `uv run pytest tests/graph -q` once at the end and read the first failure's message before changing anything.

**Rules.** Use ONLY file reading/editing and Bash for pytest. Never create sessions, triggers, agents or remote resources. Do not run git commands that change state. Remove `raise NotImplementedError` only in the functions this task owns. Keep docstrings and the existing imports. Standard library only. Public API of `dsdk.core` / `dsdk.logic` only. 2 attempts total.
