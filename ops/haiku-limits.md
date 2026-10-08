# Haiku limits (observed)

What Haiku got wrong, so we stop handing it that shape of task, or we spell it out.

| Date | Task | Attempt | What went wrong | Prompt fix |
|---|---|---|---|---|
| 2026-10-08 | inv-misc (15 repos) | 1 | It saw one local ref in a shallow clone and took that to mean the remote had one branch, so it skipped the fetch. The instruction was conditional ("for each repo with >1 branch") and it evaluated the condition from the wrong source. | Make instructions unconditional, or give the precomputed fact ("remote has N branches"). Don't let Haiku decide whether a step applies. |
