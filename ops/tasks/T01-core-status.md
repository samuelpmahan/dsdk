# T01-core-status

**Goal.** Implement `Judgment.__post_init__` in `src/dsdk/core/status.py` (Status enum is already complete).

**Files to edit.** `src/dsdk/core/status.py` only. Do NOT edit any file under `tests/`, `fixtures/`, `tracks.toml`, or other tasks' functions. Stub signatures and docstrings are the spec: read them before coding.

**Done when.** `uv run pytest tests/core/test_status.py -q` passes (exit 0). Also keep previously finished tasks green: `uv run pytest -q` must not regress anything you did not own.

**Depends on.** none

**Pitfalls.**
- Rule order does not matter for tests, but each violation must raise the documented type (TypeError for wrong types, ValueError for bad combinations).
- `True` is an `int`, not a `Status`: use `isinstance(self.status, Status)`.
- KNOWN forbids only `None`: `if value is None`, never `if not value`.
- INVALID reason must be non-blank after `.strip()`.
- Do not add fields or change the dataclass decorator; it must stay `frozen=True`.

**Rules.** Remove `raise NotImplementedError` only in the functions this task owns. Keep docstrings. No new dependencies. 2 attempts total.
