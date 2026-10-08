## Latest
- Newest branch: `origin/codex/bazel-pages`, 2026-10-07 14:18:58, commit `66c944e`: "Build PageRouter sources with Bazel and deploy through Pages Actions".
- Default branch: `origin/main` (`e86b9e7`), 2026-10-07, "Merge pull request #1 from samuelpmahan/codex/bazel-pages". Its tree is identical to `origin/codex/bazel-pages` (checked with `git diff --stat`, empty).
- Not imported: `origin/parallel-compressing-bootstrap` (2026-10-07 02:52, "Compile authoritative PageRouter source through pinned Bazel actions"). It differs from main by 2,222 files; main's `SOURCE.md` says its later application experiments are "not imported by this build change". Also `origin/rollback/pre-composed-workbench-20261002-5cc1ae3` (2026-09-28).

## Purpose
PageRouter is a static "Composed Workbench" site that combines PxCube experiences, an HH (Hall-of-Heroes style) C6 fixture, and Justin's static leaf in one browser-local app. Its newest feature is the PxCube Atlas tab (`#/pxcube/atlas`): it runs a pinned six-node motion/Beta recipe in JavaScript, exports a case for independent Python execution, imports the Python result, and compares declared observations through a PxC FunctionalGuarantee. It is a bounded candidate, and its README says it is not a human contract milestone.

## Stack
- JavaScript ES modules (`"type": "module"`), Node 24.19.0 (pinned); esbuild 0.28.2 and fast-check 4.10.2 as devDependencies (`checkpoint/package.json`).
- Python 3 for the Atlas cross-language CLI (`checkpoint/exp/atlas/cross_language.py`), a capability lab in `checkpoint/vendor/pxc-learning/` (`.py`), and browser QA scripts (`*_qa.py`).
- Build: Bazel 7.4.1 (`checkpoint/.bazelversion`, `checkpoint/ci/bazel/run.sh`, `site.bzl`), with `npm ci --ignore-scripts` for private build tools.
- Test runner: `node --test` over `exp/cooperative/*.test.mjs`, `exp/adversarial/*.test.mjs`, `exp/atlas/*.test.mjs`, `scripts/*.test.mjs` (`checkpoint/package.json` `test` script). Python tests (`test_*.py`) run separately (runner not determined).

## Key modules
- `checkpoint/src/app.mjs`, `checkpoint/src/atlas-view.mjs` — app shell and Atlas view (listed; not opened).
- `checkpoint/exp/atlas/calculations.mjs` — browser-native port of the Python atlas calculations: `canonical` (sorted-key JSON), `clone`, `fit_motion`, and a `calculationRegistry` with no dynamic code execution (opened, first ~40 lines).
- `checkpoint/exp/atlas/atlas-fg.mjs` — the six-node Atlas composition's declared FunctionalGuarantee: `contract` with `consumes`/`emits` per node and `sourcePorts` mapping `/parts/...` (opened, first ~30 lines).
- `checkpoint/exp/atlas/atlas-session.mjs`, `runtime-adapter.mjs` — session definition and `preflightRecipe` (imported by atlas-fg.mjs; not opened).
- `checkpoint/exp/atlas/cross-language.mjs` and `cross_language.py` — capture/compare of a case between JS and Python (`CROSS_LANGUAGE.md`, opened).
- `checkpoint/exp/cooperative/annotation-fg.mjs`, `fg-association.mjs` — `AnnotationFG.leaf` and `deriveFGAssociations` (imported by atlas-fg.mjs; not opened).
- `checkpoint/exp/cooperative/hh-workbench.mjs` — HH cooperative workbench (listed; not opened).
- `checkpoint/exp/adversarial/session-graph.test.mjs`, `project-router.test.mjs`, `static-compiler.test.mjs` — tests for the session graph, router and static compiler (names only).
- `checkpoint/src/project-router.mjs`, `static-compiler.mjs`, `local-store.mjs`, `session-repl.mjs`, `compiled-patch.mjs` — router, compiler, local storage, session REPL, compiled deltas (names only).
- `checkpoint/scripts/build-pxcube.mjs`, `preserve-pxcube.mjs`, `verify-crisp-delta.mjs` — PxCube build and delta verification (names only).
- `checkpoint/sources/pxcube/` — a 416-file copy of the PxCube source tree inside the checkpoint (listed; not diffed against the pxcube repo).
- `checkpoint/vendor/pxcube-checkpoint/`, `checkpoint/vendor/hh/`, `checkpoint/vendor/justin/`, `checkpoint/vendor/pxc-learning/` — pinned vendor snapshots (listed only).

## Reusable for dsdk
- B3 — `checkpoint/exp/atlas/cross-language.mjs` + `cross_language.py` + `CROSS_LANGUAGE.md` — capture a case in JS, recompute it in Python, compare declared observations; a concrete parity protocol, with `case_id` as a SHA-256 over inputs and bindings. Direct fit for B3 (Python/JS parity).
- D3 — `checkpoint/exp/atlas/atlas-fg.mjs` — a declared contract per node (`consumes`/`emits`) checked against the recipe before running (`preflightRecipe`). A typed-wiring pattern for D3.
- B1 — `checkpoint/exp/atlas/calculations.mjs` `canonical`/`clone` — stable key-sorted JSON used for hashing and replay identity. Fits B1 reproducibility.
- A3 / B2 — `checkpoint/exp/atlas/calculations.mjs` (`fit_motion`, Bernoulli-case assumption "conditionally independent Bernoulli cases with one shared pass probability") — a small, explicit probabilistic model with its assumption written in code (opened); useful for A3/B2 exercises.
- D1 — the `exp/adversarial` directory (hostile-import, cyclic-session, wrong-pin-session evidence) — test cases for rejecting bad inputs (names from evidence list).

## PxC / provenance concepts
- Addressed values: Atlas recipe addresses such as `/parts/training`, `/parts/config`, `/parts/prior` (`atlas-fg.mjs` `sourcePorts`); recipe output names like `motion-model`, `beta-posterior` (`atlas-fg.mjs` `contract`).
- Calculations: a `calculationRegistry` is "the only executable family" (`calculations.mjs`). The root README pins the Atlas implementation closure `b1cd98c6...` and HH evaluator `af0c2e0f...`.
- Functional guarantee: `AnnotationFG`-based leaves per recipe node, with a `preflightRecipe` check (`atlas-fg.mjs`).
- Cross-language provenance: `case_id` is a SHA-256 over the literal training rows, queries, observations, prior, policy, specification and optional implementation identity (`CROSS_LANGUAGE.md`).
- Session replay and cache: release notes mention "persistent-session replay/cache inspection", "exact-pin agent-readable graph/session export/import" (`package.json`); session code in `exp/atlas/atlas-session.mjs` (not opened).
- Execution path: `CROSS_LANGUAGE.md` says JavaScript runs the recipe through `AtlasRuntime` and HH `PxC.compose`. PxCube's neat/tidy/crisp lifecycle is copied under `sources/pxcube`. Tick-level detail not verified here.

## Evidence quality
- 121 test-like files under `checkpoint/` (includes vendored HH, Justin, PxCube copies), of which the `npm test` glob covers the cooperative, adversarial, atlas and script tests. Not counted exactly by runner.
- Committed evidence: `checkpoint/evidence/` (50 files) and `checkpoint/exp/adversarial/evidence/` (JSON receipts and screenshots, e.g. `browser-qa.json`, `reproducible-session.json`, `wrong-pin-session.json`). Not opened.
- Build verification is declared to run `npm test` against fresh output and check Atlas built imports (`checkpoint/README.md`); CI is a Bazel build on PRs and main.
- I did not run tests or Bazel (read-only survey).
- Main's `SOURCE.md` says the build does not claim human acceptance.

## Open questions
- Whether the Python `pxc-learning` capability lab is connected to the Atlas recipe or is an independent exploration (not determined).
- Whether `checkpoint/sources/pxcube` matches the current pxcube `main` (commit `5625972`). It was not compared.
- Whether `parallel-compressing-bootstrap` contains anything beyond the Bazel compile commit that main lacks; main's SOURCE.md says later experiments were not imported.
- The `SOURCE.md` figures (2,081 logical files; 709-file dist) were not checked against `SOURCE-ARCHIVE-MANIFEST.json`.
- Python test runner for `test_*.py` (pytest vs unittest) not determined.
- Whether the Drive-hosted source archive (SHA-256 `2d58add7...`) is reachable: not checked and not needed for this survey.
