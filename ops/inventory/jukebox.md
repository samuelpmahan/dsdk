## Latest
- Newest remote branch is `origin/lab/composable-mining`, last commit 2026-09-06 (8b4d32b), Samuel Mahan: "Add six-method LAB mining runner with inspectable corpus receipts". `origin/main` is 2026-09-04: "Let projection slider expose the local graph". The earlier "main only" note was wrong; the remote has two branches.

## Purpose
A TypeScript revival of a 2018 graph recommender that builds a track-level graph from DJ set tracklists and offers an inspectable local-graph and set-builder UI; raw tracklists are not committed, only derived gzip primitives. The `lab/composable-mining` branch adds a privacy-bounded mining runner (SKOPUS, ClaSP, SQUISH, SUBDUE, an EMM-inspired contrast screen, and a Kleinberg-style burst screen) that emits compact receipts while keeping raw inputs local.

## Stack
TypeScript (`src/model.ts`, `src/parser.ts`), a vanilla `index.html` browser UI, npm scripts, gzip stored as eight binary-safe text chunks in `data/`, reassembled in the browser with `DecompressionStream` and checked against a pinned SHA-256. The lab branch adds Python 3.11+, optional SPMF (Java 17) providers, and `lab/` receipts.

## Key modules
- `/home/user/samuelpmahan/jukebox/src/model.ts` — `Track`, `Transition` (count-weighted directed edge with a pk), `Tracklist`, and the `Jukebox` aggregate.
- `/home/user/samuelpmahan/jukebox/src/parser.ts` — tracklist line parser with variation and featured-credit extraction and `rejectedLines`.
- `/home/user/samuelpmahan/jukebox/src/model.test.ts` — model tests.
- `/home/user/samuelpmahan/jukebox/scratch/build-primitives.ts` — builds the derived primitive store from a local corpus.
- `/home/user/samuelpmahan/jukebox/index.html` — browser graph and set-builder UI.
- `/home/user/samuelpmahan/jukebox/data/lostlands-2018.jukebox.json.gz.part00` through `part07` — chunked derived store.
- `/home/user/samuelpmahan/jukebox/lab/core.py` (branch `lab/composable-mining`) — shared privacy-bounded runtime contract, `jukebox-lab-receipt/v1` schema, `RunStatus`.
- `/home/user/samuelpmahan/jukebox/lab/methods/kleinberg.py` (branch `lab/composable-mining`) — burst screen over dated set-presence bins.

## Reusable for dsdk
- C2 — `/home/user/samuelpmahan/jukebox/src/model.ts` — `Transition` as a count-weighted directed edge between `Track` nodes; a transition-graph shape for C2 mining.
- A5 — `/home/user/samuelpmahan/jukebox/src/model.ts` — the same structure as an explicit track and artist graph, a reference for graph construction.
- B1 — `/home/user/samuelpmahan/jukebox/scratch/build-primitives.ts` — publishes derived data with a pinned SHA-256 and gzip integrity check; a provenance pattern.
- C4 — `/home/user/samuelpmahan/jukebox/lab/methods/kleinberg.py` — burst detection over dated bins with an upward-transition penalty; a temporal change screen, not a verified-release detector.
- B1 — `/home/user/samuelpmahan/jukebox/lab/core.py` — receipt schema and run-status enum that keep raw inputs out of published output.

## Evidence quality
- Medium-low on the main branch. Model tests (`src/model.test.ts`) exist but were not executed. There is no evaluation of recommendation or transition quality, and no held-out split.
- The lab branch has receipts from one executed run: `lab/evidence/2026-09-06/` (`run.json` plus six receipts). The input was 1,222 distinct nonempty sets, 43,941 ordered occurrences, and 19,282 track strings. Raw input and full outputs are not published, so the receipts cannot be re-derived from the repo.
- The EMM-inspired screen is explicitly not an EMM reproduction, and its contrasts carry no adjusted significance claim. Lab method tests (`lab/methods/test_*.py`, `tests/test_*.py`) were not executed.

## Open questions
- Source tracklists are not in the repo. The lab branch names a "BigData415 archive". Confirm its origin and licensing before any dsdk use.
- Which of the six methods ran as SUCCESS in `run.json`, and which emitted unavailable-provider receipts? Not read.
- Is the projection slider a graph embedding (C3) or only a view over the existing graph?
