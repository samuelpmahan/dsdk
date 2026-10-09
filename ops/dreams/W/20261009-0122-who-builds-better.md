# Who builds dsdk better? First-try rates with exact intervals, from the build ledger
kind: instrument
idea: Turn first_try_rate into a small table with an exact binomial (Clopper-Pearson) interval per model, plus a plot of how the rate moved round by round, so "Haiku is reliable" is stated with its uncertainty and a thin sample is shown as thin.
why it's interesting: dsdk studying the agents that build it is the literal self-reference Sam asked for, and the ledger already holds the data. It also keeps "not observed" (Opus has no rows), "unknown" (too few rows) and a measured rate visibly different, which is the same epistemic point as the Lost Lands graphs.
smallest experiment: Add the interval to first_try_rate's reason text and render models x (n, passes, interval) in the Lab; assert the interval against a hand-computed value for 33/35 and 9/9.
reuses: dsdk.worlds.first_try_rate, dsdk.prob once it exists (exact binomial), the Lab table component
probe: In the live ledger Haiku has 33 passes in 35 first attempts (0.943), Sonnet 9 in 9 (1.0, but only 9 rows, so UNKNOWN at min_n 10). Command: .venv/bin/python -c "from dsdk.worlds import *; e=load_ledger(); print(first_try_rate(e,'haiku'), first_try_rate(e,'sonnet',min_n=10))" (works once the build-ledger card is implemented).
score: surprise=3 cost=2 reuse=5
