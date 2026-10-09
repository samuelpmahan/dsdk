# T30-prob-exact-worlds-build

**Goal.** Implement exact number conversion and belief construction: `to_weight`, `to_prob` in `src/dsdk/prob/exact.py`; `WeightedWorld.__post_init__`, `WeightedWorld.assignment`, `Belief.__post_init__`, `Belief.total`, `Belief.mass` and `prior_belief` in `src/dsdk/prob/worlds.py`.

**Files to edit.** `src/dsdk/prob/exact.py` (both functions) and `src/dsdk/prob/worlds.py` (only the six functions/methods named in the goal). Do NOT edit any file under `tests/`, `fixtures/`, `tracks.toml`, `tracks/`, `ops/`, or functions owned by other tasks. The docstrings in the stub files are the spec: read them first (module docstring, then each function), then the tests named in the done command.

**Done when.** `cd /home/user/dsdk && uv run pytest tests/prob/test_exact.py tests/prob/test_worlds_build.py -q` passes (exit 0). Then run `cd /home/user/dsdk && uv run pytest -q tests/core tests/logic tests/test_reuse.py` and confirm it still passes.

**Depends on.** none (start here, in parallel with T34).

**Pitfalls.**
- Check order in `to_weight`: `bool` is a `TypeError` BEFORE the int check (`isinstance(True, int)` is true). Then `Fraction`, `int`, `float`. A float must be finite (`math.isfinite`, else `ValueError`) and is converted with `Fraction(repr(x))`, NEVER `Fraction(x)`: `0.2` must become exactly `1/5`. Anything else is a `TypeError`. A negative value is a `ValueError`. `to_prob` calls `to_weight` and then rejects `> 1`.
- `WeightedWorld.__post_init__` checks, in this order: `values` is a `tuple` (TypeError); every item is a 2-tuple whose first element is `str` and whose second element has `type(v) is bool` (so `1` is rejected, TypeError); names strictly increasing (ValueError); `weight` is a `Fraction` (TypeError; an `int` or `float` weight is rejected); `weight >= 0` (ValueError). The dataclass is frozen, so only read `self.values` / `self.weight`.
- `Belief.__post_init__`: `variables` is a tuple of `str` (TypeError), strictly increasing (ValueError); `worlds` is a tuple whose items are all `WeightedWorld` (TypeError); each world's names, in order, equal `variables` (ValueError). `Belief.total` is `sum((w.weight for w in self.worlds), Fraction(0))` so an empty belief gives a `Fraction`, not the int 0.
- `Belief.mass(f)`: `TypeError` if `f` is not a `Formula`; then `UnmodelledVariableError(tuple(sorted(missing)))` for variables of `f` (use `dsdk.logic.variables`) not in `self.variables`; then the sum of weights of worlds where `dsdk.logic.evaluate(f, world.assignment())` is true. The result starts from `Fraction(0)`.
- `prior_belief`: DO NOT re-implement the enumeration. Use `dsdk.logic.models(formula, over=names)` where `formula` is `Const(True)` when `constraint is None`, and `names = tuple(sorted(set(priors) | variables(formula)))`. Check `len(names) > MAX_VARIABLES` (ValueError) BEFORE calling `models`. Validate `priors` is a `Mapping` (TypeError), constraint is `None` or a `Formula` (TypeError), every prior key is `str` (TypeError), and convert each prior with `to_prob`. The weight of a model is the product, over variables that HAVE a prior, of `p` if the variable is true else `1 - p`; variables without a prior contribute 1. KEEP worlds whose weight is 0. Each world is `WeightedWorld(tuple((n, model[n]) for n in names), weight)`.
- `models` yields dicts keyed by exactly the sorted names; `priors` may be a dict whose iteration order is not sorted: never rely on it. Do not mutate the `priors` argument.

**Rules.** Use ONLY file reading/editing and Bash for pytest. Never create sessions, triggers, agents or remote resources. Do not run git commands that change state. Remove `raise NotImplementedError` only in the functions this task owns. Keep docstrings. No new dependencies. 2 attempts total.
