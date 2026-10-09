# T37-prob-transitions-model

**Goal.** Implement the next-track model in `src/dsdk/prob/transitions.py`: `NextTrackModel.outgoing`, `fit_next_track`, `model_from_graph`, `_row`, `next_track_distribution`, `top_next`.

**Files to edit.** `src/dsdk/prob/transitions.py`, only those functions/methods. Do NOT edit any file under `tests/`, `fixtures/`, `tracks.toml`, `tracks/`, `ops/`, or functions owned by other tasks. The docstrings in the stub files are the spec: read them first (module docstring, then each function), then the tests named in the done command.

**Done when.** `cd /home/user/dsdk && uv run pytest tests/prob/test_transitions_model.py -q` passes (exit 0). Then run `cd /home/user/dsdk && uv run pytest -q tests/core tests/logic tests/test_reuse.py` and confirm it still passes.

**Depends on.** T30 (`to_weight`).

**Pitfalls.**
- `fit_next_track`: for each item of `sequences` (it may be a generator: consume it once) raise `TypeError` if the item is a `str` or not a `collections.abc.Sequence` (a bare string would be read as characters). Collect tracks from all sequences plus `vocabulary`; every track must be `str` (TypeError) and non-empty (ValueError). `alpha = to_weight(alpha, "alpha")`. Count `(x, y)` for consecutive pairs INSIDE each sequence only (`zip(s, s[1:])`; never across two sequences). `tracks = tuple(sorted(set))`. Return `NextTrackModel(tracks, counts, alpha)` where `counts` is a plain dict of int counts (only observed pairs).
- `model_from_graph`: `TypeError` if `g` is not a `Graph`; `ValueError` if not `g.directed`; every node must be `str` (TypeError) and non-empty (ValueError). The vocabulary is `tuple(g.nodes)` IN THE GRAPH'S ORDER (do NOT sort). For each edge, skip it when `e.evidence is not Status.KNOWN and not include_uncertain`. Weight: `None` means 1; a `bool` is a TypeError; otherwise it must satisfy `float(w).is_integer()` and `w >= 1`, else ValueError; store `int(w)`. Self-loops count.
- `_row(model, track)` is the shared helper: if `track not in model.tracks` return `Judgment(Status.NOT_OBSERVED, None, ...)` (reason contains the track's repr). Else `out = model.outgoing(track)` and `denominator = out + model.alpha * len(model.tracks)`; if the denominator is 0 return `Judgment(Status.UNKNOWN, None, ...)` with "alpha is 0" in the reason (do NOT invent a uniform row). Otherwise return the list `[(model.counts.get((track, y), 0) + model.alpha) / denominator for y in model.tracks]` of Fractions.
- `next_track_distribution`: `TypeError` for a non-model or non-str track; if `_row` returned a Judgment return it; else `Judgment(Status.KNOWN, tuple(zip(model.tracks, row)), "")`. Alpha = 0 keeps the zero entries.
- `top_next(model, track, k)`: check `k` first (`bool`/non-int TypeError, `k < 1` ValueError), then get the distribution and return it unchanged if it is not KNOWN. Drop entries with probability 0, sort by `(-probability, canonical index)`, keep at most `k`.
- `NextTrackModel.outgoing(track)` sums the counts of pairs whose first element is `track` (0 for an unknown track; no error).

**Rules.** Use ONLY file reading/editing and Bash for pytest. Never create sessions, triggers, agents or remote resources. Do not run git commands that change state. Remove `raise NotImplementedError` only in the functions this task owns. Keep docstrings. No new dependencies. 2 attempts total.
