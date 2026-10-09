# Mutation evidence: dsdk.prob (A3)

Commit `a355b9b752a0`. 526 mutation sites in the shipped source; 120 sampled with seed 20261009.
**120 killed, 0 survived** (100% kill rate).

Reproduce: `.venv/bin/python tools/mutants/run.py dsdk.prob tests/prob tests/integration/test_prob_text.py --max 120 --seed 20261009`

A survivor is either equivalent (no observable change) or a test gap. Each one is listed for triage.

## Survivors

| # | Where | Kind | Original | Mutant |
|---|---|---|---|---|

## Killed (first failing test)

| # | Where | Kind | Killed by |
|---|---|---|---|
| 0 | `src/dsdk/prob/ask.py:45` | flip-bool | `exit 4` |
| 1 | `src/dsdk/prob/ask.py:51` | return-none | `exit 4` |
| 2 | `src/dsdk/prob/ask.py:56` | drop-not | `exit 4` |
| 3 | `src/dsdk/prob/ask.py:61` | compare | `exit 4` |
| 4 | `src/dsdk/prob/ask.py:63` | negate-if | `exit 4` |
| 5 | `src/dsdk/prob/ask.py:64` | return-none | `exit 4` |
| 6 | `src/dsdk/prob/ask.py:110` | drop-not | `exit 4` |
| 7 | `src/dsdk/prob/ask.py:115` | return-none | `exit 4` |
| 8 | `src/dsdk/prob/ask.py:123` | negate-if | `exit 4` |
| 9 | `src/dsdk/prob/ask.py:126` | compare | `exit 4` |
| 10 | `src/dsdk/prob/ask.py:128` | return-none | `exit 4` |
| 11 | `src/dsdk/prob/bayesnet.py:57` | drop-not | `exit 4` |
| 12 | `src/dsdk/prob/bayesnet.py:59` | drop-not | `exit 4` |
| 13 | `src/dsdk/prob/bayesnet.py:72` | compare | `exit 4` |
| 14 | `src/dsdk/prob/bayesnet.py:77` | binop | `exit 4` |
| 15 | `src/dsdk/prob/bayesnet.py:91` | negate-if | `exit 4` |
| 16 | `src/dsdk/prob/bayesnet.py:115` | int+1 | `exit 4` |
| 17 | `src/dsdk/prob/bayesnet.py:127` | negate-if | `exit 4` |
| 18 | `src/dsdk/prob/bayesnet.py:142` | drop-not | `exit 4` |
| 19 | `src/dsdk/prob/bayesnet.py:145` | negate-if | `exit 4` |
| 20 | `src/dsdk/prob/bayesnet.py:154` | compare | `exit 4` |
| 21 | `src/dsdk/prob/bayesnet.py:156` | flip-bool | `exit 4` |
| 22 | `src/dsdk/prob/exact.py:33` | negate-if | `exit 4` |
| 23 | `src/dsdk/prob/sampling.py:40` | boolop | `exit 4` |
| 24 | `src/dsdk/prob/sampling.py:74` | drop-not | `exit 4` |
| 25 | `src/dsdk/prob/sampling.py:76` | compare | `exit 4` |
| 26 | `src/dsdk/prob/sampling.py:79` | binop | `exit 4` |
| 27 | `src/dsdk/prob/sampling.py:82` | binop | `exit 4` |
| 28 | `src/dsdk/prob/sampling.py:82` | int+1 | `exit 4` |
| 29 | `src/dsdk/prob/sampling.py:87` | negate-if | `exit 4` |
| 30 | `src/dsdk/prob/sampling.py:119` | int+1 | `exit 4` |
| 31 | `src/dsdk/prob/sampling.py:123` | return-none | `exit 4` |
| 32 | `src/dsdk/prob/sampling.py:148` | negate-if | `exit 4` |
| 33 | `src/dsdk/prob/sampling.py:148` | compare | `exit 4` |
| 34 | `src/dsdk/prob/sampling.py:155` | return-none | `exit 4` |
| 35 | `src/dsdk/prob/sampling.py:168` | negate-if | `exit 4` |
| 36 | `src/dsdk/prob/sampling.py:171` | negate-if | `exit 4` |
| 37 | `src/dsdk/prob/sampling.py:173` | negate-if | `exit 4` |
| 38 | `src/dsdk/prob/sampling.py:175` | int+1 | `exit 4` |
| 39 | `src/dsdk/prob/sampling.py:176` | boolop | `exit 4` |
| 40 | `src/dsdk/prob/sampling.py:178` | int+1 | `exit 4` |
| 41 | `src/dsdk/prob/sampling.py:179` | compare | `exit 4` |
| 42 | `src/dsdk/prob/sampling.py:197` | negate-if | `exit 4` |
| 43 | `src/dsdk/prob/sampling.py:197` | drop-not | `exit 4` |
| 44 | `src/dsdk/prob/sampling.py:200` | negate-if | `exit 4` |
| 45 | `src/dsdk/prob/sampling.py:202` | negate-if | `exit 4` |
| 46 | `src/dsdk/prob/sampling.py:202` | compare | `exit 4` |
| 47 | `src/dsdk/prob/sampling.py:203` | return-none | `exit 4` |
| 48 | `src/dsdk/prob/sampling.py:226` | boolop | `exit 4` |
| 49 | `src/dsdk/prob/sampling.py:226` | compare | `exit 4` |
| 50 | `src/dsdk/prob/sampling.py:226` | drop-not | `exit 4` |
| 51 | `src/dsdk/prob/sampling.py:236` | return-none | `exit 4` |
| 52 | `src/dsdk/prob/sampling.py:241` | int+1 | `exit 4` |
| 53 | `src/dsdk/prob/sampling.py:244` | boolop | `exit 4` |
| 54 | `src/dsdk/prob/sampling.py:246` | int+1 | `exit 4` |
| 55 | `src/dsdk/prob/sampling.py:249` | negate-if | `exit 4` |
| 56 | `src/dsdk/prob/sampling.py:266` | negate-if | `exit 4` |
| 57 | `src/dsdk/prob/sampling.py:284` | drop-not | `exit 4` |
| 58 | `src/dsdk/prob/sampling.py:287` | boolop | `exit 4` |
| 59 | `src/dsdk/prob/sampling.py:298` | return-none | `exit 4` |
| 60 | `src/dsdk/prob/transitions.py:47` | return-none | `exit 4` |
| 61 | `src/dsdk/prob/transitions.py:50` | int+1 | `exit 4` |
| 62 | `src/dsdk/prob/transitions.py:64` | negate-if | `exit 4` |
| 63 | `src/dsdk/prob/transitions.py:64` | drop-not | `exit 4` |
| 64 | `src/dsdk/prob/transitions.py:69` | int+1 | `exit 4` |
| 65 | `src/dsdk/prob/transitions.py:70` | binop | `exit 4` |
| 66 | `src/dsdk/prob/transitions.py:70` | int+1 | `exit 4` |
| 67 | `src/dsdk/prob/transitions.py:71` | compare | `exit 4` |
| 68 | `src/dsdk/prob/transitions.py:80` | negate-if | `exit 4` |
| 69 | `src/dsdk/prob/transitions.py:80` | drop-not | `exit 4` |
| 70 | `src/dsdk/prob/transitions.py:96` | drop-not | `exit 4` |
| 71 | `src/dsdk/prob/transitions.py:108` | negate-if | `exit 4` |
| 72 | `src/dsdk/prob/transitions.py:109` | int+1 | `exit 4` |
| 73 | `src/dsdk/prob/transitions.py:117` | negate-if | `exit 4` |
| 74 | `src/dsdk/prob/transitions.py:117` | compare | `exit 4` |
| 75 | `src/dsdk/prob/transitions.py:132` | negate-if | `exit 4` |
| 76 | `src/dsdk/prob/transitions.py:149` | negate-if | `exit 4` |
| 77 | `src/dsdk/prob/transitions.py:151` | negate-if | `exit 4` |
| 78 | `src/dsdk/prob/transitions.py:156` | return-none | `exit 4` |
| 79 | `src/dsdk/prob/transitions.py:165` | negate-if | `exit 4` |
| 80 | `src/dsdk/prob/transitions.py:168` | negate-if | `exit 4` |
| 81 | `src/dsdk/prob/transitions.py:173` | int+1 | `exit 4` |
| 82 | `src/dsdk/prob/transitions.py:175` | return-none | `exit 4` |
| 83 | `src/dsdk/prob/transitions.py:184` | int+1 | `exit 4` |
| 84 | `src/dsdk/prob/transitions.py:196` | compare | `exit 4` |
| 85 | `src/dsdk/prob/transitions.py:198` | compare | `exit 4` |
| 86 | `src/dsdk/prob/transitions.py:202` | negate-if | `exit 4` |
| 87 | `src/dsdk/prob/transitions.py:202` | int+1 | `exit 4` |
| 88 | `src/dsdk/prob/transitions.py:234` | compare | `exit 4` |
| 89 | `src/dsdk/prob/transitions.py:244` | return-none | `exit 4` |
| 90 | `src/dsdk/prob/updates.py:51` | drop-not | `exit 4` |
| 91 | `src/dsdk/prob/updates.py:53` | compare | `exit 4` |
| 92 | `src/dsdk/prob/updates.py:101` | negate-if | `exit 4` |
| 93 | `src/dsdk/prob/updates.py:109` | binop | `exit 4` |
| 94 | `src/dsdk/prob/updates.py:111` | compare | `exit 4` |
| 95 | `src/dsdk/prob/updates.py:112` | binop | `exit 4` |
| 96 | `src/dsdk/prob/worlds.py:72` | negate-if | `exit 4` |
| 97 | `src/dsdk/prob/worlds.py:72` | compare | `exit 4` |
| 98 | `src/dsdk/prob/worlds.py:74` | negate-if | `exit 4` |
| 99 | `src/dsdk/prob/worlds.py:74` | compare | `exit 4` |
| 100 | `src/dsdk/prob/worlds.py:74` | compare | `exit 4` |
| 101 | `src/dsdk/prob/worlds.py:104` | negate-if | `exit 4` |
| 102 | `src/dsdk/prob/worlds.py:104` | drop-not | `exit 4` |
| 103 | `src/dsdk/prob/worlds.py:107` | drop-not | `exit 4` |
| 104 | `src/dsdk/prob/worlds.py:109` | boolop | `exit 4` |
| 105 | `src/dsdk/prob/worlds.py:109` | drop-not | `exit 4` |
| 106 | `src/dsdk/prob/worlds.py:126` | negate-if | `exit 4` |
| 107 | `src/dsdk/prob/worlds.py:130` | negate-if | `exit 4` |
| 108 | `src/dsdk/prob/worlds.py:155` | drop-not | `exit 4` |
| 109 | `src/dsdk/prob/worlds.py:160` | flip-bool | `exit 4` |
| 110 | `src/dsdk/prob/worlds.py:174` | return-none | `exit 4` |
| 111 | `src/dsdk/prob/worlds.py:187` | drop-not | `exit 4` |
| 112 | `src/dsdk/prob/worlds.py:242` | return-none | `exit 4` |
| 113 | `src/dsdk/prob/worlds.py:253` | negate-if | `exit 4` |
| 114 | `src/dsdk/prob/worlds.py:253` | drop-not | `exit 4` |
| 115 | `src/dsdk/prob/worlds.py:256` | compare | `exit 4` |
| 116 | `src/dsdk/prob/worlds.py:260` | int+1 | `exit 4` |
| 117 | `src/dsdk/prob/worlds.py:262` | return-none | `exit 4` |
| 118 | `src/dsdk/prob/worlds.py:268` | negate-if | `exit 4` |
| 119 | `src/dsdk/prob/worlds.py:272` | return-none | `exit 4` |
