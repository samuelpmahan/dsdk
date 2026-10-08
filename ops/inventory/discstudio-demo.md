## Latest
- Newest branch: `origin/courier/pxc-fg-deps-20261004`, 2026-10-05, commit `a4f54b5`: "courier: native test dependencies for FG operational adapter". It adds only two workflow files (`.github/workflows/pxc-native-courier.yml`, `.github/workflows/pxc-fg-dependency-courier.yml`, +110 lines). It is a dependency-bundling CI courier, not a product change.
- Default branch: `origin/main`, 2026-10-02, "DiscStudio 6.5.7: Photo intake 0.5.0 and Re-crop". This is the real product state; the courier branch sits on top of it.
- Other recent: `origin/stoplight-boone-hh` (2026-10-02, "Stoplight: add Boone's HH parity battery as crucibles", +2413 lines, 29 files) and `origin/stoplight-ci` (2026-10-02). Not inspected in depth.

## Purpose
DiscStudio demo is a static photo-to-card disc-golf demo for GitHub Pages. It handles photo intake, circle crop correction, mold details, a local bag, and PNG or ZIP export of cards. Its deployable source is `demo-scratch/new-ship/upload-disc-to-shelf`, which uses a copied PxC runtime (`part-first-kernel`) and a copied tick-checklist component.

## Stack
- TypeScript (`.ts`, run with `node --experimental-strip-types`) and plain ES modules (`.mjs`); `"type": "module"`.
- Canvas rendering: `@napi-rs/canvas` for native rendering (`package.json` dependency); `jszip` as a dev dependency for ZIP checks.
- Node 22.13+ (deploy uses Node 24, per README). Build: `node build.mjs`; serve: `node serve.mjs`.
- Test runner: Node built-in `node --test` (`npm test` → `test:tournament`; `npm run test:capture` for paired-capture tests).
- GitHub Pages deploy via `.github/workflows/deploy-pages.yml` (per README; not opened).

## Key modules
- `demo-scratch/new-ship/upload-disc-to-shelf/SOURCE_LINEAGE.md` — component-level provenance (what came from the received DiscStudio source, what is copied verbatim).
- `demo-scratch/new-ship/upload-disc-to-shelf/persistence.ts` — `storageKey` `discstudio.pxc.shelf.v1`, a photo data-URI regex, and a comment that `archive(state)` is an OnTop format (the function body was not opened).
- `demo-scratch/new-ship/upload-disc-to-shelf/model.ts` — the disc/shelf model over `Part`/`PxC` from `part-first-kernel/src/pxc.mjs`.
- `demo-scratch/new-ship/upload-disc-to-shelf/kompozition.ts` — the active overlay set (currently empty) and the `paintedDiscs` capability flag.
- `demo-scratch/new-ship/upload-disc-to-shelf/url-free-materializer.mjs` — builds the module graph and inlines it as blob modules for a single offline HTML (`builtModuleGraph`, `inlineBuiltHtml`, `installBlobModules`, `storageShim`).
- `demo-scratch/new-ship/upload-disc-to-shelf/card-renderer-core.ts` — shared SpotlightCard draw routines (ten routines, per lineage doc).
- `demo-scratch/new-ship/upload-disc-to-shelf/circle-fit.ts` and `circle-candidates.ts` — bounded CircleFit ring search and candidate selection (names only plus lineage doc; not opened).
- `demo-scratch/new-ship/upload-disc-to-shelf/zip.ts` — deterministic ZIP32 STORE helper (per lineage doc).
- `demo-scratch/new-ship/upload-disc-to-shelf/export-queue-core.ts` — preserves `discstudio-export` v1 manifest fields (per lineage doc).
- `demo-scratch/new-ship/part-first-kernel/src/pxc.mjs` — the same `Part`/`PxC` kernel as in pnc's `exp/part-first-kernel` (copied verbatim per the lineage doc; not diffed here).
- `demo-scratch/new-ship/upload-disc-to-shelf/candidate-evidence/candidate-receipt.mjs` — candidate receipt writer with its test.
- `demo-scratch/new-ship/upload-disc-to-shelf/approval-identity.ts` and `build-input-identity.mjs` / `build-output-identity.mjs` — identity hashes for approvals and builds (names only; not opened).
- `DEMO-STATUS.md` (repo root) — live checkpoint, what is verified, and the open limits (download completion unverified; no iPhone testing).

## Reusable for dsdk
- B1 — `demo-scratch/new-ship/upload-disc-to-shelf/persistence.ts` — a versioned archive (`archive`, OnTop format per its comment); the same lineage as pnc's `persistence.ts`, whose unsupported-material refusal I did observe.
- B1 — `demo-scratch/new-ship/upload-disc-to-shelf/url-free-materializer.mjs` — deterministic module-graph bundling with a cycle check, producing a single offline artifact; relevant to reproducible packaging.
- B1 — `demo-scratch/new-ship/upload-disc-to-shelf/candidate-evidence/candidate-receipt.mjs` — a receipt per candidate build (names; check before use).
- D3 — `demo-scratch/new-ship/upload-disc-to-shelf/kompozition.ts` — overlays as an explicit, frozen capability record. Small typed-composition pattern.
- B3 — `demo-scratch/new-ship/upload-disc-to-shelf/export-queue-core.ts` with `export-queue.test.ts` — manifest-versioned export contract with tests (names only).
- D2 — `demo-scratch/new-ship/upload-disc-to-shelf/zip.ts` — deterministic ZIP32 STORE output; byte-stable exports.

## PxC / provenance concepts
- Addressed values: the shelf is stored under `storageKey` `discstudio.pxc.shelf.v1` (`persistence.ts`); `model.ts` imports `Part` and `PxC`. The `ds.px.*` binding filter I saw is in pnc's copy of `persistence.ts`, not verified here.
- Calculations: not confirmed in this repo's files; pnc's `persistence.ts` keeps `fn.`/`oc.` entries as known functions.
- Lineage: pnc's `persistence.ts` (not this copy) walks `Part.composition` into nodes with `material`, `calculation` and `inputs` links. Whether this copy does the same is an open question.
- Ticks: the `tick-part-checklist` component is copied from pxcube's `vendor/neat/` (lineage doc); the lineage doc says its checkbox state is inspection only, not formal acceptance.
- Shared kernel: `Part` is frozen, `PxC` refuses occupied addresses (same as pnc `pxc.mjs`; I opened the pnc copy, not this one).

## Evidence quality
- Test files on main: 29 `*.test.ts`/`*.test.mjs` under `demo-scratch/new-ship/upload-disc-to-shelf`, plus `candidate-evidence/candidate-receipt.test.mjs`.
- `DEMO-STATUS.md` reports `npm test` (69 tests) and `npm run test:capture` (7 tests) passing, and cites GitHub Actions run `35537043916`. This is the owner's own report; I did not re-run or open that run.
- Not verified: browser flows (download completion, iPhone touch), per `DEMO-STATUS.md` limits.
- Fixture directory exists; `rimfit-v3/` and `candidate-evidence/` hold receipts and cross-review notes (not opened).
- I ran nothing; no `npm install`.

## Open questions
- Whether `demo-scratch/new-ship/part-first-kernel/src/pxc.mjs` matches pnc's `exp/part-first-kernel/src/pxc.mjs` byte-for-byte (lineage says "verbatim"; not checked).
- What the courier branch's workflows are for: "FG operational adapter" is not explained in the repo files I read. The workflow names say "dependency transport only".
- Whether the `stoplight-*` branches (Boone HH parity battery) relate to the staging repo's `boone/uds-live-label` work. Not checked.
- The `package.json` test script lists `session-storage.test.ts`, `rimfit-persistence.test.ts` and `photo-crop.test.ts`; I did not confirm these files exist (they were not in my first 90-file listing).
- `twc-hello-world` and `review/`, `checkpoint/`, `exp/` branches were not inspected.
