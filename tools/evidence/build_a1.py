"""Build tracks/A1/evidence/packet.json by RUNNING dsdk.logic (fixtures are only the independent oracle).

Run: uv run python tools/evidence/build_a1.py
"""
from __future__ import annotations

import itertools
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
from common import REPO  # noqa: E402

from dsdk.logic import (And, Const, Formula, Iff, Implies, Leaf, Node, Not, Or, Proof, Rule, Step,  # noqa: E402
                        Var, check, countermodel, entails, evaluate, evaluate_partial, is_satisfiable,
                        is_valid, mirror, models, size, to_str, tree_height, tree_size, triangular,
                        truth_table, variables)
from dsdk.logic.semantics import UnassignedVariableError  # noqa: E402

TRACK = "A1"
OUT = REPO / "tracks" / "A1" / "evidence" / "packet.json"
FIXTURES = ["fixtures/logic/formulas.json", "fixtures/logic/wumpus_kb.json"]
CODE = ["src/dsdk/logic/formula.py", "src/dsdk/logic/semantics.py", "src/dsdk/logic/proof.py",
        "src/dsdk/logic/structures.py", "src/dsdk/core/status.py", "viewer/parity/logic.mjs"]

_BIN = {"and": And, "or": Or, "implies": Implies, "iff": Iff}
_OPNAME = {And: "and", Or: "or", Implies: "implies", Iff: "iff"}


def from_struct(d: dict) -> Formula:
    op = d["op"]
    if op == "const":
        return Const(d["value"])
    if op == "var":
        return Var(d["name"])
    if op == "not":
        return Not(from_struct(d["operand"]))
    return _BIN[op](from_struct(d["left"]), from_struct(d["right"]))


def to_struct(f: Formula) -> dict:
    if isinstance(f, Const):
        return {"op": "const", "value": f.value}
    if isinstance(f, Var):
        return {"op": "var", "name": f.name}
    if isinstance(f, Not):
        return {"op": "not", "operand": to_struct(f.operand)}
    return {"op": _OPNAME[type(f)], "left": to_struct(f.left), "right": to_struct(f.right)}


def fmt(f: Formula) -> dict:
    return {"string": to_str(f), "structure": to_struct(f)}


def rows(f: Formula) -> list[dict]:
    return [{"assignment": a, "value": v} for a, v in truth_table(f)]


def load(rel: str) -> dict:
    return json.loads((REPO / rel).read_text())


def hashed(rels: list[str]) -> list[dict]:
    return [{"path": r, "sha256": common.sha256_file(REPO / r)} for r in rels]


# ------------------------------------------------------------------ panels

def panel_truth_tables(fx: dict) -> tuple[list[dict], dict]:
    out, mism = [], {"rows": 0, "cases": 0, "compared_rows": 0}
    for case in fx["cases"]:
        f = from_struct(case["structure"])
        t = rows(f)
        entry = {"name": case["name"], **fmt(f), "variables": sorted(variables(f)), "size": size(f),
                 "rows": t, "model_count": sum(1 for _ in models(f)), "satisfiable": is_satisfiable(f),
                 "valid": is_valid(f)}
        out.append(entry)
        mism["cases"] += 1
        mism["compared_rows"] += len(t)
        ok = (entry["string"] == case["string"] and entry["variables"] == case["variables"]
              and entry["size"] == case["size"] and t == case["truth_table"]
              and entry["model_count"] == case["model_count"] and entry["satisfiable"] == case["satisfiable"]
              and entry["valid"] == case["valid"])
        mism["rows"] += 0 if ok else 1
    return out, mism


def panel_wumpus(kb: dict) -> tuple[dict, dict]:
    prem = [from_struct(p["structure"]) for p in kb["premises"]]
    conj = prem[0]
    for p in prem[1:]:
        conj = And(conj, p)
    allv = kb["variables"]
    ms = list(models(conj, allv))
    cells = []
    for c in ["P11", "P12", "P21", "P22", "P31"]:
        v = Var(c)
        pit, safe = entails(prem, v), entails(prem, Not(v))
        status = "entailed_pit" if pit else "entailed_safe" if safe else "undetermined"
        cells.append({"cell": c, "x": int(c[1]), "y": int(c[2]), "entails_pit": pit, "entails_safe": safe,
                      "status": status, "countermodel_for_pit": countermodel(prem, v),
                      "countermodel_for_safe": countermodel(prem, Not(v))})
    queries = []
    for q in kb["queries"]:
        f = from_struct(q["structure"])
        queries.append({"name": q["name"], **fmt(f), "entails": entails(prem, f), "countermodel": countermodel(prem, f)})
    mism = sum(1 for q, fq in zip(queries, kb["queries"])
               if q["entails"] != fq["entails"] or q["countermodel"] != fq["first_countermodel"])
    mism += 0 if ms == kb["models"] else 1
    mism += 0 if len(ms) == kb["model_count"] else 1
    panel = {"variables": allv, "premises": [{"name": p["name"], **fmt(from_struct(p["structure"]))} for p in kb["premises"]],
             "models": ms, "model_count": len(ms), "cells": cells, "queries": queries,
             "grid_note": "Cell Pxy: x = column, y = row; (1,1) is the bottom-left start cell. P31 lies outside the 2x2 grid."}
    return panel, {"compared": len(queries) + 2, "mismatches": mism}


def panel_countermodels() -> list[dict]:
    p, q, r = Var("p"), Var("q"), Var("r")
    cases = [
        ("affirming_consequent", "From (p -> q) and q, conclude p. Invalid: p=false, q=true is a countermodel.", [Implies(p, q), q], p),
        ("denying_antecedent", "From (p -> q) and ~p, conclude ~q. Invalid.", [Implies(p, q), Not(p)], Not(q)),
        ("modus_ponens_valid", "From (p -> q) and p, conclude q. Valid: no countermodel.", [Implies(p, q), p], q),
        ("hypothetical_syllogism_valid", "From (p -> q) and (q -> r), conclude (p -> r). Valid.", [Implies(p, q), Implies(q, r)], Implies(p, r)),
    ]
    out = []
    for name, desc, prem, concl in cases:
        cm = countermodel(prem, concl)
        entry = {"name": name, "description": desc, "premises": [fmt(x) for x in prem], "conclusion": fmt(concl),
                 "entails": entails(prem, concl), "countermodel": cm}
        if cm is not None:
            entry["premises_true_under_countermodel"] = [evaluate(x, cm) for x in prem]
            entry["conclusion_true_under_countermodel"] = evaluate(concl, cm)
        out.append(entry)
    return out


def _proof(specs):
    return [Step(f, Rule(rule), tuple(c)) for f, rule, c in specs]


def panel_proofs() -> list[dict]:
    p, q, r = Var("p"), Var("q"), Var("r")
    P = lambda f: (f, "premise", ())
    defs = [
        ("valid_modus_ponens", "p->q, p |- q by modus ponens.", [Implies(p, q), p],
         [P(Implies(p, q)), P(p), (q, "modus_ponens", (0, 1))], True),
        ("valid_and_elim_then_mp", "(p & q), (p -> r) |- r.", [And(p, q), Implies(p, r)],
         [P(And(p, q)), P(Implies(p, r)), (p, "and_elim_left", (0,)), (r, "modus_ponens", (1, 2))], True),
        ("invalid_affirming_consequent", "p->q, q |- p claimed by modus ponens. The checker must reject it.", [Implies(p, q), q],
         [P(Implies(p, q)), P(q), (p, "modus_ponens", (0, 1))], False),
        ("invalid_denying_antecedent", "p->q, ~p |- ~q claimed by modus tollens. Must be rejected.", [Implies(p, q), Not(p)],
         [P(Implies(p, q)), P(Not(p)), (Not(q), "modus_tollens", (0, 1))], False),
        ("invalid_forward_citation", "A step may not cite itself or a later step.", [p],
         [P(p), (p, "and_elim_left", (1,))], False),
    ]
    out = []
    for name, desc, prem, specs, expect in defs:
        proof: Proof = _proof(specs)
        res = check(proof, prem)
        out.append({"name": name, "description": desc, "premises": [fmt(x) for x in prem],
                    "steps": [{"formula": fmt(s.formula), "rule": s.rule.value, "cites": list(s.cites)} for s in proof],
                    "expect_ok": expect, "python": {"ok": res.ok, "bad_step": res.bad_step, "reason": res.reason}})
    return out


def panel_partial() -> list[dict]:
    x, y = Var("x"), Var("y")
    T, F = Const(True), Const(False)
    ex = [
        ("false_and_unknown", "False AND x is KNOWN false whatever x is.", And(F, x), {}),
        ("true_or_unknown", "True OR x is KNOWN true whatever x is.", Or(T, x), {}),
        ("excluded_middle_unknown", "x OR ~x is UNKNOWN when x is unassigned (Kleene does not see the two x are the same).", Or(x, Not(x)), {}),
        ("implies_self_unknown", "x -> x is UNKNOWN when x is unassigned.", Implies(x, x), {}),
        ("iff_self_unknown", "x <-> x is UNKNOWN when x is unassigned.", Iff(x, x), {}),
        ("and_two_unknown", "x AND y with both unassigned: reason lists both.", And(x, y), {}),
        ("false_implies_unknown", "False -> y is KNOWN true.", Implies(F, y), {}),
        ("unknown_implies_true", "x -> True is KNOWN true.", Implies(x, T), {}),
        ("true_implies_unknown", "True -> y is UNKNOWN.", Implies(T, y), {}),
        ("not_unknown", "~x is UNKNOWN.", Not(x), {}),
        ("partial_and_decided", "x AND y with x=false: KNOWN false although y is unassigned.", And(x, y), {"x": False}),
        ("fully_assigned", "A full assignment agrees with two-valued evaluate.", Iff(x, y), {"x": True, "y": False}),
        ("const_only", "A constant-only compound is always KNOWN.", And(T, Not(F)), {}),
    ]
    out = []
    for name, desc, f, a in ex:
        j = evaluate_partial(f, a)
        out.append({"name": name, "description": desc, **fmt(f), "assignment": a,
                    "python": {"status": j.status.value, "value": j.value, "reason": j.reason}})
    return out


def _all_trees(n_leaves: int):
    if n_leaves == 1:
        yield Leaf(0)
        return
    for k in range(1, n_leaves):
        for l in _all_trees(k):
            for r in _all_trees(n_leaves - k):
                yield Node(l, r)


def _tree_struct(t) -> dict:
    return {"leaf": True} if isinstance(t, Leaf) else {"left": _tree_struct(t.left), "right": _tree_struct(t.right)}


def panel_induction() -> dict:
    tri = [{"n": n, "iteration": triangular(n), "closed_form": n * (n + 1) // 2} for n in range(0, 201)]
    tri_fail = [r["n"] for r in tri if r["iteration"] != r["closed_form"]]
    trees = [t for k in range(1, 8) for t in _all_trees(k)]
    mir_fail = [i for i, t in enumerate(trees) if mirror(mirror(t)) != t]
    small = [t for k in range(1, 4) for t in _all_trees(k)]
    return {
        "disclaimer": ("These are EXECUTED CHECKS on finitely many inputs. They do not prove the claims for all n or all "
                       "trees. The proofs are in tracks/A1/PROOFS.md (Proof 1 by induction on n; Proof 2 by structural induction)."),
        "triangular": {"claim": "triangular(n) = n(n+1)/2 for all n >= 0", "proof_ref": "tracks/A1/PROOFS.md Proof 1",
                       "checked_range": [0, 200], "checked": len(tri), "failures": tri_fail,
                       "samples": [r for r in tri if r["n"] in (0, 1, 2, 3, 5, 10, 50, 100, 200)]},
        "mirror": {"claim": "mirror(mirror(t)) = t for every binary tree t", "proof_ref": "tracks/A1/PROOFS.md Proof 2",
                   "checked_scope": "every binary tree shape with 1 to 7 leaves (exhaustive: Catalan counts 1,1,2,5,14,42,132)",
                   "checked": len(trees), "failures": mir_fail,
                   "sample_trees": [{"tree": _tree_struct(t), "size": tree_size(t), "height": tree_height(t),
                                     "mirror_of_mirror_equals_original": mirror(mirror(t)) == t} for t in small]},
    }


# ------------------------------------------------------------------ oracle pieces

def mutant_check(fx: dict) -> dict:
    """Mutation test: an evaluator that wrongly treats '->' as '<->' must be CAUGHT by the fixture oracle."""
    def ev(s, a):
        op = s["op"]
        if op == "const": return s["value"]
        if op == "var": return a[s["name"]]
        if op == "not": return not ev(s["operand"], a)
        l, r = ev(s["left"], a), ev(s["right"], a)
        return {"and": l and r, "or": l or r, "implies": l == r, "iff": l == r}[op]  # BUG: implies as iff
    case = next(c for c in fx["cases"] if c["name"] == "implies_ab")
    names = case["variables"]
    bad = []
    for assignment, expected in ((r["assignment"], r["value"]) for r in case["truth_table"]):
        if ev(case["structure"], assignment) != expected:
            bad.append(assignment)
    return {"name": "mutant_implies_as_iff", "expected_to_fail": True, "failure_observed": bool(bad),
            "description": "A mutant evaluator that computes (a -> b) as (a <-> b) is run against the independent fixture truth table for implies_ab.",
            "detail": f"mutant disagrees with the oracle on {len(bad)} of {len(case['truth_table'])} rows: {bad}"}


def boundary_cases() -> list[dict]:
    def chk(name, desc, expected, observed):
        return {"name": name, "description": desc, "expected": expected, "observed": observed, "pass": expected == observed}
    x, p = Var("x"), Var("p")
    out = []
    out.append(chk("zero_variables_one_row", "A constant-only formula has exactly one (empty) assignment.", 1, len(truth_table(Const(True)))))
    out.append(chk("contradiction_zero_models", "p & ~p has no models.", 0, len(list(models(And(p, Not(p)))))))
    out.append(chk("tautology_all_models", "p | ~p has 2 of 2 models and is valid.", [2, True], [len(list(models(Or(p, Not(p))))), is_valid(Or(p, Not(p)))]))
    out.append(chk("empty_premises_is_validity", "Entailment from no premises equals validity.", [True, False], [entails([], Or(p, Not(p))), entails([], p)]))
    out.append(chk("contradictory_premises_entail_all", "Contradictory premises entail everything (vacuous).", True, entails([p, Not(p)], Var("anything"))))
    try:
        evaluate(And(Const(False), x), {})
        got = "no error"
    except UnassignedVariableError as e:
        got = f"UnassignedVariableError({e.name})"
    out.append(chk("evaluate_no_short_circuit_exemption", "Two-valued evaluate raises on an unassigned variable even when And(false, x) could short-circuit.", "UnassignedVariableError(x)", got))
    j = evaluate_partial(And(Const(False), x), {})
    out.append(chk("partial_eval_decides_without_x", "evaluate_partial decides And(false, x) as KNOWN false.", ["known", False], [j.status.value, j.value]))
    out.append(chk("triangular_zero", "triangular(0) is the empty sum 0.", 0, triangular(0)))
    out.append(chk("mirror_leaf_fixed", "mirror of a leaf is the leaf.", True, mirror(Leaf(1)) == Leaf(1)))
    out.append(chk("tree_height_leaf_zero", "A single leaf has height 0 and size 1.", [0, 1], [tree_height(Leaf(1)), tree_size(Leaf(1))]))
    return out


def analytic_checks() -> list[dict]:
    """Closed-form counts that need no reference implementation: n variables -> 2^n rows; known model counts."""
    a, b, c = Var("a"), Var("b"), Var("c")
    out = []
    for n in range(0, 6):
        f = Const(True)
        for i in range(n):
            f = And(f, Or(Var(f"v{i}"), Not(Var(f"v{i}"))))
        out.append({"name": f"rows_{n}_vars", "description": f"A formula over {n} variables has 2^{n} truth-table rows.",
                    "expected": 2 ** n, "observed": len(truth_table(f)), "pass": 2 ** n == len(truth_table(f))})
    exp = {"and_ab_models": 1, "or_ab_models": 3, "xor_like_models": 2}
    got = {"and_ab_models": len(list(models(And(a, b)))), "or_ab_models": len(list(models(Or(a, b)))),
           "xor_like_models": len(list(models(And(Or(a, b), Not(And(a, b))))))}
    out.append({"name": "known_model_counts", "description": "Hand-derived counts: a&b has 1 model, a|b has 3, exactly-one-of(a,b) has 2.",
                "expected": exp, "observed": got, "pass": exp == got})
    d = Or(a, Or(b, c))
    out.append({"name": "or_three_vars_models", "description": "a|b|c has 2^3 - 1 = 7 models.", "expected": 7,
                "observed": len(list(models(d))), "pass": len(list(models(d))) == 7})
    return out


# ------------------------------------------------------------------ main

def main() -> int:
    formulas, kb = load(FIXTURES[0]), load(FIXTURES[1])
    tables, tt_cmp = panel_truth_tables(formulas)
    wumpus, w_cmp = panel_wumpus(kb)
    counter = panel_countermodels()
    proofs = panel_proofs()
    partial = panel_partial()
    induction = panel_induction()
    panels = {"truth_tables": tables, "wumpus": wumpus, "countermodels": counter, "proofs": proofs,
              "partial_eval": partial, "induction": induction}

    deliberate = [mutant_check(formulas)]
    ac = next(c for c in counter if c["name"] == "affirming_consequent")
    ac_proof = next(c for c in proofs if c["name"] == "invalid_affirming_consequent")
    deliberate.append({"name": "affirming_consequent", "expected_to_fail": True,
                       "failure_observed": (not ac["entails"]) and (not ac_proof["python"]["ok"]),
                       "description": "The invalid inference (p -> q), q |- p. Semantically it has a countermodel; syntactically the proof checker must reject the modus_ponens step.",
                       "detail": f"countermodel={ac['countermodel']}; checker: {ac_proof['python']['reason']}"})

    tests = [common.run_pytest("tests/logic"), common.run_pytest("tests/core")]
    git = common.git_facts()
    rec = {**git, "environment": common.environment(), "data": hashed(FIXTURES),
           "parameters": {"enumeration_order": "variables sorted ascending, false before true, first variable slowest",
                          "induction_triangular_range": [0, 200], "induction_mirror_max_leaves": 7,
                          "pytest_target_list": ["tests/logic", "tests/core"]},
           "random_seeds": [], "random_draws": "none: the build is deterministic (exhaustive enumeration, no sampling). pytest's hypothesis tests draw their own examples inside the pytest run.",
           "tests": tests,
           "outputs": [{"path": "tracks/A1/evidence/packet.json", "description": "this packet"}],
           "uncertainty": "No statistical uncertainty: every value is exact (finite enumeration). The residual uncertainty is correctness of the oracle and of the shared conventions, addressed by the mutation check, the independent JS recomputation in the viewer, and the tamper control in capture.mjs.",
           "timestamp": common.now_utc()}

    comps = [{"name": "formulas.json: strings, variables, size, truth tables, model counts, satisfiable, valid", "compared": tt_cmp["cases"], "mismatches": tt_cmp["rows"]},
             {"name": "wumpus_kb.json: model list/order, model_count, 11 entailment verdicts and first countermodels", "compared": w_cmp["compared"], "mismatches": w_cmp["mismatches"]}]

    packet = {
        "packet_version": "1", "track": TRACK, "title": "A1 logic evidence packet", "generated_at": rec["timestamp"],
        "question": {
            "text": "Do dsdk.logic's truth tables, model counts, entailment verdicts, strong-Kleene partial evaluation and proof checker give the right answers, as judged by an independently generated oracle and an independent JS reimplementation?",
            "competing_explanations": [
                {"name": "correct", "description": "dsdk.logic is correct on the exercised inputs.", "how_addressed": "Compared against the brute-force fixtures and recomputed in the browser by viewer/parity/logic.mjs."},
                {"name": "shared_convention_bug", "description": "Code and fixtures agree because both use the same wrong convention (e.g. enumeration order, implication).", "how_addressed": "Fixtures were generated by an independent script; analytic counts (2^n rows, hand-derived model counts) need no reference code."},
                {"name": "weak_oracle", "description": "The comparisons would pass even if the code were wrong.", "how_addressed": "Mutation check (implication as iff) must fail against the oracle; capture.mjs also tampers one value and requires the viewer to flag a disagree mark."},
                {"name": "js_echoes_python", "description": "The JS side agrees only because it copies Python's numbers.", "how_addressed": "The viewer recomputes from formula structures alone and never reads Python's answers when computing the JS column."}],
            "scope": {"claims": ["25 fixture formulas: truth tables, model counts, satisfiable/valid flags agree across Python, fixtures and JS.",
                                 "Wumpus 2x2-corner KB has exactly 3 models; P12 and P21 are entailed safe, P22 is undetermined.",
                                 "Affirming the consequent is semantically invalid (countermodel) and rejected by the proof checker.",
                                 "Strong-Kleene examples give the documented KNOWN/UNKNOWN verdicts in Python and JS."],
                      "does_not_claim": ["Correctness for all formulas (finite sample only; see induction disclaimer).",
                                         "Any claim about performance or large formulas.",
                                         "That the Wumpus KB models the real game; only that the stated KB has these models.",
                                         "The induction claims for all n: executed checks do not prove them. tracks/A1/PROOFS.md does."]}},
        "input_snapshot": {
            "source": "Repository fixtures fixtures/logic/formulas.json (25 formulas) and fixtures/logic/wumpus_kb.json (Russell & Norvig pit/breeze corner KB); formulas, KB and proof/partial/induction cases are authored inputs, not observed data.",
            "schema": "formulas.json: cases[{name,string,structure,variables,size,truth_table,model_count,satisfiable,valid}]. wumpus_kb.json: variables, premises[{name,string,structure}], models, queries[{name,string,structure,entails,first_countermodel}]. Structures use {op: const|var|not|and|or|implies|iff}.",
            "missingness_meaning": "There is no missing data. 'Unassigned' variables in partial-evaluation examples are UNKNOWN (strong Kleene: evidence insufficient), which dsdk.core keeps distinct from NOT_OBSERVED, INVALID and NOT_APPLICABLE; a countermodel of None means entailment holds, not that data is missing.",
            "files": hashed(FIXTURES)},
        "implementation": {
            "module": "dsdk.logic", "version": "0.0.1",
            "config": {"config_version": "a1-conventions-1", "enumeration_order": "sorted variable names, false before true, first variable slowest",
                       "partial_semantics": "strong Kleene (truth-functional)", "proof_rules": [r.value for r in Rule],
                       "canonical_string_grammar": formulas["grammar"]},
            "code_files": hashed(CODE),
            "fixtures": [{"path": FIXTURES[0], "sha256": common.sha256_file(REPO / FIXTURES[0]), "representative": [c["name"] for c in formulas["cases"]]},
                         {"path": FIXTURES[1], "sha256": common.sha256_file(REPO / FIXTURES[1]), "representative": [q["name"] for q in kb["queries"]]}]},
        "oracle": {
            "analytic": analytic_checks(),
            "independent_reference": {"description": "Fixtures were produced by a separate brute-force script (not dsdk); dsdk is run fresh and compared. The browser adds a second independent implementation (viewer/parity/logic.mjs, plus partial evaluation, countermodel and proof checking in viewer/a1.mjs).", "comparisons": comps},
            "boundary_cases": boundary_cases(), "deliberate_failures": deliberate},
        "run_record": rec,
        "browser_artifact": {
            "viewer": "viewer/index.html", "query": "?packet=../tracks/A1/evidence/packet.json", "recomputes_with": "viewer/parity/logic.mjs + viewer/a1.mjs",
            "views": ["Summary", "Truth table", "Countermodel", "Wumpus 2x2 corner", "Proof check", "Partial evaluation", "Induction checks"],
            "accessibility": ["semantic tables with captions and header cells", "view switcher and formula selector operable by keyboard (Tab, Enter/Space, arrow keys in select)",
                              "every result also stated in text; agree/disagree is a word, not only a colour", "download-values link (data: URL of the packet)"],
            "provenance_shown": ["git sha", "generated time", "python version", "packet path and hash-bearing file list"],
            "capture_record": "tracks/A1/evidence/capture.json"},
        "result": {
            "verdict": "supported",
            "statement": "Within the exercised inputs (25 formulas, the 7-variable Wumpus KB, 5 proof cases, 13 partial-evaluation cases) dsdk.logic agrees with the independent fixtures and the JS reimplementation; the Wumpus KB has 3 models, P12 and P21 are entailed safe, P22 is undetermined; the invalid inference is caught both semantically and by the proof checker. Universal claims rest on PROOFS.md, not on these checks.",
            "next_bounded_experiment": "Seeded differential fuzz: generate 1,000 random formulas (fixed seed, up to 5 variables) and compare Python and JS truth tables, model counts and partial evaluation; record the seed in the run record. After A2 lands, run the same fuzz through the parser's round trip."},
        "panels": panels,
    }

    errors = common.validate_packet(packet)
    failing = [c for sec in ("analytic", "boundary_cases") for c in packet["oracle"][sec] if not c["pass"]]
    problems = errors + [f"oracle check failed: {c['name']}" for c in failing]
    problems += [f"fixture mismatch: {c['name']}" for c in comps if c["mismatches"]]
    problems += [f"deliberate failure NOT observed: {d['name']}" for d in deliberate if not d["failure_observed"]]
    problems += [f"tests failing: {t['target']} {t['summary']}" for t in tests if t["exit_code"] != 0]
    problems += ["induction check failure"] if induction["triangular"]["failures"] or induction["mirror"]["failures"] else []
    if problems:
        print("BUILD FAILED:", *problems, sep="\n  ", file=sys.stderr)
        return 1
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(packet, indent=1) + "\n")
    print(f"wrote {OUT.relative_to(REPO)} ({OUT.stat().st_size} bytes); schema valid; "
          + "; ".join(f"{t['target']}: {t['summary']}" for t in tests))
    return 0


if __name__ == "__main__":
    sys.exit(main())
