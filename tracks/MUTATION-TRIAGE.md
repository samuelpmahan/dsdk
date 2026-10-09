# Planted-bug triage, first run on shipped code (2026-10-09)

The runs covered 420 planted bugs across the kernel, logic, language and graphs. 408 were caught and 12 slipped through. A person has read and classified every one of the 12.

**Six were not real changes.** The tool turned `return None` into `return None`. That was a bug in the tool, now fixed in tools/mutants/run.py.

**Three were harmless rewrites.** Nothing observable changes, so no test can or should catch them:
- **Graph model, undirected edges** (`src/dsdk/graph/model.py`, edge normalisation). Changing `index[u] > index[v]` to `>=` only differs when u equals v. That is a self-loop, and swapping u with itself does nothing.
- **Graph model, edge lookup** (`get_edge`). Changing "both endpoints exist" to "either exists" still returns None, because no stored edge can touch a missing node.
- **Relaxed formula parser** (`src/dsdk/lang/formula_syntax.py`, inside parentheses). Starting the inner expression at precedence 1 instead of 0 accepts exactly the same inputs, because the loosest operator (`<->`) has precedence 1. This was confirmed by parsing `(a <-> b)`, `~(a <-> b)` and `((a -> b) <-> c)`.

**Two were real test gaps, both now closed.** The new tests were confirmed by planting each bug back in and watching them fail:
- **Calc parse errors** (`src/dsdk/lang/calc.py`). The list of what may come next offered `let` and `if` after an operator, where they are not legal without parentheses. New tests in `tests/lang/test_calc_parse.py`, under "Error messages name only what is legal at that point", fail on that bug and pass on the real code.
- **Import graph** (`src/dsdk/graph/bridges.py`). A relative import that climbs above the top package was not tested, and the planted change made it crash. A new test in `tests/graph/test_graph_bridges.py`, "ignores relative imports that climb past the top package", fails on that bug and passes on the real code.

The kernel, with 80 planted bugs, had none slip through.
