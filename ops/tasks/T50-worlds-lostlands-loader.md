# T50-worlds-lostlands-loader

**Goal.** Implement the Lost Lands loader in `src/dsdk/worlds/lostlands.py`: `LostLands.track_artists`, `LostLands.track_label`, `LostLands.date_label`, `LostLands.sets`, `sha256_bytes`, `parse_lostlands`, `load_lostlands`, `check_transitions` (plus private helpers). NOT `describe_provenance` / `record_provenance` (task T51).

**Files to edit.** `src/dsdk/worlds/lostlands.py` only. Do NOT edit any file under `tests/`, `fixtures/`, `tracks.toml`, `tracks/`, `ops/`, or functions owned by other tasks. Read the module docstring (file format) and every stub docstring first: they are the spec, including exact error-message prefixes, check order and tie-breaks. Read `tests/worlds/test_worlds_lostlands.py` and `tests/worlds/toy_world.py` before coding.

**Done when.** `cd /home/user/dsdk && .venv/bin/python -m pytest tests/worlds/test_worlds_lostlands.py -q -k "not provenance"` passes (exit 0). Also `cd /home/user/dsdk && .venv/bin/python -m pytest tests/core tests/logic tests/graph tests/test_reuse.py -q` must stay green.

**Depends on.** none (dsdk.core and dsdk.graph already exist)

**Pitfalls.**
- Validation order in `parse_lostlands` is the spec (schema, missing keys, artists/dates, tracks, groups, selections, transitions, meta). The error type is ALWAYS `WorldError`: never let a `KeyError`, `TypeError` or `IndexError` escape for bad input (wrong row length, `None` document, string where a list belongs).
- `bool` is a subclass of `int` in Python: `isinstance(True, int)` is true, so reject bools explicitly everywhere an integer is required. A float such as `1.0` is also not an integer.
- Row errors must name the field and row, e.g. `tracks[2]`, `selections[9]`, `meta.tracks` (tests look for those substrings).
- IDs are list positions; dates are `-1` or an index into `dates`; decoded `-1` becomes `None`. `track_artists`/`track_label` must raise `IndexError` for negative ids (no wrap-around).
- `load_lostlands`: hash the RAW file bytes first and raise `IntegrityError` BEFORE gunzipping. `gzip.decompress` raises `OSError`/`EOFError`; wrap them as `WorldError("gzip: ...")`; invalid JSON/UTF-8 becomes `WorldError("json: ...")`. A missing file must stay `FileNotFoundError`. Compare digests case-insensitively.
- Copy the `meta` dict (the world must not alias the input). `sets()` keys are in first-appearance order and keep repeated tracks. `check_transitions` reasons are exact strings given in its docstring.
- The real corpus has 1,352 tracks; `pytest` runs the 217-test file in about 30 s total; the hang guard allows 60 s per test.

**Rules.** Use ONLY file reading/editing and Bash for pytest. Never create sessions, triggers, agents or remote resources. Do not run git commands that change state. Remove `raise NotImplementedError` only in the functions this task owns. Keep docstrings and the existing imports. Standard library only. Public API of `dsdk.core` / `dsdk.logic` only. 2 attempts total.
