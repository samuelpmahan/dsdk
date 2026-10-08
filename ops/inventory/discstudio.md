## Latest
- Default branch `origin/main` and `origin/impl/pxc-studio-workbench` point to the same tree: commit `d5e324c`, 2026-09-07, "Keep the full course graphic inside the desktop viewport". No divergence between them.
- Other recent branches: none newer on this repo (only `main` and `impl/pxc-studio-workbench` were listed in the top 15 by commit date).

## Purpose
DiscStudio is a static comparison site (Vite + Svelte) that preserves two disc-studio explorations: Concept A (vanilla Creator workbench) and Concept B (Svelte rebuild), plus a provisional `/candidate/` route that merges B's shelf/Bags with A's transparent PNG course export. The candidate's battle and render logic runs as a PQL composition on a vendored ChainSpot PxC core. Its stated product plan is in `docs/MGM.md`, which says it does not claim implementation.

## Stack
- JavaScript (`.js`/`.mjs`), TypeScript (`.ts`, e.g. `source/candidate-bags/model.ts`, `source/disc-studio/model.ts`), Svelte 5 components (`.svelte`).
- Build: Vite 7 with `@sveltejs/vite-plugin-svelte` (`package.json`); `yaml@2.9.0` for PQL parsing.
- Deployment: GitHub Pages workflow (`.github/workflows/deploy-pages.yml`), Node 22, `npm ci && npm run smoke`.
- Test runner: Node built-in `node:test` (`tests/**/*.test.mjs`) plus `scripts/smoke.mjs` and `source/concept-b/smoke.mjs`.

## Key modules
- `source/candidate-pxc/index.js` — barrel for the candidate PxC/PQL layer; the tests import from it (file not opened).
- `source/candidate-pxc/composition.js` — verbatim ChainSpot `BADGE_ASSEMBLY_PQL` (S1 badge assembly, Ticks/Calculations) and the Badge composition.
- `source/candidate-pxc/candidate-battle.js` — `CANDIDATE_BATTLE_PQL` (ResolveSnapshot, RenderOverlay, MaterializeOverlay ticks) and `runCandidateBattle` with a one-entry cache keyed by shelf and semantic snapshot Parts.
- `source/candidate-pxc/pql.js` — wraps the vendored ChainSpot `invokePql` and attaches run identity and telemetry at the PxC call boundary.
- `source/candidate-pxc/chainspot/exec.js` — vendored ESM transcription of ChainSpot's `board`/`pql` exec (`createExecBoard`, `pxKey`, `pxFn`).
- `source/candidate-pxc/board.js` — `deepFreeze` and an immutable-Part adapter around the vendored core.
- `source/candidate-pxc/materialize.js` — `materializeBattleState`: deterministic projection of a run to a `battle-state@2` Part.
- `source/candidate-bags/model.ts` — Bag model (file not opened; its contract is stated in `docs/candidate-mybag-handoff.md`: Bags reference physical shelf `Disc.id`s and never clone a disc).
- `source/candidate-bags/DiscShelfPage.svelte` — the DiscShelf/MyBag first page (path only; not opened).
- `source/candidate-ui/OnTheCourse.svelte`, `CandidateStudio.svelte` — On the Course page per the handoff doc (path only; not opened).
- `source/candidate-adapter/renderer.js` — candidate renderer adapter (path only; not opened).
- `public/shared/tick-part-checklist.js` — shared Tick/Part review checklist web component; a same-named file exists in pxcube (`vendor/neat/tick-part-checklist.js`), not compared.
- `docs/candidate-mybag-handoff.md` — domain and view contract for the candidate.

## Reusable for dsdk
- B3 — `source/candidate-pxc/chainspot/exec.js` — minimal browser PxC executor with `get`/`set`/`call` access recording and a `register` that refuses duplicate calculation addresses; a reference for parity testing against a second implementation.
- B1 — `source/candidate-pxc/candidate-battle.js` — explicit cache-key rule (shelf and semantic snapshot Parts only; presentation args excluded), with a `cache` record reporting hit/computed/reused Parts; a model for memoization that stays honest about what it reused.
- B1 — `source/candidate-pxc/materialize.js` — the render input is a deterministic Part with `identity` (queryId, sourceId, executionId); fits reproducible artifact records.
- D3 — `docs/candidate-mybag-handoff.md` (domain contract for `source/candidate-bags/model.ts`) — membership stores references, missing references must fail at the model boundary; a clear typed-reference contract.
- D2 — `source/candidate-pxc/board.js` `deepFreeze` plus `candidate-battle.js` cache — a cheap immutable-snapshot technique; the cache reports which Parts were reused (no timings measured).
- B3 — `tests/candidate-pxc/core-contract.test.mjs` — checks telemetry order and PQL-to-PxC correspondence; a template for a parity battery.

## PxC / provenance concepts
- Addressed values: `px.candidate.battle.part.*` and `px.s1.exp.*` address-style keys (`candidate-battle.js`, `composition.js`), with `pxKey`/`pxFn` wrappers in the vendored exec.
- Calculations: `fn.*` identities (`fn.candidate.battle.resolveEntries`, `fn.s1.exp.maskComponents.selectHsvMask`), registered on the board before invocation (`chainspot/exec.js` `register`/`call`).
- Ticks: PQL `Ticks[]` with ordered `Calculations[]`, each step `call` / `with` / `args` / `into` (`composition.js`, `candidate-battle.js`).
- Telemetry and lineage: `pql.js` records `get`, `call`, `set` events at the boundary and `assertPqlCorrespondence` checks them (`core-contract.test.mjs` imports it).
- Run identity: `queryId`, `sourceId`, `executionId` on the run and the `battle-state@2` Part (`materialize.js`).
- Immutability: Parts are frozen via `deepFreeze`; PNG export evidence is excluded from the semantic cache key by design.

## Evidence quality
- Test files: 6 under `tests/` (`candidate-adapter/renderer`, `candidate-bags/model`, `candidate-course/snapshot-renderer`, `candidate-pxc/candidate-battle`, `candidate-pxc/contract`, `candidate-pxc/core-contract`), plus 2 smoke scripts (`scripts/smoke.mjs`, `source/concept-b/smoke.mjs`).
- The Pages workflow runs `npm run smoke` (build + artifact routing check) before deploy. Smoke checks that built routing files exist; it does not run the `node:test` suite (not verified from the workflow file, which I read only up to `upload-pages-artifact`).
- I did not run any tests or builds (read-only survey, and the instructions forbid npm install).
- `docs/MGM.md` shows its checklist items unchecked, so the status of the delivery is not established.

## Open questions
- Whether CI runs `node --test tests/**` at all: the workflow I read does not show it, and `package.json` has no `test` script.
- Whether `source/candidate-pxc/board.js` `createPxC` matches the newer `pnc`/`pxcube` Part store, or only mirrors ChainSpot's exec board. Not compared.
- Whether `public/concept-a` Creator workbench persistence still works in browsers (not run).
- Provenance pins: `README.md` cites ChainSpot commits (`f0820e0`, `1bc41b2`, `82f8fc9`). I did not verify these exist in any local repo.
- `source/candidate-ui/OnTheCourse.svelte` details and the export renderer under `source/candidate/` were not opened.
