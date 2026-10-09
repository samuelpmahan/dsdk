"""Build the claims ledger: every test as a plain-language claim with its location,
what it exercises, and whether it passed; plus the planted-bug (mutation) results
translated into words. Output feeds the Lab (lab/dist), not a file to go read.

    .venv/bin/python tools/evidence/claims.py      # writes lab/data/claims.json
"""
from __future__ import annotations

import ast
import json
import re
import subprocess
import tempfile
import tomllib
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GH = "https://github.com/samuelpmahan/dsdk/blob/claude/friendly-cray-zex2o8/"
SECTION = re.compile(r"^\s*#\s*[=\-#]{3,}\s*(.+?)\s*[=\-#]*\s*$")
TRACK_TESTS = {"dsdk.core": "tests/core", "dsdk.logic": "tests/logic", "dsdk.lang": "tests/lang", "dsdk.graph": "tests/graph"}
PLAIN = {
    "dsdk.core": "the kernel: status values, write-once Parts, recorded calculations and all-or-nothing ticks",
    "dsdk.logic": "propositional logic: formulas, evaluation with unknowns, model enumeration, entailment, a proof checker, induction exercises",
    "dsdk.lang": "the Calc language: a table-driven lexer, two formula parsers, a type checker, step-by-step and direct evaluators, and the bridge back to logic and the kernel",
    "dsdk.graph": "graphs: BFS with witness paths, cycles, topological order, components, evidence-aware reachability, and graphs built from lineage, formulas and dsdk's own imports",
}


def public_api() -> dict[str, dict[str, tuple[str, int]]]:
    """name -> (file, line) for every top-level def/class in each package."""
    api: dict[str, dict[str, tuple[str, int]]] = {}
    for pkg in TRACK_TESTS:
        d = ROOT / "src" / Path(*pkg.split("."))
        names: dict[str, tuple[str, int]] = {}
        for f in sorted(d.rglob("*.py")):
            for n in ast.parse(f.read_text()).body:
                if isinstance(n, (ast.FunctionDef, ast.ClassDef)) and not n.name.startswith("_"):
                    names.setdefault(n.name, (str(f.relative_to(ROOT)), n.lineno))
        api[pkg] = names
    return api


def enclosing(file: str, line: int) -> str:
    tree = ast.parse((ROOT / file).read_text())
    best = ""
    for n in ast.walk(tree):
        if isinstance(n, (ast.FunctionDef, ast.ClassDef)) and n.lineno <= line <= (n.end_lineno or n.lineno):
            if not best or n.lineno >= best[1]:
                best = (n.name, n.lineno)
    return best[0] if best else "module level"


def run_junit(tests: str) -> dict[str, str]:
    with tempfile.NamedTemporaryFile(suffix=".xml") as tmp:
        subprocess.run([str(ROOT / ".venv/bin/python"), "-m", "pytest", tests, "-q", "-p", "no:cacheprovider",
                        f"--junitxml={tmp.name}"], cwd=ROOT, capture_output=True, text=True)
        tree = ET.parse(tmp.name)
    out: dict[str, str] = {}
    for tc in tree.iter("testcase"):
        func = re.sub(r"\[.*$", "", tc.get("name", ""))
        file = tc.get("classname", "").replace(".", "/")
        k = f"{file}::{func}"
        bad = tc.find("failure") is not None or tc.find("error") is not None
        prev = out.get(k, "pass")
        out[k] = "fail" if bad or prev == "fail" else "pass"
    return out


def plain_kind(kind: str, before: str, after: str) -> str:
    return {
        "compare": "flipped a comparison", "binop": "swapped an arithmetic operator", "boolop": "swapped and/or",
        "drop-not": "dropped a 'not'", "negate-if": "inverted an if-condition", "int+1": "changed a constant by one",
        "flip-bool": "flipped True/False", "return-none": "made a function return nothing",
    }.get(kind, kind)


def main() -> None:
    api = public_api()
    reg = tomllib.loads((ROOT / "tracks.toml").read_text())["packages"]
    tracks = []
    claim_by_node: dict[str, str] = {}
    for pkg, tdir in TRACK_TESTS.items():
        results = run_junit(tdir)
        modules = []
        for f in sorted((ROOT / tdir).glob("test_*.py")):
            src = f.read_text()
            lines = src.splitlines()
            tree = ast.parse(src)
            section = "General"
            sections: dict[str, list] = {}
            last = 0
            for n in tree.body:
                if not (isinstance(n, ast.FunctionDef) and n.name.startswith("test_")):
                    continue
                for i in range(last, n.lineno - 1):
                    m = SECTION.match(lines[i])
                    if m:
                        section = m.group(1).strip(" =-#")
                last = n.lineno
                doc = (ast.get_docstring(n) or n.name.replace("_", " ")).strip().splitlines()[0]
                used = sorted({x.id for x in ast.walk(n) if isinstance(x, ast.Name)} & set(api[pkg]))
                rel = str(f.relative_to(ROOT))
                node = f"{rel.removesuffix('.py').replace('/', '/')}::{n.name}"
                status = results.get(f"{rel.removesuffix('.py')}::{n.name}", "not run")
                params = sum(1 for k in results if k == f"{rel.removesuffix('.py')}::{n.name}")
                claim_by_node[f"{rel}::{n.name}"] = doc
                sections.setdefault(section, []).append({
                    "claim": doc, "test": n.name, "where": f"{rel}:{n.lineno}", "link": f"{GH}{rel}#L{n.lineno}",
                    "exercises": [{"name": u, "where": f"{api[pkg][u][0]}:{api[pkg][u][1]}",
                                   "link": f"{GH}{api[pkg][u][0]}#L{api[pkg][u][1]}"} for u in used],
                    "status": status,
                })
            modules.append({"file": str(f.relative_to(ROOT)), "sections": [{"name": k, "claims": v} for k, v in sections.items()]})
        track = reg[pkg]["track"]
        mut_path = ROOT / "tracks" / track / "evidence" / "mutants.json"
        mutation = None
        if mut_path.exists():
            mj = json.loads(mut_path.read_text())
            planted = []
            for m in mj["mutants"]:
                killer = m["killed_by"]
                killer_claim = claim_by_node.get(re.sub(r"\[.*$", "", killer), "")
                planted.append({
                    "what": f"{plain_kind(m['kind'], m['before'], m['after'])} in {enclosing(m['file'], m['line'])}",
                    "before": m["before"], "after": m["after"], "where": f"{m['file']}:{m['line']}",
                    "link": f"{GH}{m['file']}#L{m['line']}", "status": m["status"],
                    "caught_by": killer_claim or (killer if "timeout" in killer else killer.split("::")[-1].replace("_", " ")),
                })
            mutation = {"sites": mj["sites_total"], "run": mj["mutants_run"], "killed": mj["killed"],
                        "survived": mj["survived"], "git_sha": mj["git_sha"], "command": mj["command"], "planted": planted}
        n_claims = sum(len(s["claims"]) for m in modules for s in m["sections"])
        n_pass = sum(c["status"] == "pass" for m in modules for s in m["sections"] for c in s["claims"])
        tracks.append({"package": pkg, "track": track, "about": PLAIN[pkg], "claims": n_claims, "passing": n_pass,
                       "modules": modules, "mutation": mutation})
    out = ROOT / "lab/data/claims.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"tracks": tracks}, separators=(",", ":")))
    for t in tracks:
        mu = t["mutation"]
        print(f"{t['package']}: {t['passing']}/{t['claims']} claims passing"
              + (f"; planted bugs {mu['killed']}/{mu['run']} caught" if mu else "; no mutation run yet"))


if __name__ == "__main__":
    main()
