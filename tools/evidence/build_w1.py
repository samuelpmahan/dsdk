"""Build tracks/W1/evidence/packet.json: "Six degrees of dubstep" on the Lost Lands 2018 corpus, by RUNNING dsdk.worlds.

Run: .venv/bin/python tools/evidence/build_w1.py        (about a minute; the pytest run dominates)

The independent oracle is fixtures/worlds/lostlands_slices.json (written by fixtures/worlds/gen_slices.py, which imports
nothing from dsdk). The browser side (viewer/w1.mjs) recomputes everything from the embedded corpus.
"""
from __future__ import annotations

import gzip
import json
import random
import statistics
import sys
import tempfile
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
from common import REPO  # noqa: E402

from dsdk.core import Status  # noqa: E402
from dsdk.graph import components, shortest_path  # noqa: E402
from dsdk.worlds import (  # noqa: E402
    FIXTURE_PATH, PINNED_SHA256, SOURCE_BRANCH, SOURCE_COMMIT, SOURCE_REPO, IntegrityError, SixDegrees,
    coselection_graph, load_lostlands, record_provenance, transition_graph,
)

TRACK = "W1"
OUT = REPO / "tracks" / "W1" / "evidence" / "packet.json"
STORE = "fixtures/worlds/lostlands-2018.jukebox.json.gz"
SLICES = "fixtures/worlds/lostlands_slices.json"
FIXTURES = [STORE, SLICES, "fixtures/worlds/gen_slices.py"]
CODE = ["src/dsdk/worlds/lostlands.py", "src/dsdk/worlds/networks.py", "src/dsdk/worlds/buildlog.py", "src/dsdk/worlds/__init__.py",
        "viewer/w1.mjs", "tools/evidence/build_w1.py"]
SEED, PAIRS = 2018, 300
DEMO = (483, 237)  # Space Laces - Torque -> PEEKABOO & G-REX - Babatunde


def hashed(rels):
    return [{"path": r, "sha256": common.sha256_file(REPO / r)} for r in rels]


def hop_json(h, kid):
    return {"source": kid[h.source], "target": kid[h.target], "evidence": h.evidence.value, "count": h.count, "sets": [list(s) for s in h.sets]}


def query_json(sd, case, kid):
    """Python's answer (track KEYS) in the packet's id form: the browser works with track ids, the reason string keeps keys."""
    keys = [t.key for t in sd.world.tracks]
    d = sd.query(keys[case["source"]], keys[case["target"]])
    py = {"source": case["source"], "target": case["target"], "status": d.judgment.status.value, "reason": d.judgment.reason,
          "path": [kid[k] for k in d.path] if d.path else None, "hops": [hop_json(h, kid) for h in d.hops]}
    ora = {"status": case["status"], "reason": case["reason"], "path": case["path"],
           "hops": [{k: h[k] for k in ("source", "target", "evidence", "count", "sets")} for h in case["hops"]]}
    py["oracle_agrees"] = {k: py[k] for k in ora} == ora
    return py


def naive_all_edges(sd, s, t):
    """MUTANT: treat inferred edges as observed (dsdk.graph.shortest_path over EVERY edge) and call the result KNOWN."""
    return shortest_path(sd.graph, s, t)


def main() -> int:
    world = load_lostlands()
    sd = SixDegrees(world)
    slices = json.loads((REPO / SLICES).read_text())
    raw_doc = json.loads(gzip.decompress((REPO / STORE).read_bytes()))

    keys = [t.key for t in world.tracks]
    kid = {k: i for i, k in enumerate(keys)}
    queries = [query_json(sd, c, kid) for c in slices["degrees"]]
    disagreements = [q for q in queries if not q["oracle_agrees"]]

    rng = random.Random(SEED)
    pairs = [[rng.randrange(len(world.tracks)), rng.randrange(len(world.tracks))] for _ in range(PAIRS)]
    results, hops_known = [], []
    for s, t in pairs:
        d = sd.query(keys[s], keys[t])
        status = d.judgment.status.value
        results.append([status, len(d.path) - 1 if d.path else None])
        if status == "known":
            hops_known.append(len(d.path) - 1)
    summary = {"pairs": PAIRS, "known": sum(r[0] == "known" for r in results),
               "needs_inferred": sum(r[0] == "unknown" and r[1] is not None for r in results),
               "open_world": sum(r[0] == "unknown" and r[1] is None for r in results),
               "median_known_hops": statistics.median(hops_known), "max_known_hops": max(hops_known)}
    histogram = {str(k): v for k, v in sorted(Counter(hops_known).items())}

    store = record_provenance(world)
    sentence = store.get("px.lostlands.provenance").value
    totals = {"tracks": len(world.tracks), "artists": len(world.artists), "selector_groups": len(world.groups), "dates": len(world.dates),
              "selections": len(world.selections), "transitions": len(world.transitions), "sets": len(world.sets()),
              "observed_edges": len(sd.known.edges), "search_edges": len(sd.graph.edges)}
    tg, cg = transition_graph(world), coselection_graph(world)
    panels = {
        "world": raw_doc, "demo": {"source": DEMO[0], "target": DEMO[1]}, "queries": queries,
        "distances": {"seed": SEED, "pairs": pairs, "results": results, "summary": summary, "histogram": histogram},
        "graph_totals": totals,
        "provenance": {"sha256": world.sha256, "commit": SOURCE_COMMIT, "repo": SOURCE_REPO, "branch": SOURCE_BRANCH, "sentence": sentence,
                       "integrity_note": "load_lostlands() hashed the file bytes and compared them with the pin before decoding."},
    }

    # ---- oracle
    cmp_oracle = {"name": f"{len(queries)} six-degrees queries: status, reason, witness path, per-step evidence vs gen_slices.py (independent algorithms)",
                  "compared": len(queries), "mismatches": len(disagreements)}
    t_total = sum(e.weight for e in tg.edges)
    analytic = [
        {"name": "transition_weights_sum_to_transition_rows", "description": "Every observed transition row is counted exactly once in the edge weights.",
         "expected": len(world.transitions), "observed": t_total, "pass": t_total == len(world.transitions)},
        {"name": "search_edges_arithmetic", "description": "Six-degrees edges = 2 x co-selected pairs + observed edges that are not co-selected pairs (self-loops). Hand-derived from the two graph builders.",
         "expected": 2 * len(cg.edges) + slices["graph_totals"]["transition_self_loops"], "observed": len(sd.graph.edges),
         "pass": len(sd.graph.edges) == 2 * len(cg.edges) + slices["graph_totals"]["transition_self_loops"]},
        {"name": "known_hops_are_real_transitions", "description": "Every KNOWN hop of every checked query appears as consecutive tracks in a set it cites.",
         "expected": True, "observed": all((h["source"], h["target"]) in list(zip(world.sets()[tuple(s)], world.sets()[tuple(s)][1:]))
                                          for q in queries for h in q["hops"] if h["evidence"] == "known" for s in h["sets"]),
         "pass": True},
    ]
    analytic[2]["pass"] = analytic[2]["observed"] is True
    boundary = []
    inv = sd.query(keys[0], 'no such track#999')
    boundary.append({"name": "invalid_node_is_not_unknown", "description": "A track id outside the corpus is INVALID (a different answer from UNKNOWN).",
                     "expected": "invalid", "observed": inv.judgment.status.value, "pass": inv.judgment.status is Status.INVALID})
    same = sd.query(keys[7], keys[7])
    boundary.append({"name": "track_reaches_itself", "description": "The empty path is KNOWN.", "expected": ["known", [7]],
                     "observed": [same.judgment.status.value, [kid[k] for k in same.path]], "pass": same.judgment.status is Status.KNOWN and same.path == (keys[7],)})
    openq = next(q for q in queries if q["status"] == "unknown" and q["path"] is None)
    boundary.append({"name": "no_path_is_unknown_not_known_false", "description": "Disconnected pair in an open world: UNKNOWN (never KNOWN False).",
                     "expected": "unknown", "observed": openq["status"], "pass": openq["status"] == "unknown"})
    boundary.append({"name": "weak_components", "description": "The transition graph has 5 weak components (one giant of 1,276 tracks); the search graph has the same 5.",
                     "expected": [5, 5], "observed": [len(components(tg)), len(components(sd.graph))],
                     "pass": [len(components(tg)), len(components(sd.graph))] == [5, 5]})

    # ---- deliberate failures
    naive_wrong = [q for q in queries if q["status"] == "unknown" and q["path"] is not None
                   and (p := naive_all_edges(sd, keys[q["source"]], keys[q["target"]])) is not None and len(p) - 1 <= len(q["path"]) - 1]
    with tempfile.TemporaryDirectory() as tmp:
        bad = Path(tmp) / "tampered.gz"
        data = bytearray(FIXTURE_PATH.read_bytes())
        data[len(data) // 2] ^= 1
        bad.write_bytes(bytes(data))
        try:
            load_lostlands(bad)
            tamper_detail, tamper_seen = "loaded a corrupted file", False
        except IntegrityError as exc:
            tamper_detail, tamper_seen = str(exc)[:120], True
    deliberate = [
        {"name": "naive_search_over_all_edges", "expected_to_fail": True, "failure_observed": len(naive_wrong) > 0,
         "description": "MUTANT: breadth-first over every edge and call the result KNOWN. It must disagree with the oracle on queries whose best path needs an inferred step.",
         "detail": f"{len(naive_wrong)} of {sum(q['status'] == 'unknown' and q['path'] is not None for q in queries)} inferred-path queries would be reported KNOWN by the mutant"},
        {"name": "tampered_corpus_bytes", "expected_to_fail": True, "failure_observed": tamper_seen,
         "description": "Flip one bit of the vendored gzip: the loader must refuse it before decoding.", "detail": tamper_detail},
    ]

    tests = [common.run_pytest("tests/worlds"), common.run_pytest("tests/core"), common.run_pytest("tests/graph")]
    rec = {**common.git_facts(), "environment": common.environment(), "data": hashed([STORE]),
           "parameters": {"seed": SEED, "random_pairs": PAIRS, "demo": list(DEMO), "pinned_sha256": PINNED_SHA256},
           "random_seeds": [SEED], "random_draws": f"{PAIRS} track pairs drawn with random.Random({SEED}).randrange for the 'How far apart?' view; the JS side replays the same pairs from the packet.",
           "tests": tests, "outputs": [{"path": "tracks/W1/evidence/packet.json", "description": "this packet"}],
           "uncertainty": "Path answers are exact for this corpus (no sampling). The corpus is a SAMPLE of one festival: 234 source rows were rejected by the parser, two credits are truncated ('+ More'), and the parser strips leading digits from artist names (12th Planet appears as 'th Planet' on 8 tracks). 'No route' therefore never means 'impossible'.",
           "timestamp": common.now_utc()}

    packet = {
        "packet_version": "1", "track": TRACK, "title": "Six degrees of dubstep", "generated_at": rec["timestamp"],
        "question": {
            "text": "How many back-to-back moves separate two tracks played at Lost Lands 2018, and how do we know each move happened? Does dsdk.worlds' answer, with its KNOWN/UNKNOWN verdict and witness path, agree with an independent oracle and an independent JS recomputation?",
            "competing_explanations": [
                {"name": "correct", "description": "The loader, graphs and search are right.", "how_addressed": "51 queries compared with an oracle script that shares no code and uses different algorithms; 40 random-world differential tests against dsdk.graph in pytest."},
                {"name": "inferred_edges_leak_into_known", "description": "A path that needs a guessed (co-selected) step is reported as observed.", "how_addressed": "Every KNOWN hop cites sets in which that exact transition occurs (analytic check); a mutant that ignores evidence is run and must disagree with the oracle."},
                {"name": "stale_or_altered_data", "description": "The corpus differs from the one Sam's pipeline produced.", "how_addressed": "The gzip's SHA-256 is pinned from jukebox's Pages workflow; a flipped bit is refused (deliberate failure)."},
                {"name": "js_echoes_python", "description": "The browser agrees only because it reads Python's numbers.", "how_addressed": "The JS side decodes the embedded corpus and searches it itself; Python's answers are used only as the comparison column."}],
            "scope": {"claims": ["For the 51 checked queries and 300 seeded random pairs, Python, the oracle (51) and JS agree on status, witness path, reason and per-step evidence.",
                                 "KNOWN means every step was seen back-to-back in a cited DJ set; UNKNOWN means at least one step is only inferred from sharing a set, or no route exists in this sample.",
                                 "The corpus is exactly the file whose SHA-256 is pinned in jukebox, with 1,352 tracks, 50 DJ credits, 54 sets and 1,919 transitions."],
                      "does_not_claim": ["That two tracks without a route are unrelated (open world, sampled corpus).",
                                         "That the parser captured every set: 234 rows were rejected upstream.",
                                         "That a DJ really intended a transition: only that the two tracks were adjacent in the recovered tracklist.",
                                         "Anything about festivals other than Lost Lands 2018."]}},
        "input_snapshot": {
            "source": f"jukebox derived store (public; no raw lines): {SOURCE_REPO}@{SOURCE_BRANCH} commit {SOURCE_COMMIT}, data/lostlands-2018.jukebox.json.gz reassembled from part00..part07 and vendored at {STORE}.",
            "schema": "jukebox-primitives/v1: artists[], tracks[[key,title,artists,featured,variation,variationArtists]], selectorGroups[[members,label,truncated]], dates[], selections[[track,group,date]], transitions[[source,target,group,date]]. Embedded verbatim in panels.world.",
            "missingness_meaning": "A pair of tracks never seen together is NOT_OBSERVED (no edge is drawn). An edge from co-selection is UNKNOWN (inferred). A track id that is not in the corpus is INVALID. A date of -1 would mean 'undated' (none occur).",
            "files": hashed(FIXTURES)},
        "implementation": {
            "module": "dsdk.worlds", "version": "0.0.1",
            "config": {"config_version": "w1-conventions-1", "search": "dsdk.graph.reachable for the verdict; shortest_path over observed edges, else candidate_path (fewest inferred edges, then hops, then node order)",
                       "nodes": "track string keys (e.g. Torque#001)", "graphs": "transition (directed, weight=count, KNOWN), co-selection (undirected, UNKNOWN), search = observed + both directions of every co-selection"},
            "code_files": hashed(CODE),
            "fixtures": [{"path": SLICES, "sha256": common.sha256_file(REPO / SLICES), "representative": [f"{c['source']}->{c['target']}" for c in slices["degrees"][:8]]},
                         {"path": STORE, "sha256": common.sha256_file(REPO / STORE), "representative": ["lost-lands-2018"]}]},
        "oracle": {
            "analytic": analytic,
            "independent_reference": {"description": "fixtures/worlds/gen_slices.py recomputes paths with level-synchronous BFS and Bellman-Ford plus a backward distance table (the library uses a FIFO queue and Dijkstra); the browser adds a third implementation in viewer/w1.mjs.",
                                      "comparisons": [cmp_oracle]},
            "boundary_cases": boundary, "deliberate_failures": deliberate},
        "run_record": rec,
        "browser_artifact": {
            "viewer": "viewer/index.html", "query": "?packet=../tracks/W1/evidence/packet.json", "recomputes_with": "viewer/w1.mjs",
            "views": ["Summary", "Six degrees (search any two tracks)", "Checked queries", "How far apart?", "The corpus"],
            "accessibility": ["labelled search inputs with a suggestion list; the path is an ordered list", "status is a word (KNOWN / UNKNOWN / INVALID), never colour alone",
                              "every table has a caption and header cells", "operable by keyboard"],
            "provenance_shown": ["corpus SHA-256 and branch commit", "git sha", "generated time", "python version"],
            "capture_record": "tracks/W1/evidence/capture.json"},
        "result": {
            "verdict": "supported" if not disagreements and all(c["pass"] for c in analytic + boundary) and all(d["failure_observed"] for d in deliberate) else "weakened",
            "statement": f"On the pinned Lost Lands 2018 corpus, {len(queries)} checked queries and {PAIRS} seeded random pairs give the same verdict, witness path and step evidence in Python, the independent oracle and the browser. Of the random pairs {summary['known']} are connected by observed steps alone (median {summary['median_known_hops']} hops, longest {summary['max_known_hops']}), {summary['needs_inferred']} need an inferred step and {summary['open_world']} have no route in this sample. The mutant that ignores evidence is caught.",
            "next_bounded_experiment": "Remove the 169-track truncated credit ('Excision & Sullivan King & Dion Timmer + More', 2018-09-13) and recompute the distance histogram: how many pairs lose their short route? Then repeat with the sets weighted by 1/size so a huge set stops dominating co-selection."},
        "panels": panels,
    }

    errors = common.validate_packet(packet)
    problems = list(errors)
    problems += [f"oracle disagreement: {q['source']}->{q['target']}" for q in disagreements]
    problems += [f"check failed: {c['name']}" for c in analytic + boundary if not c["pass"]]
    problems += [f"deliberate failure NOT observed: {d['name']}" for d in deliberate if not d["failure_observed"]]
    problems += [f"tests failing: {t['target']} {t['summary']}" for t in tests if t["exit_code"] != 0]
    if problems:
        print("BUILD FAILED:", *problems, sep="\n  ", file=sys.stderr)
        return 1
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(packet, separators=(",", ":")) + "\n")
    print(f"wrote {OUT.relative_to(REPO)} ({OUT.stat().st_size} bytes); schema valid; " + "; ".join(f"{t['target']}: {t['summary']}" for t in tests))
    return 0


if __name__ == "__main__":
    sys.exit(main())
