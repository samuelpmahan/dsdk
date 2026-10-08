## Latest
- Newest remote branch is `origin/main`, last commit 2026-09-14, Sam Mahan: "Add Pages workflow: build, test, and deploy the checklist component".
- Two other remote branches were updated 2026-09-07, and the earlier claim that `impl/DiscStudio` was missing was wrong:
  - `origin/impl/DiscStudio`: "docs: add DiscStudio four-Tick mGM setup and local report". It adds `examples/discstudio/` (items DS-01 to DS-04, `mgm.json`, `facts.json`, `ready-view.html`). The commit says its source tree matches checkpoint db598714.
  - `origin/task/review-handoff`: "feat: add structured review handoffs and inspection checklist". It claims 17 passing tests and an export/import round trip, and marks browser visual inspection and live DiscStudio wiring as pending.

## Purpose
A repo-local JSON work ledger for agent-assisted work: one item per `.neat/items/<id>.json`, each targeting an existing PxC identity (`fn.*`, `tick.*`, or `pcr.*`). It offers guarded compare-and-update, derived boards, and a review handoff with an HTML checklist, and it never records human acceptance or Tidy promotion.

## Stack
TypeScript compiled by `tsc` to `dist/` (ESM, Node >=22), `node --test` for tests, only `@types/node` and `typescript` as dev dependencies. Output is Markdown and Mermaid; GitHub Pages hosts the checklist component.

## Key modules
- `/home/user/samuelpmahan/neat/src/pxc.ts` — pure in-memory Part/Calculation store; `calculationId` enforces the `fn.*` form and each operation returns a new value.
- `/home/user/samuelpmahan/neat/src/pql.ts` — PQL composition runner; exports `PqlRunResult` and `TickRunResult`.
- `/home/user/samuelpmahan/neat/src/pcr.ts` — PCR definition: id plus ordered Ticks, with empty and duplicate ID checks.
- `/home/user/samuelpmahan/neat/src/work-items.ts` — `workItemRevision` content fingerprint and pure `updateWorkItem` compare-and-update that rejects fabricated acceptance or execution testimony.
- `/home/user/samuelpmahan/neat/src/io.ts` — guarded file write; the README describes locking, reread, fingerprint check, then temp-file rename.
- `/home/user/samuelpmahan/neat/src/review-component.ts` — drop-in `tick-part-checklist` element.
- `/home/user/samuelpmahan/neat/NEAT.md` — ledger rules: spec-bound items, mGM gate, hard no-acceptance rule.
- `examples/discstudio/.neat/mgm.json` (branch `origin/impl/DiscStudio`) — four-Tick mGM targets for the DiscStudio example.

## Reusable for dsdk
- B1 — `/home/user/samuelpmahan/neat/src/work-items.ts` — content-fingerprinted compare-and-update so a stale write is refused; a pattern for append-only run records.
- D3 — `/home/user/samuelpmahan/neat/src/pxc.ts` — branded Calculation identities and pure Part operations; a typed-composition shape compatible with the `fn.*` naming convention.
- D3 — `/home/user/samuelpmahan/neat/src/pcr.ts` — PCR as an ordered Tick list with validation at definition time.

## Evidence quality
- Seven test files under `/home/user/samuelpmahan/neat/test/` (board, cli html, core pxc-pql-pcr, io guarded-update, report, review component and handoff). Not executed in this survey.
- The checked-in fixture `fixtures/generic-project` is labeled synthetic. The README says it proves no execution, human acceptance, or promotion for a real project.
- The DiscStudio branch states that it invents no execution, acceptance, or promotion facts. The review-handoff branch's "17 tests passed" claim is self-reported and was not reproduced.
- The ledger in NEAT.md is self-reported text. Its claimed CI result and record of a real bug were not verified here.

## Open questions
- Does `origin/task/review-handoff` supersede the review-handoff code on `main`, or have the two diverged? Not compared.
- Confirm that no acceptance is recorded for the DiscStudio items on `origin/impl/DiscStudio`.
- A `tidy/` directory is tracked inside neat, and a standalone `/home/user/samuelpmahan/tidy` repo also exists. Which copy is canonical?
- The README says PQL/PxCQL has no parser yet. Does dsdk's A2 expression language intend to adopt this syntax?
