# Decisions only Sam can make (non-blocking)

Sam does not write code, proofs or exercises. Agents build, prove, review and
produce evidence. This file lists only choices about direction. Each has a default,
so the pipeline never waits.

| Added | Track | Decision | Default in use |
|---|---|---|---|
| 2026-10-08 | B1 | Which tabular world: jukebox transitions, the hithero schools CSV, or a synthetic workflow? | Synthetic workflow (no private data) |
| 2026-10-09 | Wumpus | Should the gambling agent refuse a square above some chance of death (for example 1 in 3), and climb out instead? Without a limit it finds gold 133 times in 300 caves and dies 146 times; the logic-only agent finds gold 71 times and never dies. | No limit (gambles on the least risky square, whatever the risk) |
| 2026-10-09 | Sources | Which repositories, branches or paths are the right sources for Lost Lands and the other worlds? ("u grabbed alllllll the wrong things") | Lost Lands, networks and Six Degrees cards stay held; nothing new is built on the current sources |
| 2026-10-09 | Implementers | Keep Haiku on tight, fully specified cards; switch implementers to Sonnet; or have Sonnet review each Haiku change? | Haiku on tight cards only (last two Wumpus cards: both first try) |
