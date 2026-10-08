# T02-core-pxc-parts-and-store

**Goal.** Implement `Part`, `PxC.__init__/set/get/has/entries/receipts/compose` in `src/dsdk/core/pxc.py` (NOT `tick` / `TickScope`: that is T03). Includes address validation, write-once, capture (deep copy except callables), `Composition` with a read-only `inputs` mapping, preflight order, receipts for produced/failed composes, and the in-flight pending set.

**Files to edit.** `src/dsdk/core/pxc.py` only. Do NOT edit any file under `tests/`, `fixtures/`, `tracks.toml`, or other tasks' functions. Stub signatures and docstrings are the spec: read them before coding.

**Done when.** `uv run pytest tests/core/test_pxc.py -q -k "not tick"` passes (exit 0). Also keep previously finished tasks green: `uv run pytest -q` must not regress anything you did not own.

**Depends on.** none (T01 is unrelated)

**Pitfalls.**
- Read the module docstring and `PxC.compose` docstring: the preflight ORDER and the "no receipt on preflight failure" rule are tested.
- `Part` must reject attribute assignment (`AttributeError`): use `__slots__` + `__setattr__` raising, set via `object.__setattr__`. Equality stays identity (do NOT make it a dataclass with eq).
- Callables (`callable(v)`) are stored and returned BY REFERENCE; everything else is `copy.deepcopy`'d on construction AND on every `.value`.
- A composed Part's composition is attached by the store, not by the user constructor: keep `Part(value)` public signature unchanged.
- `Composition.inputs` must be `types.MappingProxyType` over a NEW dict (callers mutating their dict afterwards must not matter); keep caller's order.
- Address regex: `(px|fn|sc)\.` followed by at least one char; use `fullmatch` (a `$` anchor would accept a trailing newline). Non-str -> TypeError first.
- Reserve `into` in a pending set BEFORE running the calculation and release it in `finally` (re-entrancy test), and also catch failures of copying the output.
- `fn.*` output must be callable, checked AFTER running, as a failure with a FAILED receipt.
- In `compose`, the open-tick check (`TickInProgressError`) comes first, but you can leave tick state as an attribute that T03 will set; for now it is always False.
- `entries()` / `receipts()` return tuples (snapshots).

**Rules.** Remove `raise NotImplementedError` only in the functions this task owns. Keep docstrings. No new dependencies. 2 attempts total.
