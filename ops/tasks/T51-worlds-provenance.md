# T51-worlds-provenance

**Goal.** Implement `describe_provenance` and `record_provenance` in `src/dsdk/worlds/lostlands.py` so the world's origin is recorded as dsdk.core Parts with real lineage.

**Files to edit.** `src/dsdk/worlds/lostlands.py` only; touch ONLY those two functions (the rest was done by T50). Do NOT edit any file under `tests/`, `fixtures/`, `tracks.toml`, `tracks/`, `ops/`. Read the `dsdk.core` module docstring in `src/dsdk/core/pxc.py` (write-once addresses, `PxC.set`, `PxC.compose`, string references) and the provenance tests.

**Done when.** `cd /home/user/dsdk && .venv/bin/python -m pytest tests/worlds/test_worlds_lostlands.py tests/worlds/test_worlds_self_reuse.py -q -k "not networks"` passes (exit 0). Also `cd /home/user/dsdk && .venv/bin/python -m pytest tests/core tests/logic tests/graph tests/test_reuse.py -q` must stay green.

**Depends on.** T50

**Pitfalls.**
- Order of writes matters (tests compare `store.entries()` order): sha256, commit, counts, then `fn.lostlands.describe`, then the composed `px.lostlands.provenance`.
- `Part` values are deep-copied; `Part(describe_provenance)` keeps the function BY REFERENCE (callables are not copied). The `fn.*` namespace requires a callable.
- Compose with string references: `store.compose("px.lostlands.provenance", "fn.lostlands.describe", {"sha256": "px.lostlands.source_sha256", "commit": "px.lostlands.source_commit", "counts": "px.lostlands.counts"})`; keep the input order sha256, commit, counts.
- The `counts` dict has exactly these keys in this order: corpus (from `world.meta.get("corpus", "")`), artists, tracks, selectorGroups, dates, selections, transitions, sets.
- Calling twice on one store must raise `AddressOccupiedError` from the FIRST `set` and leave the store unchanged: do not catch it and do not pre-check.
- The self-reuse test also needs `Part`, `PxC`, `Judgment`, `Status` to be genuinely used in `lostlands.py`; that is already true once these functions exist.

**Rules.** Use ONLY file reading/editing and Bash for pytest. Never create sessions, triggers, agents or remote resources. Do not run git commands that change state. Remove `raise NotImplementedError` only in the functions this task owns. Keep docstrings and the existing imports. Standard library only. Public API of `dsdk.core` / `dsdk.logic` only. 2 attempts total.
