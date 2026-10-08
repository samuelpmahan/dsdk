## Latest
- Newest branch: `origin/main` (HEAD), committed 2026-10-03 04:14 UTC, subject "Stoplight: never redeploy staging on its own; no reuse for Boone's battery".
- Default branch: `origin/main` (same commit). The only other branch is `origin/bootstrap-staging-deploy`, 2026-08-16, "Prepare staging workflow smoke test".

## Purpose
Staging repo for ChainSpot builds awaiting manual browser acceptance (per its README), plus a "lane stoplight" tool: a Claude Code plugin that runs tracked "crucible" tests per item and shows green/yellow/red. Main also holds an accepted S0–S7 plan (PLAN.md), September research notes, and two test batteries (Homeroom Heroes teacher rules, Boone's HH parity battery). The README says this repo should be infrastructure only; the contents are broader than that.

## Stack
- Node 22 with `node --experimental-strip-types` for TypeScript (no npm installs by design); the stoplight imports `node:` built-ins only.
- Test runner: `node --test` for `stoplight/stoplight.test.ts` and `stoplight/hh-di/teacher.test.ts`; Python for `stoplight/boone-hh/` (`test_infra/` package, `models/`, `batteries/hh_parity.py`).
- CI: GitHub Actions workflow `.github/workflows/deploy-reviewed-sha.yml` (workflow_dispatch with a ChainSpot SHA/ref, or push to main on `STAGE_REF` changes); publishes to GitHub Pages and runs the stoplight as a read-only job; Pages site at `/stoplight/`.
- Claude Code plugin wiring: `stoplight/.claude-plugin/plugin.json`, `stoplight/hooks/hooks.json`, skill `stoplight/skills/lane/SKILL.md`.

## Key modules
- `stoplight/stoplight.ts` — lights computed from crucible results on a PxC board: `fn.Crucible.run`, `fn.Crucible.fingerprint`, `fn.Stoplight.light`; green = all ran as expected, yellow = no crucible or could not run, red = ran and came out wrong.
- `stoplight/board.ts` — PxC board copied (per its header) from ChainSpot `lab/s0-viewer` `packages/alg/src/exec/board.ts`, with local stand-ins for one type import.
- `stoplight/run.ts` — runs every crucible in `items.json`, prints lights, writes `stoplight.json` and `index.html`; honours `STOPLIGHT_PREVIOUS` for delta reuse.
- `stoplight/page.ts` — turns the receipt into the one-page HTML view.
- `stoplight/items.json` — tracked items and their crucible commands; `expect: "fail"` marks adversarial copies that must be caught; `inputs` enables fingerprint reuse.
- `stoplight/stoplight.test.ts` — DI tests that inject results onto the board; `STOPLIGHT_IMPL=mutant` and `=stale` must turn red.
- `stoplight/hh-di/teacher.ts` and `stoplight/hh-di/teacher.test.ts` — Homeroom Heroes teacher steps as inject-then-run-one-step tests; `mutants.ts` and `pick-worker.ts` provide the mutant selection.
- `stoplight/boone-hh/test_infra/runner.py` and `stoplight/boone-hh/batteries/hh_parity.py` — Python parity battery (5 pinning tests, 4 intended-fix tests per README), with `models/hh_current.py` and `models/hh_fixed.py`.
- `stoplight/RULES.md` — session rules for the lane (no git, propose-not-apply, burst-and-check-back); these are instructions to Claude, not code.
- `PLAN.md` — accepted S0–S7 plan for "canonical image through numbered hole paths", with pathfinding composition steps.
- `research/2026-09-07/SYNTHESIS.md` — infrastructure synthesis (superseded in scope by PLAN.md, per its own banner).
- `.github/workflows/deploy-reviewed-sha.yml` — the staging deploy and the stoplight job.

## Reusable for dsdk
- B3 — `stoplight/stoplight.ts` — verdict model that treats "could not run" as yellow, never green, and requires broken copies to be caught; a clean pattern for verification receipts.
- B3 — `stoplight/items.json` + `stoplight/stoplight.test.ts` — adversarial-copy crucibles (`expect: "fail"`) and mutant-injection env vars as a way to prove a checker actually discriminates.
- B1 — `stoplight/stoplight.ts` (`fn.Crucible.fingerprint`) — reuse key covering runtime version, command, expected result and every declared input file's contents; results that could not run are never reused.
- B3 — `stoplight/hh-di/teacher.test.ts` — inject-state-then-run-one-step test pattern with live-bug mutants (`HH_IMPL=mutantA|B|C`) as a spec for a rewrite.
- B2 — `stoplight/boone-hh/` — externally written parity battery pinned to a commit of the reference source, run against intended-fix and current-behavior tests.
- D3 — `PLAN.md` (S0–S7 table) — explicit handoff contract per stage (public output and unresolved-result shape).
- A5 — `PLAN.md` "Pathfinding composition" section (support field to traversal cost to bucket-queue search over a graph) — separates support, occlusion, cost, search and assessment as distinct calculations with a bounded re-evaluation rule.

## PxC / provenance concepts
- Yes, in the stoplight: addressed PxC values and calculations (`fn.Crucible.run`, `fn.Crucible.fingerprint`, `fn.Stoplight.light`) on a copied board; reuse of results keyed by a fingerprint of inputs.
- The stoplight's board is a copy of the ChainSpot PxC board, so the concept matches the chainspot repo's `exec/board.ts`, but the copies are not synced.
- `PLAN.md` and `research/2026-09-07/SYNTHESIS.md` describe the intended calculation/invocation records (parent/item occurrence records, publication, selected-board handoff) as design, not as code in this repo.
- No Tick or lineage implementation in this repo beyond the stoplight board.

## Evidence quality
- Test files: `stoplight/stoplight.test.ts`, `stoplight/hh-di/teacher.test.ts`, plus the Python `boone-hh` package (`test_infra/`, `batteries/`, `demo.py`); plus `stoplight/hh-di/mutants.ts` and `pick-worker.ts` as support.
- `stoplight/README.md` records a "Last full run" on 2026-10-02 (4 green, 1 red, 4 yellow) in Claude's container; that run is claimed by the README, not reproduced here.
- Nothing was run for this survey. No deploy, no tests, no installs; only `git fetch` and `git show`/`ls-tree`.
- `stoplight/hh-di/RESULTS.md` and `stoplight/boone-hh/SETUP-RECIPE.md` exist but were not read.

## Open questions
- The README says staging should hold only deployment infrastructure, yet main contains PLAN.md, research notes, the stoplight, and test batteries. Which of these should live here? Not decided in the repo.
- The stoplight README says the nctk trees (`trees/accepted-head`, `trees/candidate-05-06`) are needed for three items; they are not in this repo, so those items show yellow here.
- `stoplight/README.md` refers to a Drive folder and `samuelpmahan/ChainSpot-staging`; the Drive lane rules (RULES.md) forbid git and say to write only in a Drive folder. How that squares with a GitHub repo is unclear.
- Whether the staging deploy workflow has ever run successfully: `.github/workflows/deploy-reviewed-sha.yml` was read only in part.
- `stoplight/board.ts` is a copy; whether it has drifted from ChainSpot's board was not checked.
- The `bootstrap-staging-deploy` branch (2026-08-16) was not inspected.
