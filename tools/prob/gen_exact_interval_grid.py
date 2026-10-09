"""Regenerate fixtures/prob/exact_interval_grid.json from the SLOW reference implementation of dsdk.prob.exact_interval.

The fixture freezes the outputs of the exact-Fraction bisection (60 halvings) so that a faster implementation can be
compared against it to 1e-12. Run it ONLY against the slow reference (the Fraction version). It takes about 25 minutes on 4 cores
because the reference needs about 6 s per (k, n) at n = 300 and minutes per point at n >= 1000.

    .venv/bin/python tools/prob/gen_exact_interval_grid.py [--workers 4] [--out fixtures/prob/exact_interval_grid.json]

Grid: every k for n in {1, 2, 3, 5, 10, 30, 100, 300}; spot checks at n = 1000 and n = 2000 (SPOTS below).
The script refuses to run if exact_interval is already fast (a 5/100 call under 0.1 s), because then it would be freezing the
output of the thing under test instead of the reference.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

GRID_N = (1, 2, 3, 5, 10, 30, 100, 300)
SPOTS = {1000: (0, 1, 500, 1000), 2000: (0, 1000, 2000)}
ROOT = Path(__file__).resolve().parents[2]


def one(case: tuple[int, int]) -> list:
    from dsdk.prob import exact_interval

    k, n = case
    low, high = exact_interval(k, n)
    return [k, n, low, high]


def cases() -> list[tuple[int, int]]:
    out = [(k, n) for n in GRID_N for k in range(n + 1)]
    out += [(k, n) for n, ks in SPOTS.items() for k in ks]
    # most expensive first so the pool stays busy
    return sorted(out, key=lambda c: -c[1])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--out", default=str(ROOT / "fixtures" / "prob" / "exact_interval_grid.json"))
    args = ap.parse_args()
    from dsdk.prob import exact_interval

    t = time.time()
    exact_interval(5, 100)
    if time.time() - t < 0.1:
        print("exact_interval is already fast: refusing to freeze it (use the slow Fraction reference)", file=sys.stderr)
        return 2
    started = time.time()
    with ProcessPoolExecutor(args.workers) as pool:
        rows = list(pool.map(one, cases(), chunksize=1))
    rows.sort()
    doc = {
        "meta": {
            "what": "outputs of the slow exact-Fraction dsdk.prob.exact_interval at confidence 0.95",
            "generator": "tools/prob/gen_exact_interval_grid.py",
            "grid_n": list(GRID_N),
            "spots": {str(n): list(ks) for n, ks in SPOTS.items()},
            "seconds": round(time.time() - started, 1),
        },
        "cases": rows,
    }
    Path(args.out).write_text(json.dumps(doc, indent=0) + "\n")
    print(f"wrote {len(rows)} cases to {args.out} in {time.time() - started:.0f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
