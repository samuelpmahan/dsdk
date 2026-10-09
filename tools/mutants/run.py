"""Mutation testing for the code dsdk actually ships.

Plants small, realistic bugs into one package's real source, one at a time, and
runs that package's tests against each mutant in an isolated copy of the repo.
A mutant is KILLED when some test fails, which is evidence that the suite would
catch that bug. A mutant that SURVIVES is either equivalent (it changes nothing
observable) or a gap in the tests. Every survivor is listed with file:line so a
person can tell which.

    .venv/bin/python tools/mutants/run.py dsdk.lang tests/lang --max 120 --workers 4

Writes tracks/<track>/evidence/mutants.json and mutants.md (track looked up in tracks.toml).
"""
from __future__ import annotations

import argparse
import ast
import concurrent.futures as cf
import copy
import json
import os
import random
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
import tomllib
from dataclasses import asdict, dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PY = str(ROOT / ".venv/bin/python")

SWAP_BINOP = {ast.Add: ast.Sub, ast.Sub: ast.Add, ast.Mult: ast.Add, ast.FloorDiv: ast.Mult, ast.Mod: ast.FloorDiv}
SWAP_CMP = {ast.Lt: ast.LtE, ast.LtE: ast.Lt, ast.Gt: ast.GtE, ast.GtE: ast.Gt, ast.Eq: ast.NotEq,
            ast.NotEq: ast.Eq, ast.Is: ast.IsNot, ast.IsNot: ast.Is, ast.In: ast.NotIn, ast.NotIn: ast.In}


@dataclass
class Mutant:
    id: int
    file: str
    line: int
    kind: str
    before: str
    after: str
    status: str = "pending"
    killed_by: str = ""
    seconds: float = 0.0


class Sites(ast.NodeVisitor):
    """Enumerate mutation sites as (path-in-tree, kind) in deterministic order."""

    def __init__(self) -> None:
        self.sites: list[tuple[int, str]] = []
        self.counter = 0
        self.fn_depth = 0

    def generic_visit(self, node: ast.AST) -> None:
        self.counter += 1
        idx = self.counter
        if self.fn_depth:
            for kind in kinds_for(node):
                self.sites.append((idx, kind))
        is_fn = isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        if is_fn and ast.get_docstring(node) is not None and _is_stub(node):
            return
        self.fn_depth += is_fn
        super().generic_visit(node)
        self.fn_depth -= is_fn


def _is_stub(fn: ast.FunctionDef) -> bool:
    return any(isinstance(s, ast.Raise) and "NotImplementedError" in ast.unparse(s) for s in fn.body)


def kinds_for(node: ast.AST) -> list[str]:
    k = []
    if isinstance(node, ast.BinOp) and type(node.op) in SWAP_BINOP:
        k.append("binop")
    if isinstance(node, ast.Compare) and len(node.ops) == 1 and type(node.ops[0]) in SWAP_CMP:
        k.append("compare")
    if isinstance(node, ast.BoolOp):
        k.append("boolop")
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
        k.append("drop-not")
    if isinstance(node, ast.If):
        k.append("negate-if")
    if isinstance(node, ast.Constant) and type(node.value) is int and not isinstance(node.value, bool):
        k.append("int+1")
    if isinstance(node, ast.Constant) and isinstance(node.value, bool):
        k.append("flip-bool")
    if isinstance(node, (ast.Return,)) and node.value is not None and not (isinstance(node.value, ast.Constant) and node.value.value is None):
        k.append("return-none")
    return k


class Apply(ast.NodeTransformer):
    def __init__(self, target: int, kind: str) -> None:
        self.target, self.kind, self.counter = target, kind, 0
        self.before = self.after = ""
        self.line = 0

    def generic_visit(self, node: ast.AST) -> ast.AST:
        self.counter += 1
        if self.counter == self.target:
            self.line = getattr(node, "lineno", 0)
            self.before = ast.unparse(node).splitlines()[0][:120]
            node = self.mutate(node)
            self.after = ast.unparse(node).splitlines()[0][:120] if node is not None else "<removed>"
            return node
        return super().generic_visit(node)

    def mutate(self, n: ast.AST) -> ast.AST:
        n = copy.deepcopy(n)
        k = self.kind
        if k == "binop":
            n.op = SWAP_BINOP[type(n.op)]()
        elif k == "compare":
            n.ops = [SWAP_CMP[type(n.ops[0])]()]
        elif k == "boolop":
            n.op = ast.Or() if isinstance(n.op, ast.And) else ast.And()
        elif k == "drop-not":
            return n.operand
        elif k == "negate-if":
            n.test = ast.UnaryOp(op=ast.Not(), operand=n.test)
        elif k == "int+1":
            n.value = n.value + 1
        elif k == "flip-bool":
            n.value = not n.value
        elif k == "return-none":
            n.value = ast.Constant(value=None)
        return ast.fix_missing_locations(n)


def build_mutants(pkg_dir: Path, rel_root: Path, cap: int, seed: int) -> tuple[list[Mutant], dict[int, tuple[str, str]]]:
    all_sites: list[tuple[Path, int, str]] = []
    for path in sorted(pkg_dir.rglob("*.py")):
        tree = ast.parse(path.read_text())
        s = Sites()
        s.visit(tree)
        all_sites += [(path, idx, kind) for idx, kind in s.sites]
    rng = random.Random(seed)
    chosen = all_sites if len(all_sites) <= cap else sorted(rng.sample(all_sites, cap), key=lambda t: (str(t[0]), t[1]))
    mutants, sources = [], {}
    for i, (path, idx, kind) in enumerate(chosen):
        tree = ast.parse(path.read_text())
        ap = Apply(idx, kind)
        new = ap.visit(tree)
        try:
            src = ast.unparse(ast.fix_missing_locations(new))
        except Exception:
            continue
        rel = str(path.relative_to(rel_root))
        mutants.append(Mutant(i, rel, ap.line, kind, ap.before, ap.after))
        sources[i] = (rel, src)
    return mutants, sources, len(all_sites)


def run_one(m: Mutant, src: str, tests: str, timeout: int) -> Mutant:
    with tempfile.TemporaryDirectory(prefix="mut-") as tmp:
        t = Path(tmp)
        for d in ("src", "tests", "fixtures"):
            shutil.copytree(ROOT / d, t / d, ignore=shutil.ignore_patterns("__pycache__", ".hypothesis"))
        shutil.copy(ROOT / "tracks.toml", t / "tracks.toml")
        shutil.copy(ROOT / "pyproject.toml", t / "pyproject.toml")
        (t / "ops").mkdir()
        shutil.copy(ROOT / "ops/ledger.jsonl", t / "ops/ledger.jsonl")
        (t / m.file).write_text(src)
        start = time.time()
        try:
            r = subprocess.run([PY, "-m", "pytest", *shlex.split(tests), "-x", "-q", "-p", "no:cacheprovider", "-p", "no:randomly"],
                               cwd=t, env=dict(os.environ, PYTHONPATH=str(t / "src"), HYPOTHESIS_PROFILE=os.environ.get("HYPOTHESIS_PROFILE", "")),
                               capture_output=True, text=True, timeout=timeout)
            m.seconds = round(time.time() - start, 1)
            if r.returncode == 0:
                m.status = "survived"
            elif r.returncode in (2, 3, 4, 5):
                # interrupted / internal error / usage error / no tests collected: no test judged this mutant
                m.status, m.killed_by = "invalid", f"pytest exit {r.returncode}: not a test failure"
            else:
                m.status = "killed"
                hit = re.search(r"^(?:FAILED|ERROR) (\S+)", r.stdout, re.M)
                m.killed_by = hit.group(1) if hit else f"exit {r.returncode}"
        except subprocess.TimeoutExpired:
            m.seconds, m.status, m.killed_by = float(timeout), "killed", f"timeout >{timeout}s (hang)"
    return m


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("package"); ap.add_argument("tests")
    ap.add_argument("--max", type=int, default=120); ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--seed", type=int, default=20261009); ap.add_argument("--timeout", type=int, default=120)
    a = ap.parse_args()
    reg = tomllib.loads((ROOT / "tracks.toml").read_text())["packages"]
    track = reg[a.package]["track"]
    pkg_dir = ROOT / "src" / Path(*a.package.split("."))
    mutants, sources, n_sites = build_mutants(pkg_dir, ROOT, a.max, a.seed)
    sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    print(f"{a.package}: {n_sites} mutation sites, running {len(mutants)} mutants with {a.workers} workers", flush=True)
    base = run_one(Mutant(-1, mutants[0].file, 0, "baseline", "", ""), (ROOT / mutants[0].file).read_text(), a.tests, a.timeout)
    if base.status != "survived":
        sys.exit(f"baseline (no mutation) does not pass cleanly: {base.status} {base.killed_by}; refusing to score mutants")
    t0 = time.time()
    with cf.ThreadPoolExecutor(a.workers) as ex:
        futs = [ex.submit(run_one, m, sources[m.id][1], a.tests, a.timeout) for m in mutants]
        for f in cf.as_completed(futs):
            m = f.result()
            print(f"  #{m.id:3d} {m.status:8s} {m.file}:{m.line} {m.kind}", flush=True)
    mutants.sort(key=lambda m: m.id)
    killed = sum(m.status == "killed" for m in mutants)
    invalid = sum(m.status == "invalid" for m in mutants)
    if invalid:
        sys.exit(f"{invalid} mutants were not judged by any test (pytest usage/collection error); not writing evidence")
    out = ROOT / "tracks" / track / "evidence"
    out.mkdir(parents=True, exist_ok=True)
    summary = {"package": a.package, "track": track, "tests": a.tests, "git_sha": sha, "seed": a.seed,
               "sites_total": n_sites, "mutants_run": len(mutants), "killed": killed,
               "survived": len(mutants) - killed, "minutes": round((time.time() - t0) / 60, 1),
               "command": f".venv/bin/python tools/mutants/run.py {a.package} {shlex.quote(a.tests)} --max {a.max} --seed {a.seed}",
               "mutants": [asdict(m) for m in mutants]}
    (out / "mutants.json").write_text(json.dumps(summary, indent=1))
    lines = [f"# Mutation evidence: {a.package} ({track})", "",
             f"Commit `{sha[:12]}`. {n_sites} mutation sites in the shipped source; {len(mutants)} sampled with seed {a.seed}.",
             f"**{killed} killed, {len(mutants) - killed} survived** ({100 * killed / max(1, len(mutants)):.0f}% kill rate).",
             "", f"Reproduce: `{summary['command']}`", "",
             "A survivor is either equivalent (no observable change) or a test gap. Each one is listed for triage.", "",
             "## Survivors", "", "| # | Where | Kind | Original | Mutant |", "|---|---|---|---|---|"]
    for m in mutants:
        if m.status == "survived":
            lines.append(f"| {m.id} | `{m.file}:{m.line}` | {m.kind} | `{m.before}` | `{m.after}` |")
    lines += ["", "## Killed (first failing test)", "", "| # | Where | Kind | Killed by |", "|---|---|---|---|"]
    for m in mutants:
        if m.status == "killed":
            lines.append(f"| {m.id} | `{m.file}:{m.line}` | {m.kind} | `{m.killed_by}` |")
    (out / "mutants.md").write_text("\n".join(lines) + "\n")
    print(f"done: {killed}/{len(mutants)} killed -> {out/'mutants.md'}")


if __name__ == "__main__":
    main()
