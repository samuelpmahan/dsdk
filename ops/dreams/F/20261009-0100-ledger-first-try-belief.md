# Put an honest interval on "Haiku passes first time" from the build ledger
kind: instrument
idea: Turn ops/ledger.jsonl into a small belief: each first attempt is a Bernoulli trial, and the Lab shows the estimated first-try pass rate for each model with its interval, plus how many more trials would be needed to tell two models apart. It would use the Wilson interval and the exact-versus-sampled comparison from the new probability package, so the Lab reports a range instead of "27 of 28".
why it's interesting: The build ledger is the data dsdk generates about its own construction, and the question "is it safe to give Haiku the next kind of card?" is exactly what Sam's reporting rules ask us to support with checkable evidence. A point estimate of 96% sounds safer than the data allows.
smallest experiment: A short script that reads the ledger, groups first attempts by model, and prints successes, trials and the 95% Wilson interval; then add the number of further passing trials that would shrink the lower end above 90%.
reuses: dsdk.prob wilson_interval and standard_error; the ledger reader in ops/ledger.py.
probe: Haiku first attempts in the ledger today: 27 passes out of 28 (one partial). The 95% Wilson interval for 27 of 28 is about 0.82 to 0.99, so the data does not rule out a first-try rate of 82%. Sonnet has 8 passes in 8, whose interval starts near 0.68. Command: wilson_interval(27, 28) and wilson_interval(8, 8) from dsdk.prob, counts from python over ops/ledger.jsonl.
score: surprise=2 cost=1 reuse=4
