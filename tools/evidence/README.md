# Evidence pipeline

Every track ships a machine-produced packet plus browser captures in `tracks/<T>/evidence/`.
A person reviews the evidence; nobody hand-writes it.

    tools/evidence/run.sh A1      # build -> capture -> summary (about 8 s)

Steps (also runnable alone):

| Step | Command | Output |
|---|---|---|
| build | `uv run python tools/evidence/build_a1.py` | `tracks/A1/evidence/packet.json` (schema-validated) |
| capture | `node viewer/capture.mjs A1` | `a1-*.png`, `capture.json`; exit code 1 if any assertion fails |
| view by hand | `python3 -m http.server -d . 8000`, open `/viewer/index.html?packet=../tracks/A1/evidence/packet.json` | |

Requirements: Python via `uv run`, Node 22, global Playwright (`/opt/node22/lib/node_modules/playwright`, override with
`PLAYWRIGHT_MODULE`) and Chromium from `PLAYWRIGHT_BROWSERS_PATH`. Nothing is installed.

## Files

- `tools/evidence/schema.json`: packet schema. Generic sections (question, input snapshot, implementation contract,
  oracle, run record, browser artifact, result) are strict; `panels` is free-form per track.
- `tools/evidence/common.py`: git facts, pytest runner, sha256, timestamp, and a small hand-written JSON-Schema validator
  (`validate_packet`). `jsonschema` is not a dependency.
- `tools/evidence/build_<track>.py`: runs the track's code and writes the packet.
- `viewer/index.html`: generic shell. It loads `?packet=`, imports `viewer/<track>.mjs`, and draws the Summary view, view
  buttons, cross-check counter, provenance footer and download link.
- `viewer/ui.mjs`: `h()`, `table()`, and `CrossCheck` (counts agree/disagree marks).
- `viewer/<track>.mjs`: the track panel. **Recomputes** every value with independent JS and marks agree/disagree.
- `viewer/checks/<track>.mjs`: the track's browser assertions and screenshot plan.
- `viewer/capture.mjs`: generic runner: static server, Chromium, keyboard checks, zero-disagree check, tamper control,
  `capture.json`.

## Extension recipe (A2, A5, ...)

1. **Build script** `tools/evidence/build_a2.py`. Import `common`; run the real `dsdk.lang` code; fill every packet section
   (copy the section list from `build_a1.py`). Put recomputable data in `panels.<name>`: store the *inputs* in a form JS can
   read (structures, not just strings) plus the Python *outputs*. Give the oracle at least one deliberate failure
   (a mutant or an invalid case that must fail) and fail the build if it does not. Call `common.validate_packet(packet)`
   and write `tracks/A2/evidence/packet.json`. Exit non-zero on any problem. Hash the code and fixtures
   (`common.sha256_file`) because the working tree may be dirty.
2. **Panel** `viewer/a2.mjs`: `export function views(packet, { xc }) { return [{ id, label, node }, ...]; }`.
   For each Python value, compute the JS value from the *inputs* and call `xc.mark(pyValue, jsValue)`; put the returned
   node in a table cell. Use `table(caption, headers, rows)` for semantic tables, state each result in a sentence, and give
   interactive elements real labels. Import earlier JS kernels (e.g. `./parity/logic.mjs`); if the JS kernel does not exist,
   write one: the JS side must not read Python's answers. Give anything a test must find a stable `id` or `data-*`.
   For A5 (graph over Part lineage) the JS side should be an independent BFS/topological sort over the packet's edge list.
3. **Browser checks** `viewer/checks/a2.mjs`: `export async function run({ page, assert, shot, openView })`.
   Assert specific numbers and verdicts from DOM text, not just "no errors". `openView(id)` uses the keyboard. Call
   `shot('a2-<view>.png')` for each view (full page).
4. **Run** `tools/evidence/run.sh A2` (it looks for `build_a2.py`, `viewer/checks/a2.mjs`, `viewer/a2.mjs`).
5. The tamper control in `capture.mjs` currently flips the first row of `panels.truth_tables`. For a new track make that
   hook generic (for example `panels.<first key>`), or add a `tamper` export to `viewer/checks/<track>.mjs`. Do this before
   relying on the negative control for A2/A5.
6. Update `ROADMAP.md` board state to "Evidence ready" only when `capture.json` has `"ok": true`.

## Conventions

- Verdict vocabulary: `supported`, `weakened`, `unresolved`, `outside_scope`.
- Agree/disagree is shown as a word, never colour alone.
- Executed checks are labelled as such; proofs live in `tracks/<T>/PROOFS.md`.
- `run_record.working_tree_dirty` is recorded; the code file hashes identify the exact code. Re-run after committing
  to get a clean sha.
