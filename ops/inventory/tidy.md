## Latest
- Branch `main` (only remote branch on disk). Last commit 2026-09-07, Samuel Mahan: "Publish standalone Tidy with promotion and build Action".

## Purpose
A tiny, portable Node guard for structured lineage in one working tree. It checks `.tidy/manifest.json` lineage boundaries, version progression, and relevant tests. Git owns history, and `tidy promote` is gated on Sam's explicit `--by-sam` words.

## Stack
A single-file Node executable `tidy` with no package install, `hooks/pre-commit`, `package.json`, and `node --test` tests in `test/tidy.test.js`.

## Key modules
- `/home/user/samuelpmahan/tidy/tidy` — the executable: check, verify, and promote commands.
- `/home/user/samuelpmahan/tidy/docs/TIDY.md` — command contract.
- `/home/user/samuelpmahan/tidy/examples/.tidy/manifest.json` — example manifest.
- `/home/user/samuelpmahan/tidy/hooks/pre-commit` — pre-commit hook.
- `/home/user/samuelpmahan/tidy/test/tidy.test.js` — tests.

## Reusable for dsdk
- B1 — `/home/user/samuelpmahan/tidy/tidy` — milestone freezing: version, clean tree, and content hash, with a `pre-baseline` state that reports nothing to verify. A reproducibility checkpoint pattern.

## Evidence quality
- Medium. Tests exist but were not executed here. The `neat` ledger notes that the DS-DEMO milestone is still `pre-baseline`, so no frozen baseline exists yet.

## Open questions
- The commit subject says "build Action", but no workflow file is tracked in this clone. Is it missing or untracked?
- `neat` has its own `tidy/` copy. Which is canonical, and do they drift?
