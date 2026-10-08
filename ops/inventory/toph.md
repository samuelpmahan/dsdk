## Latest
- Newest remote branch is `origin/claude/toph-viewer-usability-audit-4e2soi`, last commit 2026-08-18, Claude: "fix(viewer): define COLOR.dim for KEEP badge; make selectRun failure-safe". The remote has 10 branches, and the earlier "only branch" note was wrong.
- Other same-period branches: `origin/claude/toph-counterfactual-debugger-27h9v5` and `origin/codex/query-semantics-hardening` (2026-08-17), and `origin/adversarial/family-scoped-first-loss` (2026-08-17, the PR #2 source).

## Purpose
Toph is a TypeScript observability library, "Chrome DevTools for a classical CV pipeline", that compiles annotated filter stages with trace hooks so you can see why a stage kept or rejected an object. Its evidence comes from ChainSpot tee-detection examples, the library is pre-alpha, and the design doc is explicitly grounded in one codebase. The newest branch adds a local trace viewer and an adversarial suite that records known gaps.

## Stack
TypeScript (ESM), Node >=22, built to `dist/` with exports for runtime, compiler, and a `toph` CLI bin. The viewer branch adds a server (`src/viewer/server.ts`) and static browser JS. Examples are JSON manifests, traces, source maps, and patch files.

## Key modules
- `/home/user/samuelpmahan/toph/src/compiler/directives.ts` — annotation directives that trace-compile filter stages.
- `/home/user/samuelpmahan/toph/src/runtime/index.ts` — runtime hooks the trace calls into (package main).
- `/home/user/samuelpmahan/toph/src/evaluation/compare.ts` — `compareValidationMetrics` over per-stage reached and kept counts, baseline vs candidate, with a comparison policy.
- `/home/user/samuelpmahan/toph/src/viewer/server.ts` (viewer branch) — local viewer server.
- `/home/user/samuelpmahan/toph/src/viewer/static/viewer.js` (viewer branch) — browser viewer; the latest commit fixes its KEEP badge and failure-safe run selection.
- `/home/user/samuelpmahan/toph/test/adversarial/13-known-gap-family-scoped-first-loss.test.ts` (viewer branch) — known-gap test.
- `/home/user/samuelpmahan/toph/test/adversarial/14-known-gap-repeated-stage-invocation-inflates-funnel.test.ts` (viewer branch) — known-gap test.
- `/home/user/samuelpmahan/toph/EVALUATION.md` — self-critical eight-question review of the first run.

## Reusable for dsdk
- B3 — `/home/user/samuelpmahan/toph/src/evaluation/compare.ts` — baseline-vs-candidate comparison over per-stage counts; a verification-by-comparison pattern.
- B3 — `/home/user/samuelpmahan/toph/test/adversarial/14-known-gap-repeated-stage-invocation-inflates-funnel.test.ts` — pins a known failure as an explicit gap test rather than hiding it; a pattern for B3 verification.
- D3 — `/home/user/samuelpmahan/toph/src/compiler/directives.ts` — annotation-driven instrumentation that leaves stage outputs unchanged; a typed-contract idea.
- B1 — `/home/user/samuelpmahan/toph/examples/heritage-first-loss/manifest.json` — example run manifest with trace and source map; a provenance layout to copy.

## Evidence quality
- Medium. Examples are real run outputs for one domain. `EVALUATION.md` says broader instrumentation is not yet justified.
- The adversarial branches record Toph as VULNERABLE to two attacks: family-scoped first loss, and repeated stage invocation inflating the survival funnel. The viewer branch keeps both as known-gap tests, so the gaps are known and not fixed.
- Single-domain evidence with no cross-domain validation. Tests were not executed here.

## Open questions
- Are the two known gaps fixed on any branch? The viewer branch still names them as known gaps.
- The design doc cites `samuelpmahan/chainspot @ main`, which is not on disk, so its claims cannot be re-checked.
- Is `examples/chainspot-validation/workflow.yml` a live CI workflow or a sketch?
- Does `compare.ts` take ground truth (for example `truth.json`) or only stage counts? Not verified.
