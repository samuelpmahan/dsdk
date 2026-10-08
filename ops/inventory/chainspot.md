## Latest
- Newest branch: `origin/pxcube/lifecycle-spine`, committed 2026-09-23, subject "crisp: carry neat source provenance into Stage contract" (commit b8c3392).
- Default branch: `origin/main`, last commit 2026-08-28, subject "Remove accidental connector scratch file". Main is older than the PxCube branch and does not contain the `packages/alg/src/exec/` tree.
- Other recent branches (2026-09-20 to 2026-09-06): `lab/s0-viewer`, `task/disc-studio-v00`, `task/quick-anno-*`, `review/s1-*`, `lab/pxc-root-mounts`. 145 branches total, all fetched with depth 1.

## Purpose
ChainSpot is a browser-only SvelteKit app (Svelte 5, static adapter, no backend) for annotating golf-course hole geometry from images and for running a computer-vision pipeline that reads badges, baskets and tees out of those images. The newest branch adds "PxCube": an execution model in which stage algorithms are compiled to registered calculations with addressed values, lineage and receipts. A LAB CLI (`scripts/chainspot-lab/`) is the inspection surface.

## Stack
- TypeScript (strict, ESM), Svelte 5 runes, SvelteKit 2, Vite 6, Konva for raster drawing, fflate for the project archive, `yaml` for the PQL/stage files (packages/alg).
- Tests: Vitest (jsdom) for `tests/unit/*.test.ts` (125 files); plain `node --test` for `tests/node/*.test.mjs` (23 files, run by the PxCube workflow); Playwright for e2e (none present in the tree).
- Storybook 10 with a vitest addon; Python experiments under `experiments/dashs-track-edge-sensing/` (5 `test_*.py` files; runner not verified).
- Monorepo via npm workspaces: `packages/alg` is the algorithm package (`@chainspot/alg`).

## Key modules
- `packages/alg/src/exec/board.ts` — `PxC` address space: `get/set/has` on string SlotRefs, `register(fn.*)`, `call(fn.*)`, and `fork()` that shares the catalog but changes lineage.
- `packages/alg/src/exec/pcr.ts` — `composePcr()` builds a `chainspot-pcr@1` record from executed Tick testimony; `runResultId` is a SHA-256 over plan fingerprint, params hash and frozen tick identity. It deliberately has no run() method.
- `packages/alg/src/exec/pql.ts` — `readPql()` parses YAML `PrincipleComponentRender` + `Ticks[].Calculations[]` with `call: fn.*`, `with`, `args`, `into`; the run record keeps actual inputs and outputs by reference.
- `packages/alg/src/exec/gateway.ts` — `executeCompiledPlan`, the only function allowed to walk a compiled operation list; emits receipts through an injected sink.
- `packages/alg/src/exec/compile.ts` — `compileExecutionPlan`: legal operation orders from consumes/produces, a plan fingerprint from `sha256.ts`, a stable op-id tiebreak.
- `packages/alg/src/exec/contract.ts` — types-only contract: `SlotRef`, `PartEditionRef` (part@lineage/edition with producedBy tick and calculation), `CalculationAddress = fn.${string}`, `LineageAddress = clean | exp/*`.
- `packages/alg/src/exec/sink.ts` — `ExecSink` interface (`putArtifact`, `putReceipt`); core never touches disk.
- `packages/alg/src/exec/stage.ts` — `createPqlStage()`: default plus registered A/B features that override Calculations, each run through a comparator; records `executionMs`.
- `packages/alg/src/exec/crisp.ts` — compiles a Stage into a `pxc.stage/v1` contract (ticks, kinds, consumes, produces, calculations, assertions).
- `packages/alg/src/exec/neat.ts` — `NeatCatalog`: Calculations registered per lineage (`clean | work | exp/*`) with a repo-relative `source` path; duplicate registrations throw.
- `packages/alg/src/exec/speculative.ts` — `semanticDelta(before, after)` returns path-level differences between two value trees.
- `scripts/crisp.mjs` — `crisp delta <Stage>`: SHA-256 per file under `stages/<S>/clean` vs `stages/<S>/<lineage>`, reports added/removed/changed.
- `scripts/neat.mjs` — `neat work <Stage>`: seeds `work/` from `clean/`, refuses to clobber existing work.
- `packages/alg/src/stages/S0/clean/S0.stage.yaml` and `S0.pcr.yaml` — declarative S0 (intake/crop) stage: initial path, output `px.course.canonicalPixels`, receipt fields.
- `scripts/prototypes/badge-pcr/tick.ts` — prototype `Tick` with `TraceIdentity` (inputId, schemaId, coordinateFrame, planHash), explicit `evidence` and `residue`, and `unexplained` list on the PCR trace.
- `docs/WORKFLOW.md` and `AGENTS.md` — the working rules: small demonstrable progress, receipts as acceptance, "every number ships with where it came from".

## Reusable for dsdk
- B1 — `packages/alg/src/exec/pcr.ts` — content-addressed run identity over plan fingerprint plus tick identity; it states its limit (opaque values need a Materialization) and that limit is worth copying.
- B1 — `packages/alg/src/exec/sink.ts` — injected sink keeps the core pure; artifacts and receipts are written by the caller.
- B1 — `packages/alg/src/exec/neat.ts` — lineage-separated registry (`clean`, `work`, `exp/*`) with duplicate-registration errors and repo-relative source provenance.
- B1 — `scripts/crisp.mjs` — per-file digest diff between a baseline and a working copy; a small model for "what changed" receipts.
- B2 — `packages/alg/src/exec/stage.ts` — A/B features as Calculation overrides plus a comparator, with executed-time recorded per variant.
- D3 — `packages/alg/src/exec/contract.ts` — open string SlotRef namespace with the legality check left to the compiler walk; `PartEditionRef` is a good shape for typed lineage references.
- D3 — `packages/alg/src/exec/crisp.ts` — stage contract schema generated from declarations, not hand-written.
- D3 — `packages/alg/src/exec/pql.ts` — YAML composition with fail-loud validators (`expected a registered fn. address`).
- B3 — `packages/alg/src/exec/speculative.ts` — `semanticDelta` for parity comparisons between two outputs.
- C4 — `scripts/prototypes/badge-pcr/tick.ts` — explicit `unexplained` residue list alongside evidence; keeps unknowns visible rather than dropped.

## PxC / provenance concepts
- Addressed values: `PxC` board with string SlotRefs (`px.course.canonicalPixels`, `badgeStage.masks`), typed through `PxKey<T>`; fail-loud reads.
- Calculations: `pxFn<Args,Result>('fn.*')` address, `register`/`call` on the board; `neat.ts` keeps the implementation registry per lineage; PQL YAML binds them by `call: fn.*`.
- Ticks/operations: `operations.ts` groups operations under engine units (an ownership label); `compile.ts` orders them from consumes/produces; `pcr.ts` composes executed Tick testimony into a PCR record.
- Lineage: `clean | work | exp/*` on parts and on Stage directories; `board.fork(lineage)` shares the catalog and changes resolution context.
- Receipts and provenance: `Receipt` per operation, `planFingerprint` and `paramsHash`, artifact SHA-256s, `crisp` Stage contract with `source` links from `neat`.
- Lineage of values: `PartEditionRef` records part, lineage, edition and producing tick/calculation.

## Evidence quality
- 125 Vitest unit files in `tests/unit`, 23 `node --test` files in `tests/node` (all `pxcube-*`), 1 spike test. No Playwright e2e files exist in the tree although AGENTS.md mentions them.
- The `pxcube-lifecycle.yml` workflow (triggered on `pxcube/**`) runs a fixed list of `tests/node` files plus receipt runners and uploads artifacts; AGENTS.md says there is no general test CI gate.
- Nothing was run for this survey. No npm install, no build, no tests were executed; only `git fetch` and `git show`/`ls-tree` were used.
- Latest-branch commit messages describe passing proofs ("Materialize full receipt suite"), but I did not verify those receipts exist in the tree.

## Open questions
- Whether `main` or `pxcube/lifecycle-spine` is the intended trunk: `docs/WORKFLOW.md` (a historical record) says `main` is "dead" and lanes stack on the LAB trunk, but the default HEAD is `main`. Confirm with Sam.
- Whether `lab/s0-viewer` (cited by the staging repo's stoplight as the source of its `board.ts`) matches `pxcube/lifecycle-spine` `board.ts`; not diffed.
- Whether the crisp contract outputs (`artifacts/crisp/<Stage>.stage.json`, read by `scripts/crisp.mjs`) are committed anywhere; not checked.
- Behavior of `scripts/pxcube-graph.mjs` (imported by `crisp.mjs` for `invalidationClosure`) was not opened.
- S1–S4 stage contract files (`packages/alg/src/stages/S*/contract.ts`) were not opened; PxC usage there is unverified.
- Whether the 145-branch sprawl hides a branch newer than 2026-09-23 that a `--depth 1` fetch did not surface; the listing used all refs under `refs/remotes`.
