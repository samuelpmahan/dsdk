## Latest
- Default branch: `main`. Latest commit: `5625972` on `origin/main`, 2026-09-28, "Add typed upload overlay and evidence-backed neat comparison".
- Other recent branch: `origin/codex/local-pages`, 2026-09-15, "Normalize captured test log whitespace for review" (older; 126 files differ from main, mostly deletions, so treat as stale).

## Purpose
PxCube is a "PxC hypervisor" that hosts small PxC apps ("Experiences"). Each app declares a `experience.json` manifest, addresses data only through mounts (`{MOUNT}.{px|fn|oc|sc}.*`), is built and sandboxed in its own frame, and is reviewed on one GitHub Pages launcher. It is a PxC/neat/tidy/crisp monorepo, and the DiscStudio "upload disc to shelf" workbench is one of its apps.

## Stack
- JavaScript ES modules (`.mjs`), Node 22/24 for CI and local runs; some TypeScript (`app.ts`, `*.test.ts`, `vendor/neat/src/*.ts`, compiled to `vendor/neat/dist/*.js`).
- GitHub Actions (`.github/workflows/experiences.yml`) as a thin wrapper over `crisp`.
- Test runner: Node's built-in `node:test` (used in ~41 files); a custom `crisp/test/run.mjs` self-test; browser tests with a local shim (`experiences/mock-smoke/shims/node-test.mjs`).
- No root `package.json`; only `vendor/neat/package.json` (`type: module`, private).

## Key modules
- `vendor/studio/part-first-kernel/src/pxc.mjs` — `Part` (frozen value with composition record) and `PxC` class; `compose({into, calculation, inputs})` runs a function-valued Part and records receipts.
- `vendor/neat/src/pxc.ts` — execution store: `Part`, `PartRead`/`PartWrite`, `CalculationInvocation`, `ExecutionTelemetry` (reads/writes/invocations/events), `calculationId` (must match `fn.*`).
- `vendor/neat/src/pql.ts` — PQL: `part(address)` references and composition of Ticks/Calculations.
- `vendor/neat/src/pcr.ts` — PCR (`definePcr`, `TickDeclaration`, `composePcr`) over PQL run results.
- `vendor/neat/src/board.ts` — builds the Markdown/Mermaid board from one PxC/PQL run; derives shared-Calculation fanout from `Ticks[].Calculations[]`.
- `local/pxc-kernel.mjs` — shell-owned kernel: per-key retained state (`schemaVersion: 1`), mounts `mock.<id>[.<n>]`, scratch writes (`sc.*`), change log, guarded commit against other owners, recorded results.
- `kompoze/typed-overlay.mjs` — `resolveTypedOverlay`: base + type-provider identity, JSON merge patches, forbids patches that change id/version/tidy/composition.
- `spec/manifest.md` — the app manifest contract (fields, sandbox model, registration, failure semantics).
- `launcher/shell.mjs`, `launcher/build-launcher.mjs` — Pages launcher shell and generator (path only; not opened).
- `crisp/lib/packager.mjs`, `crisp/lib/verifier.mjs` — build/package/verify pipeline per spec/README; not opened.
- `tidy/lib/registry.mjs` — tidy registry, per README (apps, milestones, tests); not opened.
- `vendor/studio/upload-disc-to-shelf/README.md` — DiscStudio upload/shelf slice on the PxC store (opened); `persistence.ts`/`operations.ts` exist but were not opened.
- `local/studio-demo/compositions.mjs`, `local/studio-demo/model.mjs` — studio demo composition model (path only; not opened).
- `docs/cartridges.md` — listed under docs; not opened.

## Reusable for dsdk
- B1 — `vendor/studio/part-first-kernel/src/pxc.mjs` — minimal, frozen `Part` + `PxC.compose` that records each composition and receipt; a good seed for provenance-carrying values in dsdk.
- B1 — `vendor/neat/src/pxc.ts` — typed execution telemetry (reads/writes/invocations as a total-ordered event list); fits reproducibility receipts.
- B3 — `vendor/neat/src/pql.ts` — declarative `part(address)` references kept as data, not a DSL string; relevant to the typed expression language (A2) and typed contracts (D3).
- D3 — `kompoze/typed-overlay.mjs` — identity-preserving overlay/merge with explicit forbidden keys; a compact pattern for typed composition.
- B1 — `local/pxc-kernel.mjs` — guarded commit (refuses writes if another owner changed storage), quota-safe write ordering, and iteration-numbered runs for replay.
- D2 — `vendor/neat/src/board.ts` — derives shared-Calculation impact from composition records; fits an impact/fanout report.

## PxC / provenance concepts
- Addressed values: `{MOUNT}.{px|fn|oc|sc}.*` addresses; the mount prefix is resolved at the seam and not persisted (`local/pxc-kernel.mjs`, `README.md`). Literal-key dotted addresses; `readPart` raises `MissingPartError` for unknown addresses.
- Calculations: `fn.*` identities (`calculationId` in `vendor/neat/src/pxc.ts`); function-valued Parts in `part-first-kernel`; `oc.*` for effectful calculations (per README).
- Ticks / compositions: PQL `Ticks[]` with `Calculations[]` (`vendor/neat/src/board.ts`, `pcr.ts`). A `tick-part-checklist` web component (`vendor/neat/tick-part-checklist.js`) records human inspection per tick part, kept separate from acceptance.
- Provenance / lineage: each `Part` carries its `composition` (calculation + input bindings); `PxC.receipts()` records `produced`/`failed` with the composition. Typed overlays record `composition.base`, `resolvedType`, and `baseManifestSource` (`kompoze/typed-overlay.mjs`). Run telemetry is in `ExecutionTelemetry`.
- Ticks (checkpoint-style) and PCR ids: `.neat/items/*.json` targets a `fn.*`, `tick.*`, or `pcr.*` (`vendor/neat/README.md`).

## Evidence quality
- Test files on `main` (excluding `evidence/`): 41 `.test.mjs`/`.test.ts` files, plus browser harnesses under `local/test/` (e.g. `browser.mjs`, `*-browser.mjs`). I did not count the harness scripts.
- `evidence/` holds ~84 committed artifacts (browser-results JSON, unit/test logs, packaging reports), for example `evidence/local-pages/tests.log`, `evidence/demo-experiences-m/unit-results.txt`, `evidence/ntc-console/unit.txt`. Not verified by me.
- I did not run any tests or builds (read-only survey).
- CI runs `crisp/test/run.mjs` first, and browser coverage runs in a separate non-blocking job (`.github/workflows/experiences.yml`).

## Open questions
- Whether `local/pxc-kernel.mjs`'s `oc.*` (effectful) path is implemented or only `fn.*`/`px.*`/`sc.*` are used in practice; I did not open the full `local/` runner.
- Exact relationship between `vendor/studio/part-first-kernel` and `vendor/neat/src/pxc.ts` (two PxC implementations: one class-based, one functional). Not confirmed which is canonical.
- What "Tick" means in full (checkpoint vs. calculation grouping) beyond the board/PQL usage; `docs/` not read.
- Status of the older `codex/local-pages` branch: whether any of its unique content is still wanted.
- `vendor/studio/SOURCE.json` names "PnC (local integration repository)" at commit `6f7937b`; the relation to the `pnc` repo is not verified.
