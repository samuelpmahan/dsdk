# dsdk roadmap

dsdk is a data-science SDK built by working through a curriculum. The organising rule is **diagonal scaling**: every
track has to consume earlier tracks' code, so the pieces connect as they are built and nobody has to assemble them
at the end. `tests/test_reuse.py` enforces this using the orders in `tracks.toml`. A package that imports nothing
earlier fails the build.

Python is the rigour side: the SDK, proofs and reference calculations. A single JS viewer (not built yet) is the
demonstration side. It reads the same `fixtures/` JSON, and it reimplements only the kernels that are worth checking
independently.

## The spine

`dsdk.core` (A0) is the kernel. It has two parts:

- **Status/Judgment**: KNOWN, UNKNOWN, NOT_OBSERVED, INVALID, NOT_APPLICABLE. These are never collapsed into each other.
- **Part-first PxC**: write-once addresses (`px.*`, `fn.*`, `sc.*`). Calculations are Parts too. Every composed Part
  carries its `composition`, so lineage is a DAG of Parts. An atomic `tick` groups multi-step updates.

This is a port of the owner's newest PxC design (`pxcube` `vendor/studio/part-first-kernel`, 2026-09-28). It is not
the older Wumpus `pxc.js` with mutable slots.

## Stage 1 as a web, not five parallel lanes

| Track | Package | Builds | Consumes (enforced) |
|---|---|---|---|
| A0 | `dsdk.core` | Status, Judgment, Part, PxC, tick | — |
| A1 | `dsdk.logic` | formulas, strong-Kleene partial evaluation, model enumeration, entailment, proof checker, induction exercises | core (`Judgment` is the 3-valued result) |
| A2 | `dsdk.lang` | tokenizer/parser that round-trips A1's canonical formula strings, then a typed expression language | logic (sublanguage + evaluator), core |
| A5 | `dsdk.graph` | graphs, BFS with witness paths, topo sort, cycles | core (traverses the **Part lineage DAG**), lang (AST is a tree; evaluation order is a topo sort) |
| A3 | `dsdk.prob` | possible worlds = A1 models; weighting, conditioning, marginals, sampling vs exact | logic (`models`), core (`tick` for belief updates), graph (Bayes-net structure) |
| A4 | `dsdk.geom` | vectors, least squares, gradients; spectral (Laplacian) embedding | graph (Laplacian), prob (expectations) |

Order: A0 → A1 → A2 → A5 → A3 → A4. A5 moves ahead of A3 because probability over a network needs graphs.

## Worlds in circulation

1. **Wumpus.** It ties A1, A3, A5, C4 and C5 together. A1 already holds the Russell & Norvig corner KB, which has 3
   models (`fixtures/logic/wumpus_kb.json`). A3 weights those models with the pit prior, and the result must
   reproduce the 4/9, 4/9, 1/9 numbers from `embodiedwumpusworld/src/priors.js`. The JS world in
   `embodiedwumpusworld@lab/wumpus-core` is the B3 parity partner, and it is already oracle-checked against the WSU
   simulator.
2. **dsdk itself.** The repo's own import graph and PxC lineage are data. A5 replaces the hand-written logic in
   `test_reuse.py` with `dsdk.graph`. C2 mines the dependency graph.
3. **A tabular/transaction source, chosen at B1.** Candidates:
   - jukebox listening transitions (`lab/composable-mining`)
   - the hithero schools CSV seed
   - a synthetic workflow

## Existing work each track should start from

These come from `ops/inventory/`. "Start from" means: read it, port the idea, and cite it in the track card. It does
not mean vendoring the code.

| Track | Source |
|---|---|
| A3 | `embodiedwumpusworld/src/core/probability.js` (`conditionWeights`, `marginalProbability`), `src/wumpus/belief.js` |
| B1 | `chainspot@pxcube/lifecycle-spine packages/alg/src/exec/{pcr,sink,neat}.ts`, `jukebox/lab/core.py` (receipt schema), `neat/src/work-items.ts`, `toph/examples/*/manifest.json` |
| B2 | `chainspot … exec/stage.ts` (A/B features as calculation overrides + comparator) |
| B3 | `chesslab/scripts/generate-learning-cases.py` (independent Python oracle → JS fixtures), `toph/test/adversarial/*known-gap*` (pin known failures), `audio-viz@agent/dsp-eval-harness eval/metrics/events.js` |
| C2 | `jukebox/src/model.ts` (count-weighted transition graph) |
| C4 | `jukebox/lab/methods/kleinberg.py` (burst detection), `audio-viz … eval/types.d.ts` (causal streaming contract) |
| D3 | `chainspot … exec/{contract,crisp}.ts`, `pxcube/kompoze/typed-overlay.mjs`, `neat/src/{pxc,pcr}.ts`, `chesslab/src/lab/contract.ts` |

## Board

States: Proposed → Selected → Building → Evidence ready → Reviewed.

| Track | State | Next bounded step |
|---|---|---|
| A0 core | Evidence ready | 189 tests green. Next: evidence packet + browser capture of tick rollback receipts |
| A1 logic | Evidence ready | 472 logic + 189 core tests green; browser evidence 29/29 (`tools/evidence/run.sh A1`); proofs audited twice. Next: Sonnet audit of PROOFS.md; evidence packet + browser captures (truth tables, countermodels, Wumpus worlds) |
| A2 lang | Evidence pending | 1,338 lang tests green (T09–T16, all first try). Formulas parse back to A1 ASTs; Calc evaluation traces are PxC lineage chains. Next: proof audit (by W), Lab query bar |
| A5 graph | Evidence pending | 273 graph tests green (T20–T26, all first try); dsdk now checks its own import graph with its own graph code. Next: proof audit (by F), "Six degrees" instrument (W) |
| A3 prob | Proposed | Contract: weight `wumpus_kb` models; reproduce 4/9, 4/9, 1/9 |
| A4 geom | Proposed | — |
| B1–B3, C1–C5, D1–D3, capstone | Proposed | See the original curriculum brief |

## How work is dispatched

See `ops/README.md`.

- **Sonnet** writes contracts and tests.
- **Haiku** implements, with 2 attempts per task and at most 3 running concurrently.
- **Opus** plans, reviews and commits.

Backpressure is tracked in `ops/ledger.jsonl` (`python ops/ledger.py stats`). Haiku failure modes are recorded in
`ops/haiku-limits.md`.

**Sam's part:** direction only (`ops/for-sam.md`). Agents write the code, the proofs, the audits and the evidence.
