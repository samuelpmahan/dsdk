## Latest
- Newest branch: `origin/codex/studio-workbench`, 2026-09-14, "Add inspectable Experience cases and retain sandbox iterations" (commit `6f7937b`). It holds the most work: 252 files, including `exp/upload-disc-to-shelf` and `.neat/ds/`.
- Default branch: `origin/main`, 2026-09-12, "Name the fresh PnC destination and clarify publication state". Main is the small handoff export (21 files: `AGENTS.md`, `CLOUD-BRIEF.md`, `RETURN.md`, `exp/part-first-kernel`, `reference/neat-ontop`). No `exp/upload-disc-to-shelf` on main.

## Purpose
PnC ("P&C") is the working repo for the Part-first experiment: an isolated, in-memory prototype of Parts (values with a composition record) and Calculations (Parts with an executable role). Its newest branch also carries the DiscStudio "upload disc to shelf" Studio workbench, which runs on that same Part store. Nothing here is promoted to core; results go back to the originating conversation as reviewable candidates.

## Stack
- Plain JavaScript ES modules (`.mjs`) for the kernel; TypeScript (`.ts`) for the Studio app, run by Node 24 (`node server.mjs`) with no installed dependencies.
- Test runner: Node built-in `node --test` (`exp/part-first-kernel/package.json` scripts: `test`, `demo`).
- Some `.html` front ends and an `.mjs` dev server (`exp/upload-disc-to-shelf/server.mjs`).

## Key modules
- `exp/part-first-kernel/src/pxc.mjs` — `Part` (frozen wrapper; `composition` is null for supplied material) and `PxC` (`set`, `get`, `entries`, `receipts`, async `compose({into, calculation, inputs})`).
- `exp/part-first-kernel/src/inspect.mjs` — `contributorsOf(part)` and `usesOf(pxc, part)` helpers for tracing composition links in both directions.
- `exp/part-first-kernel/CONTRACT.yaml` — the current Part-first definition and API (supersedes the draft below).
- `exp/part-first-kernel/examples/demo.mjs` — runnable demo: `2 + 3 = 5`, a produced Calculation `double`, and shared-body Basket assemblies.
- `exp/part-first-kernel/test/pxc.test.mjs` — kernel tests (28 tests across the part-first suite, per `evidence/tests.tap`).
- `exp/upload-disc-to-shelf/persistence.ts` — `storageKey` `discstudio.pxc.shelf.v1`; `archive(state)` serialises the Part graph to an OnTop-format JSON (nodes, material, calculation/input links, bindings).
- `exp/upload-disc-to-shelf/operations.ts` — "OnTop operations": `Calculation`/`Tick` types; a Tick composes its calculations then a `fn.tick` step.
- `exp/upload-disc-to-shelf/model.ts` — Studio model over the PxC store (seeds, `createExperience`, imports `paint.ts`, `shelf-query.ts`, `bags.ts`, `plastics.ts`, `catalog.ts`).
- `exp/upload-disc-to-shelf/sandbox-cases.ts` — `CaseStep`/`Check` shapes for Experience cases (the newest commit's feature).
- `exp/upload-disc-to-shelf/devtools.mjs` and `devtools-data.mjs` — Part inspection UI and data over the live store.
- `exp/upload-disc-to-shelf/shelf-query.ts` — composable shelf filtering and ordering.
- `exp/upload-disc-to-shelf/bags.ts` — Bag creation and membership helpers.
- `exp/upload-disc-to-shelf/paint-recipe.ts` — `validatePaintRecipe`, `recipeFromDraft`, `renderDepiction`.
- `.neat/ds/experiences/EXPERIENCES.md` and `.neat/ds/experiences/MUSE-PXCUBE.md` — design notes linking the Studio work to PxCube (read by name only; contents not opened).

## Reusable for dsdk
- B1 — `exp/part-first-kernel/src/pxc.mjs` — every produced Part keeps the exact Calculation and named input Part references (`composition`), plus a frozen failed/produced receipt log; direct fit for provenance and lineage.
- B1 — `exp/upload-disc-to-shelf/persistence.ts` — replayable archive of a Part graph with the composition links preserved and an explicit refusal ("Unsupported persistent material") for values it cannot serialise; the pattern fits reproducible artifacts.
- B3 — `exp/part-first-kernel/src/inspect.mjs` — `contributorsOf`/`usesOf` as ordinary helpers outside the evaluator; a template for lineage queries.
- D3 — `exp/part-first-kernel/CONTRACT.yaml` — written "deliberate bounds" list (borrowed in-memory payloads, hidden inputs of trusted functions, no determinism proof); a useful checklist for typed contracts.
- C5 — `exp/upload-disc-to-shelf/shelf-query.ts` — composable filter/order over typed records; relevant to retrieval-style queries.
- D2 — `exp/upload-disc-to-shelf/operations.ts` — Tick = batch of Calculations plus a summary step; a simple pattern for staged computation.

## PxC / provenance concepts
- Addressed values: `PxC.set(address, part)` refuses occupied or in-flight addresses; `get` fails on missing addresses (`exp/part-first-kernel/src/pxc.mjs`). Addresses are local handles, not global names.
- Calculations: a Calculation is a function-valued Part (`fn.*` by convention in the example); no separate registry (`CONTRACT.yaml`).
- Composition/lineage: `compose` records `{calculation, inputs}` on the output Part and pushes `produced` or `failed` receipts (`pxc.mjs`); `contributorsOf` and `usesOf` trace both directions (`inspect.mjs`).
- Ticks: `operations.ts` declares `Tick = {into, calculations[]}` and composes each step, then a `fn.tick` summary Part.
- Provenance on disk: `persistence.ts` writes `nodes` (material or calculation/input links) and `bindings`; storage key `discstudio.pxc.shelf.v1`.
- Explicit limits: no immutable snapshots, no sandboxing, no persistent executable replay (`exp/part-first-kernel/README.md`).

## Evidence quality
- `exp/part-first-kernel`: 1 kernel test file plus a `evidence/tests.tap` (28 tests, all pass per the committed TAP output; not re-run by me). `evidence/demo.txt` and `evidence/SHA256SUMS` also present.
- `exp/upload-disc-to-shelf`: 13 `*.test.ts`/`*.test.mjs` files (`bags`, `catalog`, `experiences`, `import-integration`, `legacy-archive`, `model`, `operations`, `paint-recipe`, `persistence`, `sandbox-cases`, `shelf-query`, `shelf`, `devtools`). Plus the `.neat/ds/experiences/evidence/` tree (browser results, unit logs) for the sandbox-consumer case.
- Total test-like files on the newest branch: 14 under `exp/`. The branch's own DEVELOPMENT.md gives the commands but says "no dependency installation".
- I ran nothing; all results above are the committed artifacts, not fresh runs.

## Open questions
- Whether `evidence/tests.tap` is current for the newest branch's kernel bytes (it was committed on the export baseline; I did not check hashes against `SHA256SUMS`).
- Whether the upload app's `persistence.ts` archive round-trips (I read the serialiser only; I did not open the loader).
- Relationship to the pxcube `vendor/studio/part-first-kernel` copy: the same `pxc.mjs` lineage appears in both repos; which is canonical is not stated.
- `reference/neat-ontop/` archive (tarball) contents were not inspected.
- The `.neat/ds/imports/boone-uds` import packet and the 36-commit contribution map referenced by DEVELOPMENT.md were not opened.
