# Haiku limits (observed)

What Haiku got wrong, so we stop handing it that shape of task, or we spell it out.

| Date | Task | Attempt | What went wrong | Prompt fix |
|---|---|---|---|---|
| 2026-10-08 | inv-misc (15 repos) | 1 | It saw one local ref in a shallow clone and took that to mean the remote had one branch, so it skipped the fetch. The instruction was conditional ("for each repo with >1 branch") and it evaluated the condition from the wrong source. | Make instructions unconditional, or give the precomputed fact ("remote has N branches"). Don't let Haiku decide whether a step applies. |
| 2026-10-08 | T03 core-tick | 1 | Passed, but it created a stray Claude Code Remote session by mistake and then archived it. Haiku will reach for powerful tools it was never asked to use. | Implementation prompts should say "use only Read/Edit/Bash; never create sessions, triggers, or agents". Consider restricting tools for implementer agents. |
| 2026-10-08 | T08 logic-structures | 1 | Passed, but it was the second Haiku to create a stray remote session, and this one was left running (the planner archived it). Two Haikus also finished with background work still running. Haiku does not reliably clean up after itself. | Treat it as a pattern: every implementer prompt now carries the "only file edits and pytest; never create sessions/triggers/agents" rule (T06 and T07 had it and stayed clean). Planner checks for child sessions after each round. |
