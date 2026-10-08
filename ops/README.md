# ops — how work gets dispatched

Roles
- **Opus (planner)**: plans, reviews, arbitrates, commits.
- **Sonnet (contract author)**: writes interface stubs + adversarial *and* explainable tests. Never implements.
- **Haiku (implementer / surveyor)**: implements against Sonnet tests. **2 attempts per task.** Max 3 concurrent.

Backpressure ledger: `ops/ledger.jsonl`, one JSON object per agent attempt:
`{ts, task, model, attempt, outcome: pass|partial|fail|error, tests_passed, tests_total, wall_s, note}`

Concurrency policy (AIMD):
- Start Haiku concurrency at 2.
- After a round where every attempt-1 passed: +1 (cap 3).
- Any attempt-2 failure, tool/proxy error (429 etc.), or review rejection: halve (floor 1).
- A task that fails both Haiku attempts escalates to Sonnet and is logged as a *Haiku limit*
  (`ops/haiku-limits.md`) — that list is the point: it tells us what to stop handing Haiku.
