"""Append to and summarise the agent-dispatch ledger (ops/ledger.jsonl).

    python ops/ledger.py log TASK MODEL ATTEMPT OUTCOME WALL_S [--tests P/T] [--note ...]
    python ops/ledger.py stats

`stats` prints per-model pass rates and the recommended Haiku concurrency
under the AIMD policy in ops/README.md.
"""
from __future__ import annotations

import argparse
import json
import time
from collections import defaultdict
from pathlib import Path

LEDGER = Path(__file__).with_name("ledger.jsonl")
START, CAP, FLOOR = 2, 3, 1


def load() -> list[dict]:
    if not LEDGER.exists():
        return []
    return [json.loads(line) for line in LEDGER.read_text().splitlines() if line.strip()]


def log(args: argparse.Namespace) -> None:
    passed = total = None
    if args.tests:
        passed, total = (int(x) for x in args.tests.split("/"))
    entry = {
        "ts": int(time.time()), "task": args.task, "model": args.model,
        "attempt": args.attempt, "outcome": args.outcome, "wall_s": args.wall_s,
        "tests_passed": passed, "tests_total": total, "round": args.round, "note": args.note,
    }
    with LEDGER.open("a") as fh:
        fh.write(json.dumps(entry) + "\n")


def recommended_concurrency(entries: list[dict]) -> int:
    """Replay AIMD over Haiku rounds in order."""
    level = START
    rounds: dict[int, list[dict]] = defaultdict(list)
    for e in entries:
        if e["model"] == "haiku" and e.get("round") is not None:
            rounds[e["round"]].append(e)
    for r in sorted(rounds):
        batch = rounds[r]
        bad = any(e["outcome"] in ("fail", "error") and e["attempt"] >= 2 for e in batch) or any(
            e["outcome"] == "error" for e in batch
        )
        clean = all(e["outcome"] == "pass" and e["attempt"] == 1 for e in batch)
        if bad:
            level = max(FLOOR, level // 2)
        elif clean:
            level = min(CAP, level + 1)
    return level


def stats(_: argparse.Namespace) -> None:
    entries = load()
    by_model: dict[str, list[dict]] = defaultdict(list)
    for e in entries:
        by_model[e["model"]].append(e)
    for model, es in sorted(by_model.items()):
        n = len(es)
        p = sum(e["outcome"] == "pass" for e in es)
        first = [e for e in es if e["attempt"] == 1]
        p1 = sum(e["outcome"] == "pass" for e in first)
        wall = sum(e["wall_s"] or 0 for e in es)
        print(f"{model:7s} attempts={n:3d} pass={p:3d} first-try={p1}/{len(first)} wall={wall}s "
              f"mean={wall / n if n else 0:.0f}s")
    print(f"recommended haiku concurrency: {recommended_concurrency(entries)}")


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(required=True)
    lg = sub.add_parser("log")
    lg.add_argument("task"); lg.add_argument("model"); lg.add_argument("attempt", type=int)
    lg.add_argument("outcome", choices=["pass", "partial", "fail", "error"])
    lg.add_argument("wall_s", type=int)
    lg.add_argument("--tests"); lg.add_argument("--note", default="")
    lg.add_argument("--round", type=int)
    lg.set_defaults(func=log)
    st = sub.add_parser("stats"); st.set_defaults(func=stats)
    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
