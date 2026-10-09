# T09-lang-lexer

**Goal.** Implement `char_class`, `default_dfa` and `tokenize` in `src/dsdk/lang/lexer.py`: a maximal-munch tokenizer driven by an explicit DFA table.

**Files to edit.** `src/dsdk/lang/lexer.py` only. Do NOT edit any file under `tests/`, `fixtures/`, `tracks.toml`, `src/dsdk/lang/errors.py` or other tasks' functions. The module docstring is the spec: read it first, then `tests/lang/test_lexer.py`.

**Done when.** `cd /home/user/dsdk && uv run pytest tests/lang/test_lexer.py -q` passes (exit 0). Then run `cd /home/user/dsdk && uv run pytest -q tests/core tests/logic tests/test_reuse.py` and confirm it still passes.

**Depends on.** none (start here).

**Pitfalls.**
- `default_dfa()` returns the table from the docstring as DATA: write the 20 transitions and the 16 accepting states out literally as dict literals inside the function (a test compares them entry by entry). Build FRESH dicts on every call.
- `char_class` is ASCII only. Use explicit character sets (`"abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_"`, `"0123456789"`, `" \t\n\r"`, `"()~&|+*-<>="`). NEVER `str.isalpha`, `isdigit`, `isspace`, `isalnum`: they accept `é`, `٣` and NBSP and the tests check exactly those. A symbol character's class is the character itself (`char_class("(") == "("`). A non-str raises `TypeError`; a str whose length is not 1 raises `ValueError`.
- Algorithm for each start index `i`: `state = dfa.start; j = i; last = None`; while `j < n`: `nxt = dfa.transitions.get((state, char_class(text[j])))`; if `nxt is None` break; `state = nxt; j += 1`; if `state in dfa.accepting`: `last = (j, dfa.accepting[state])`. After the loop: if `last is None` raise `LexError(f"illegal character {text[i]!r}", i)` (message first, OFFSET second, offset is `i`). Otherwise emit `Token(kind, text[i:end], i, end)` and continue from `end`. This "remember the last accepting position" step IS the backtracking: `<-b` reaches the non-accepting state `lt_minus`, falls back to the accepted `<`, and then `-` is lexed on its own.
- Use the `dfa` argument when given (`dfa if dfa is not None else default_dfa()`); a test passes a modified table and expects the modified behaviour. Do not hard-code any character logic outside the table and `char_class`.
- Keywords are applied AFTER the DFA: if `kind == "NAME"` and the whole token text is in `keywords`, the kind becomes `text.upper()`. `trueish` and `True` stay NAME. `keep_whitespace=False` drops WS tokens, but offsets of the other tokens still refer to the original text.
- Non-str input raises `TypeError`. Empty input returns `[]`. Loop with indexes (no recursion, no repeated string concatenation): a test lexes 100000 characters.

**Rules.** Use ONLY file reading/editing and Bash for pytest. Never create sessions, triggers, agents or remote resources. Do not run git commands that change state. Remove `raise NotImplementedError` only in the functions this task owns. Keep docstrings. No new dependencies. 2 attempts total.
