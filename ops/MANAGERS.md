# Manager protocol

Two long-lived Sonnet managers. Opus orchestrates. Sam sets direction only.

| Manager | Owns | Haiku slots |
|---|---|---|
| **F: Foundations** | A2 lang (cards T09–T16), A3 prob, A4 geom contracts; proofs; Python/JS parity harness | 2 |
| **W: Worlds & Lab** | A5 close-out (T26); `dsdk.worlds` (Lost Lands DJ corpus, Wumpus, the build ledger); Lab instruments; evidence builders | 2 |

## Each turn
1. **Intervene first.** Handle whatever woke you: a Haiku report, a review, a failing test, or a cross-manager request.
   - Verify every Haiku claim yourself by re-running its done command with `.venv/bin/python -m pytest`.
   - Log every Haiku attempt with `python ops/ledger.py log <task> haiku <attempt> <pass|fail|partial|error> <wall_s> --tests P/T --round <n> --note "<manager>: ..."`.
   - Haiku gets 2 attempts per card. After a second failure, take the card yourself and add a row to `ops/haiku-limits.md`.
2. **Keep your 2 Haiku slots full** whenever ready cards exist. (Checked 2026-10-09: subagent managers have no Agent tool, so they always use the queue path below. Opus dispatches from `ops/queue/` on every wake.)
   - Dispatch with the Agent tool: `model: haiku`, `subagent_type: general-purpose`, `run_in_background: true`.
   - Use the implementer prompt below.
   - If you cannot spawn agents, append ready cards to `ops/queue/<F|W>.md` and Opus will dispatch them.
3. **Dream when nothing needs intervention.** End the turn by writing 1–3 files to `ops/dreams/<F|W>/<YYYYMMDD-HHMM>-<slug>.md`, using this format:
   ```
   # <idea title>
   kind: instrument | hypothesis | cross-track link | better test | process
   idea: <2-4 sentences>
   why it's interesting: <for Sam specifically; prefer his own data: Lost Lands, Wumpus, the build ledger>
   smallest experiment: <bounded, runnable>
   reuses: <dsdk packages/functions it builds on>
   probe: <optional: a read-only result you computed now, with the command>
   score: surprise=<1-5> cost=<1-5, low is cheap> reuse=<1-5>
   ```
   - You may run read-only probes on real data to ground a dream.
   - Never implement a dream on your own initiative. Opus promotes the winners to cards.
4. **Report to Opus.** Reply with what changed, what is in flight, what you dreamed (titles only), and any request for the other manager.

## Rules
- Never review or audit your own work. F audits W's proofs and evidence, and W audits F's.
- Edit only the paths your track owns. Before an edit, check that another agent is not editing the same file.
- Implementers and managers run pytest via `.venv/bin/python -m pytest`, never `uv run`. Only Opus runs `uv sync`.
- No sessions, triggers, remote messages or repo-attachment tools. Do not commit; Opus commits.
- Sam does not write code or proofs. Things for Sam are direction-level questions only, and they go in your report.

## Implementer prompt (Haiku)
> You implement exactly one task card in /home/user/dsdk: `<card path>`.
> 1. Read the card, the stub file(s) it owns (docstrings are the spec), and the tests named in its done command.
> 2. Edit ONLY the functions or files the card owns. Never edit tests, fixtures, tracks.toml or ops/.
> 3. Run the done command with `.venv/bin/python -m pytest` in place of `uv run pytest`, keeping the same arguments. Do not run uv. Iterate until it exits 0, or until you are sure you cannot make it pass.
> 4. Use ONLY file reading/editing and Bash for pytest. Never create sessions, triggers, agents, messages or remote resources. Never run git commands that change state.
>
> Final reply: one line of JSON only: `{"task":"<id>","passed":N,"total":M,"done_command_exit":0|1,"notes":"<=200 chars"}`
