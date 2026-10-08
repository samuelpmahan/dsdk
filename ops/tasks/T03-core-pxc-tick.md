# T03-core-pxc-tick

**Goal.** Implement `PxC.tick` and `TickScope` (compose/get/has) in `src/dsdk/core/pxc.py`: staging, isolation, atomic commit, rollback receipts, closed-scope errors.

**Files to edit.** `src/dsdk/core/pxc.py` only. Do NOT edit any file under `tests/`, `fixtures/`, `tracks.toml`, or other tasks' functions. Stub signatures and docstrings are the spec: read them before coding.

**Done when.** `uv run pytest tests/core -q  (tick tests alone: uv run pytest tests/core/test_pxc.py -q -k tick)` passes (exit 0). Also keep previously finished tasks green: `uv run pytest -q` must not regress anything you did not own.

**Depends on.** T02

**Pitfalls.**
- Reuse T02's compose logic (refactor into a helper taking an optional scope) rather than duplicating; do not break T02's tests.
- Receipts for a tick are appended only when the tick EXITS, in attempt order. During the tick `store.receipts()` and `entries()` show committed state only.
- Attempt records: produced-ok, own-failure (calculation raised or fn rule violated, error = own exception), caught failures stay recorded. On rollback successful attempts become FAILED with `error` = the exception leaving the block and `output=None`; own failures keep their own error.
- A staged address counts as occupied inside the tick (AddressOccupiedError) but a FAILED compose stages nothing (the address is free to retry).
- `with` entry validates `id` (TypeError/ValueError) and must not leave the store 'open'. Use try/finally so the open flag is cleared on every exit path, and mark the scope dead (all methods raise `TickInProgressError`).
- Catch `BaseException` for rollback, then re-raise the SAME object (`raise`).
- While open, store.set / compose / tick raise `TickInProgressError`; get/has/entries/receipts keep working.

**Rules.** Remove `raise NotImplementedError` only in the functions this task owns. Keep docstrings. No new dependencies. 2 attempts total.
