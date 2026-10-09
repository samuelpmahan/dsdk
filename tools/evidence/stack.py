"""Measure how dsdk actually stacks: which earlier functions each package CALLS
(not merely imports), and which packages nothing later calls. Imports were gameable;
calls are not, short of writing pointless calls, which review catches.

    .venv/bin/python tools/evidence/stack.py      # prints the stack; also used by tests/test_stack.py
"""
from __future__ import annotations

import ast
import collections
import json
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def registry() -> dict:
    return tomllib.loads((ROOT / "tracks.toml").read_text())["packages"]


def calls() -> dict[str, dict[str, set[str]]]:
    """package -> earlier package -> names of its functions/classes called."""
    reg = registry()
    out: dict[str, dict[str, set[str]]] = {p: collections.defaultdict(set) for p in reg}
    for p in reg:
        for f in (ROOT / "src" / Path(*p.split("."))).rglob("*.py"):
            tree = ast.parse(f.read_text())
            alias: dict[str, str] = {}
            for n in ast.walk(tree):
                if isinstance(n, ast.ImportFrom) and n.level == 0 and n.module and n.module.startswith("dsdk."):
                    src = ".".join(n.module.split(".")[:2])
                    if src != p:
                        for a in n.names:
                            alias[a.asname or a.name] = src
                elif isinstance(n, ast.Import):
                    for a in n.names:
                        src = ".".join(a.name.split(".")[:2])
                        if a.name.startswith("dsdk.") and src != p:
                            alias[(a.asname or a.name).split(".")[-1]] = src
            # Objects whose type comes from an earlier package: parameters annotated with an imported class,
            # and `with <such object>.<method>(...) as name` targets. Method calls on them count as uses of that
            # package, named Class.method. Nothing is guessed from method names alone.
            typed: dict[str, tuple[str, str]] = {}
            for fn in ast.walk(tree):
                if isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    for a in fn.args.args + fn.args.kwonlyargs:
                        ann = a.annotation
                        name = ann.id if isinstance(ann, ast.Name) else (ann.value if isinstance(ann, ast.Constant) and isinstance(ann.value, str) else None)
                        if name in alias:
                            typed[a.arg] = (alias[name], name)
            for w in ast.walk(tree):
                if isinstance(w, ast.With):
                    for item in w.items:
                        c = item.context_expr
                        if (isinstance(c, ast.Call) and isinstance(c.func, ast.Attribute) and isinstance(c.func.value, ast.Name)
                                and c.func.value.id in typed and isinstance(item.optional_vars, ast.Name)):
                            src, cls = typed[c.func.value.id]
                            typed[item.optional_vars.id] = (src, f"{cls}.{c.func.attr}()")
            for n in ast.walk(tree):
                if (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and isinstance(n.func.value, ast.Name)
                        and n.func.value.id in typed):
                    src, cls = typed[n.func.value.id]
                    out[p][src].add(f"{cls}.{n.func.attr}")
            for n in ast.walk(tree):
                if isinstance(n, ast.Call):
                    fn = n.func
                    if isinstance(fn, ast.Name) and fn.id in alias:
                        out[p][alias[fn.id]].add(fn.id)
                    elif isinstance(fn, ast.Attribute) and isinstance(fn.value, ast.Name) and fn.value.id in alias:
                        out[p][alias[fn.value.id]].add(fn.attr)
    return {p: {k: v for k, v in d.items()} for p, d in out.items()}


def summary() -> dict:
    reg = registry()
    c = calls()
    used_by: dict[str, set[str]] = {p: set() for p in reg}
    for p, deps in c.items():
        for d in deps:
            used_by[d].add(p)
    return {"packages": [{"package": p, "track": reg[p]["track"], "order": reg[p]["order"],
                          "calls": {d: sorted(n) for d, n in sorted(c[p].items(), key=lambda kv: reg[kv[0]]["order"])},
                          "used_by": sorted(used_by[p], key=lambda q: reg[q]["order"]),
                          "owed_to": reg[p].get("owed_to", ""), "thin_owed": reg[p].get("thin_owed", "")}
                         for p in sorted(reg, key=lambda q: reg[q]["order"])]}


if __name__ == "__main__":
    s = summary()
    for e in s["packages"]:
        print(f"{e['package']}: calls {sum(len(v) for v in e['calls'].values())} earlier functions "
              f"from {len(e['calls'])} packages; used by {e['used_by'] or 'nothing'}"
              + (f" (owed to {e['owed_to']})" if e["owed_to"] else ""))
    (ROOT / "lab/data").mkdir(parents=True, exist_ok=True)
    (ROOT / "lab/data/stack.json").write_text(json.dumps(s))
