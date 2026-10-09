# T38-prob-transitions-sampling

**Goal.** Implement `sample_next_tracks`, `compare_next_track` and `held_out_log_loss` in `src/dsdk/prob/transitions.py`.

**Files to edit.** `src/dsdk/prob/transitions.py`, only those three functions. Do NOT edit any file under `tests/`, `fixtures/`, `tracks.toml`, `tracks/`, `ops/`, or functions owned by other tasks. The docstrings in the stub files are the spec: read them first (module docstring, then each function), then the tests named in the done command.

**Done when.** `cd /home/user/dsdk && uv run pytest tests/prob/test_transitions_sampling.py -q` passes (exit 0). Then run `cd /home/user/dsdk && uv run pytest -q tests/core tests/logic tests/test_reuse.py` and confirm it still passes.

**Depends on.** T30, T34, T37.

**Pitfalls.**
- `sample_next_tracks`: get `d = next_track_distribution(model, track)`. If it is not KNOWN, FIRST validate the arguments by calling `inverse_cdf_draws([Fraction(1)], n, seed)` (so a bad `n`/`seed` still raises), then return `d`. Otherwise `picks = inverse_cdf_draws([p for _, p in d.value], n, seed)` and return `Judgment(Status.KNOWN, tuple(model.tracks[i] for i in picks), "")`.
- `compare_next_track(model, track, target, n, seed)`: `d = next_track_distribution(...)`; return it if not KNOWN. If `target not in model.tracks` return NOT_OBSERVED. `exact = dict(d.value)[target]`. Call `sample_next_tracks(model, track, n, seed)` (this validates `n`/`seed`). If `n == 0` return `Judgment(Status.UNKNOWN, None, ...)`. Else `hits` = number of draws equal to `target` and the answer is `Judgment(Status.KNOWN, make_comparison(exact, make_estimate(hits, n, n)), "")`.
- `held_out_log_loss(model, pairs)`: `TypeError` for a non-model; consume `pairs` into a list and check every element is a 2-tuple of `str` (TypeError; a list `["b", "c"]` is NOT a tuple). Empty -> UNKNOWN. Order of verdicts: first, if ANY element of ANY pair is outside `model.tracks` return NOT_OBSERVED (reason names the track); then compute probabilities: if the distribution of `x` is not KNOWN, or `P(y|x) == 0`, remember the pair and skip; if any such pair exists the answer is `Judgment(Status.INVALID, None, ...)` with "probability zero" in the reason (NEVER a large made-up number). Otherwise KNOWN with `-sum(math.log(float(p))) / len(pairs)` as a float (mean in nats).

**Rules.** Use ONLY file reading/editing and Bash for pytest. Never create sessions, triggers, agents or remote resources. Do not run git commands that change state. Remove `raise NotImplementedError` only in the functions this task owns. Keep docstrings. No new dependencies. 2 attempts total.
