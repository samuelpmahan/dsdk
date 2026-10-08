## Latest
- Default and newest branch: `origin/main`, committed 2026-08-25 15:33 -0500, subject "Add demo set and base Annotated set". 46 files tracked.
- Newer or equal-era branches: `origin/codex/lab-scope-validation` (2026-08-24, "Add LAB scope assisted/blind validation manifest"), `origin/research/fountain-hills-pr-run` and `origin/research/fountain-hills-renderer-study` (2026-08-18). `origin/Claude/handoff-refinement-test` also appears in the ref list.
- The annotation JSON files live on `codex/lab-scope-validation`, not on `main`. Main has the image blobs and zips only.

## Purpose
Private image corpus for ChainSpot: golf-course screenshot images (Git LFS), hole annotations (tee, basket, corridor per numbered hole), demo and sealed zip bundles, and gold-labelled validation sets. The LAB scope-validation manifest and Fountain Hills renderer studies are on side branches and read these images.

## Stack
- Git LFS for `*.png`, `*.PNG`, `*.jpg`, `*.JPG`, `*.jpeg` (`.gitattributes`); the shallow clone holds LFS pointer files (`version https://git-lfs.github.com/spec/v1`), not pixels.
- JSON annotation files (schemaVersion 1); zip bundles (`dev/Annotated.zip`, `demo.zip`, `sealed/*.zip`).
- Side-branch research code: TypeScript (`research/fountain_crop.ts`) and Python (`research/fountain_hills_study.part0.py`–`part2.py`) run from GitHub Actions workflows.
- No test runner in this repo.

## Key modules
- `.gitattributes` — LFS rule for image formats; the reason pixels are not in a shallow clone.
- `dev/Annotated/` (main) — per-course annotated sets: `AlexClark`, `DashsTrack`, `Heritage`, `Lenard`, `TowneLake` full-size images.
- `dev/Annotated.zip` (main) — zipped copy of the annotated set.
- `dev/<Course>/` (main) — raw dev images, e.g. `dev/Lenard/Lenard-1.PNG`–`-5.PNG` and `-full.PNG`.
- `demo/` (main) — `TheREC-McKinney-TX.jpg`, `TheRec-L.PNG`, `TheRec-R.PNG`, `TheRec-Thrown-full.PNG`.
- `sealed/` (main) — zipped sets `MiloMcIver`, `PatriotPark`, `WildernessRanch`, `Wondervu`.
- `validation/<Course>/clean/` (main) — `BeaverRanch-Gold`, `ColetoCreek`, `FountainHills`, `Seatac` clean images with lazy and full variants.
- `dev/Annotated/AlexClark/AlexClark-full.annotation.json` (codex/lab-scope-validation) — schemaVersion 1; `sourceImage` with sha256 and dimensions; `holes[]` with `number`, `tee`, `basket`, `corridorWidthPx`, `corridorBends`, `shots`.
- `dev/lab-scope-validation.json` (codex/lab-scope-validation) — `version: 1` manifest with `cases[]` (`dashs-assisted` with a hole-scoped view, `heritage-blind` with a box-scoped overview).
- `.github/workflows/fountain-hills-study.yml` (read from research/fountain-hills-pr-run; triggers on push to research/fountain-hills-renderer-study) — checks out with LFS, pulls, asserts the size and sha256 of `validation/FountainHills/clean/FountainHills-full.PNG`, then runs the study.
- `research/fountain_crop.ts` and `research/fountain_hills_study.part0.py`–`part2.py` (research/fountain-hills-pr-run) — study code; only the file list was read.

## Reusable for dsdk
- B2 — `dev/lab-scope-validation.json` (codex/lab-scope-validation) — assisted vs blind validation cases with explicit scopes; a concrete design for held-out evaluation.
- B1 — `dev/Annotated/AlexClark/AlexClark-full.annotation.json` (codex/lab-scope-validation) — annotation carries the source image's sha256 and dimensions, which pins labels to a specific pixel source.
- B1 — `.github/workflows/fountain-hills-study.yml` (read from research/fountain-hills-pr-run; triggers on push to research/fountain-hills-renderer-study) — pins an LFS object by byte size and sha256 before a study runs (file read from research/fountain-hills-pr-run); a reproducibility gate.
- D3 — annotation JSON schema v1 (codex branch) — typed fixture shape for hole/tee/basket geometry; usable as a contract example.
- B3 — `validation/<Course>/clean/` and `sealed/` layout (main) — separates gold-labelled validation material from sealed sets; whether `sealed/` is held out is not stated in the repo.

## PxC / provenance concepts
- Provenance is by content: annotation JSON stores the source sha256 and `bundlePath`; the fountain workflow checks sha256 before use.
- No PxC addresses, calculations, Ticks, or lineage are implemented here. Data only.

## Evidence quality
- No test files, no code under test on `main`.
- The fountain study workflow contains its own integrity check (size + sha256 on the LFS object) but that check was not run.
- Image contents were not verified: the shallow clone has LFS pointers only (e.g. `dev/Annotated/AlexClark/AlexClark-full.jpg` is 131 bytes, the pointer; the real blob is 792,940 bytes per the pointer's `size` line).
- Nothing was run for this survey; only `git fetch` and `git show`/`ls-tree`/`cat-file -s` were used.

## Open questions
- Why the annotation JSON files (10 of them) are on `codex/lab-scope-validation` and absent from `main` (main has `dev/Annotated/*.jpg` and `.png` but no `*.annotation.json`).
- Whether `sealed/` sets are held out from development or merely zipped; the repo does not say.
- Whether the Annotated sets on codex match the images on main (same sha256); not checked, since LFS blobs are not pulled.
- What `origin/Claude/handoff-refinement-test` contains (it appears in refs but was not inspected).
- The fountain research code (`research/*.py`, `research/fountain_crop.ts`) was not read beyond its file list.
- Whether `dev/lab-scope-validation.json` references images that exist on the codex branch (`Annotated/...` paths are relative to `dev/`).
