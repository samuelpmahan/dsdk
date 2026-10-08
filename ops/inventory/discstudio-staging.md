## Latest
- Newest branch: `origin/boone/uds-live-label`, 2026-09-14, commit `ec1141f`: "Remove CSS scroll-snap from focus lanes: iOS Safari's snap yanked the lane back to start on real phones..." (its own `CLOUD-START.md` calls it the focused UploadDiscToShelf build).
- Default branch: `origin/main`, 2026-09-12, "land(task-150): ... neat hot names the hot Calculations ... and neat equiv rebuilds every receipt's inputs". Main and the boone branch have very different trees (about 3,700 vs 393 files, different layouts), so a plain diff is not useful.
- Other recent: `origin/exp/140` through `origin/exp/150` (2026-09-12, "exp/NNN: packet (suite exit 0)") are per-experiment packet commits on main's lineage; not inspected.

## Purpose
DiscStudio PxC staging is a static, no-backend GitHub Pages app (`#/shelf`, `#/course`, `#/components`, `#/competition`) that runs the DiscStudio domain through the ChainSpot PxC/PQL runtime. It has physical discs, photos and paint art, Bags, battle/course scoring and transparent PNG/SVG export. The newest branch adds P&C "Experience" definitions (UploadDiscToShelf, ExploreShelf and others) loaded as Studio Parts.

## Stack
- Plain JavaScript ES modules (`"type": "module"`), no runtime npm dependencies, Node 22+ (`package.json`).
- Vendored Python "pyto" kernel tree (`pyto/` on main, ~3,557 files; `pyto/` on boone with 35 files) and Python 3 with Playwright for browser checks (`scripts/browser_test.py`).
- Test runner: `node --test tests/*.test.js` (`npm test`). Build: `node scripts/build.mjs`. Browser: Playwright (Python).
- Pages deploy: per README, CI runs unit tests, builds, runs browser checks, then deploys (workflow file not opened).

## Key modules
- `src/runtime.js` — `createStudioRuntime`: the application adapter over the ChainSpot exec board (`createExecBoard`, `pxFn`, `invokePql`); names `fn.*` calculations and `px.*` addresses; memo reuse vs computation trace.
- `src/core/exec.js` — ChainSpot exec/PQL core (`createExecBoard`, `readPql`, `invokePql`, `invokePqlAsync`); used by runtime.js.
- `src/domain.js` — object/field definitions and the immutable command reducer (`applyCommand`, `validateWorld`, `discoverFields`).
- `src/presentation.js` — the single card/graphic implementation: `prepareDiscArt`, `composeCard`, `cardSvg`, `composeOverlay`, `materializeOverlay`.
- `src/constraints.js` — bag count, distinct mold, exact team throw, AND/OR combination (`combineConstraints`, `teamThrows`).
- `src/battle.js` — battle standings and entries (names taken from runtime.js imports; file not opened).
- `src/experiences.js` — `studioExperienceParts()`: P&C Experience definitions as ordinary Parts (`px.studio.uds.definition`, `px.studio.exploreshelf.definition`, `px.studio.discviztype.photo/paint`, etc.). Newest branch only.
- `src/shelf.js` — `shelfQuery` (shelf filter/order; name taken from runtime.js imports).
- `src/art.js` — `assignArt`, `shelfItems` (painter assignment for physical discs).
- `src/exports.js`, `src/formats/shelf-sheet.js`, `src/formats/receipt-list.js`, `src/formats/undo.js` — export and format modules (path only; not opened).
- `src/lab/stages.js` and `src/lab/s*.js` — the lab pipeline stages S0–S7 with `.mmd`/`.pcr.yaml` sources and records under `src/lab/store/`.
- `pyto/consumers/discstudio-card/port/painter/painter.mjs` — the painter family registry (`FAMILIES`) used by art and tests.
- `pyto/viewer/adapters.js` — `fromDiscStudioReceipt`, `validate` (receipt adaptation).
- `docs/experiences.md` — Experience definition doc (newest branch).
- `AGENTS.md` — the agent contract: all work goes through the existing PxC/PQL integration, no competing state store or renderer.

## Reusable for dsdk
- B1 — `src/runtime.js` — memoized results are kept in PxC "matched by full inputs and calculation revision" with a trace that separates reuse from computation; directly relevant to reproducibility and provenance.
- D3 — `src/domain.js` — "Adding a displayable field makes it discoverable"; field metadata declared once, plus an immutable command reducer. A small typed-contract pattern.
- D3 — `src/constraints.js` — composable AND/OR constraint definitions with explicit "unconstrained" rather than a fake pass; useful for typed validation.
- C5 — `src/shelf.js` — shelf query; retrieval-style filter over typed records.
- B3 — `src/core/exec.js` — the PQL reader/executor, mirrored in `discstudio/source/candidate-pxc/chainspot/exec.js`; a second copy for parity testing.
- A2 — `src/lab/stages.js` (`labStageSpecs`, `validateStage`) with `src/lab/source/*.pcr.yaml` — declarative stage specs plus a validator; I saw the names in imports, not the file contents.

## PxC / provenance concepts
- Addressed values: `px.studio.*` and `px.shelf.*` addresses (`src/experiences.js`, `docs/experiences.md`); the runtime names every Part by address.
- Calculations: `fn.*` (e.g. `fn.studio.applyCommand`, `fn.shelf.query`, `fn.disc.art`, `fn.art.assign`) registered on the board (`src/runtime.js`, `src/experiences.js`).
- Ticks / PQL: lab stages use `.mmd` and `.pcr.yaml` compositions; `invokePql` runs them (`src/core/exec.js`).
- Provenance: `labelHash`, `partAddress`, `stable` and `freeze` in `src/domain.js` and `src/runtime.js`; `calls`, `counters` (calls/computed/reused) and a `previousObjects` set track reuse; `pyto/viewer/adapters.js` converts DiscStudio receipts.
- Experience contexts publish under `px.studio.<key>.context.*` on use (`docs/experiences.md`).
- Explicit limit (from runtime.js comment): memo caches are session-local, not durable.

## Evidence quality
- Unit tests: 25 `*.test.js` on main under `tests/`; 35 on the newest branch (including `tests/uds.test.js`, `tests/runtime-signature.test.js`, `tests/shelf.test.js`).
- Lab records and invariants exist under `src/lab/store/records/` (e.g. `S7.course.invariants.json`), and the newest branch has `evidence/` (155 files, e.g. `evidence/card-render/`).
- The `pyto/` tree holds receipts and experiments; I did not open them.
- I did not run tests, builds, or Playwright (read-only survey).
- The README states the CI order (unit, build, browser, then deploy) and that review checkpoints are automated fixtures, not Sam's acceptance.

## Open questions
- Whether the boone branch's Experience frame and UDS fill (`CLOUD-START.md` "Build the frame, then fill it") are complete. I read the definitions only, not the views or actions.
- Whether the boone branch's `src/runtime.js` (with `runtime-signature.test.js`) is the same code as main's `src/runtime.js`, or a fork: the two differ, but I did not diff them line by line.
- Which tree is canonical: main (lab + pyto, 2026-09-12) or boone (experiments + evidence, 2026-09-14). The `bundle-source.json` on the boone branch names base `455f66d` on branch `codex/card-render-experiment`, which I did not verify.
- Whether the `exp/NNN` packet branches contain code changes beyond the single "packet" commit each.
- `scripts/review_checkpoint.mjs` and `.neat/items/DS-STUDIO-02.json` (named in AGENTS.md) were not opened.
