## Latest
- Branch `main` (only remote branch on disk). Last commit 2026-09-05, Samuel Mahan: "Record Terra XHigh ladder and expose hidden immediate mate risks".

## Purpose
A browser and terminal chess "LAB" debugger that shows a deterministic, inspectable policy model of each side (attacks, blockers, defenders, candidate moves, heuristic score components) over FEN frames. It also has a CLI arena where agents or Stockfish submit moves that are validated by chess.js and retained; the README says the model is not an engine score and not a recovery of historical players' thoughts.

## Stack
TypeScript run directly by Node 22.18+ (`node src/tui.ts`, `node --test tests/*.test.ts`), chess.js 1.4.0 as the only dependency, a browser build via `scripts/build.mjs` into `site/` (GitHub Pages), Python python-chess for fixture generation, optional Stockfish 18 Lite UCI.

## Key modules
- `/home/user/samuelpmahan/chesslab/src/chess/debugger.ts` — `runDebugger` entry shared by browser and terminal; returns a snapshot with receipts.
- `/home/user/samuelpmahan/chesslab/src/chess/analysis.ts` — per-side relations, candidate moves, check witnesses, score components.
- `/home/user/samuelpmahan/chesslab/src/chess/stages/S0/clean/index.ts` and `/home/user/samuelpmahan/chesslab/src/chess/stages/S1/clean/index.ts` — S0 piece construction and S1 relationships/decisions.
- `/home/user/samuelpmahan/chesslab/src/lab/contract.ts` — types-only shared execution contract (five verbs, slot refs, receipts); no I/O.
- `/home/user/samuelpmahan/chesslab/src/lab/host.ts` — synchronous host that records accesses and called calculation identities.
- `/home/user/samuelpmahan/chesslab/src/engine/uci.ts` — bounded UCI process for Stockfish analysis.
- `/home/user/samuelpmahan/chesslab/src/arena/index.ts` — agent move submission, legality via chess.js, retained outcome records.
- `/home/user/samuelpmahan/chesslab/scripts/generate-learning-cases.py` — python-chess generator used as an independent oracle.

## Reusable for dsdk
- B3 — `/home/user/samuelpmahan/chesslab/scripts/generate-learning-cases.py` — an independent Python oracle that generates fixtures the JS model is tested against; a concrete Python/JS parity pattern.
- B1 — `/home/user/samuelpmahan/chesslab/src/lab/host.ts` — receipts that record actual accesses and called calculation identities; provenance pattern. Caveat: runtime-function hashes cover only the function body, not transitive dependencies.
- D3 — `/home/user/samuelpmahan/chesslab/src/lab/contract.ts` — data-only typed operation/slot contract with an injected sink for I/O; a template for typed composition.

## Evidence quality
- Seven `*.test.ts` files under `/home/user/samuelpmahan/chesslab/tests/` (debugger, engine, arena, study, constraint, boardStory, state). Not executed in this survey.
- Trials in `/home/user/samuelpmahan/chesslab/trials/2026-09-06/` are two-game smoke runs with four LLM player contexts. The README says they are not a controlled comparison, and n is tiny.
- The README claims CI checks generated-output parity and python-chess agreement. Neither was verified here.

## Open questions
- `src/lab/board.ts` and `contract.ts` were copied from ChainSpot Sweep-Ready (pinned SHA in README). That repo is not on disk, so drift cannot be checked.
- Are the python-chess snapshots in `src/learningCases.ts` committed and asserted by tests, or regenerated ad hoc?
- The README says there is no PxCQL parser yet. Is any dsdk A2 expression language meant to consume these stages?
