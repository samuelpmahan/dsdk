# Mutation evidence: dsdk.graph (A5)

Commit `a355b9b752a0`. 384 mutation sites in the shipped source; 120 sampled with seed 20261009.
**120 killed, 0 survived** (100% kill rate).

Reproduce: `.venv/bin/python tools/mutants/run.py dsdk.graph tests/graph tests/integration/test_graph_proofs.py --max 120 --seed 20261009`

A survivor is either equivalent (no observable change) or a test gap. Each one is listed for triage.

## Survivors

| # | Where | Kind | Original | Mutant |
|---|---|---|---|---|

## Killed (first failing test)

| # | Where | Kind | Killed by |
|---|---|---|---|
| 0 | `src/dsdk/graph/bridges.py:46` | negate-if | `exit 4` |
| 1 | `src/dsdk/graph/bridges.py:96` | negate-if | `exit 4` |
| 2 | `src/dsdk/graph/bridges.py:101` | return-none | `exit 4` |
| 3 | `src/dsdk/graph/bridges.py:119` | flip-bool | `exit 4` |
| 4 | `src/dsdk/graph/bridges.py:136` | negate-if | `exit 4` |
| 5 | `src/dsdk/graph/bridges.py:139` | compare | `exit 4` |
| 6 | `src/dsdk/graph/bridges.py:147` | negate-if | `exit 4` |
| 7 | `src/dsdk/graph/bridges.py:174` | compare | `exit 4` |
| 8 | `src/dsdk/graph/bridges.py:177` | compare | `exit 4` |
| 9 | `src/dsdk/graph/bridges.py:180` | int+1 | `exit 4` |
| 10 | `src/dsdk/graph/bridges.py:181` | negate-if | `exit 4` |
| 11 | `src/dsdk/graph/bridges.py:183` | binop | `exit 4` |
| 12 | `src/dsdk/graph/bridges.py:184` | compare | `exit 4` |
| 13 | `src/dsdk/graph/bridges.py:186` | negate-if | `exit 4` |
| 14 | `src/dsdk/graph/bridges.py:186` | int+1 | `exit 4` |
| 15 | `src/dsdk/graph/bridges.py:231` | compare | `exit 4` |
| 16 | `src/dsdk/graph/bridges.py:237` | flip-bool | `exit 4` |
| 17 | `src/dsdk/graph/bridges.py:238` | flip-bool | `exit 4` |
| 18 | `src/dsdk/graph/evidence.py:76` | int+1 | `exit 4` |
| 19 | `src/dsdk/graph/evidence.py:80` | negate-if | `exit 4` |
| 20 | `src/dsdk/graph/evidence.py:88` | compare | `exit 4` |
| 21 | `src/dsdk/graph/evidence.py:101` | compare | `exit 4` |
| 22 | `src/dsdk/graph/evidence.py:109` | negate-if | `exit 4` |
| 23 | `src/dsdk/graph/evidence.py:109` | boolop | `exit 4` |
| 24 | `src/dsdk/graph/evidence.py:109` | compare | `exit 4` |
| 25 | `src/dsdk/graph/evidence.py:113` | negate-if | `exit 4` |
| 26 | `src/dsdk/graph/evidence.py:114` | return-none | `exit 4` |
| 27 | `src/dsdk/graph/evidence.py:116` | return-none | `exit 4` |
| 28 | `src/dsdk/graph/model.py:114` | negate-if | `exit 4` |
| 29 | `src/dsdk/graph/model.py:123` | negate-if | `exit 4` |
| 30 | `src/dsdk/graph/model.py:124` | negate-if | `exit 4` |
| 31 | `src/dsdk/graph/model.py:124` | boolop | `exit 4` |
| 32 | `src/dsdk/graph/model.py:124` | drop-not | `exit 4` |
| 33 | `src/dsdk/graph/model.py:126` | negate-if | `exit 4` |
| 34 | `src/dsdk/graph/model.py:140` | negate-if | `exit 4` |
| 35 | `src/dsdk/graph/model.py:140` | compare | `exit 4` |
| 36 | `src/dsdk/graph/model.py:155` | negate-if | `exit 4` |
| 37 | `src/dsdk/graph/model.py:163` | negate-if | `exit 4` |
| 38 | `src/dsdk/graph/model.py:203` | compare | `exit 4` |
| 39 | `src/dsdk/graph/model.py:206` | int+1 | `exit 4` |
| 40 | `src/dsdk/graph/model.py:207` | negate-if | `exit 4` |
| 41 | `src/dsdk/graph/model.py:230` | return-none | `exit 4` |
| 42 | `src/dsdk/graph/model.py:242` | negate-if | `exit 4` |
| 43 | `src/dsdk/graph/model.py:246` | return-none | `exit 4` |
| 44 | `src/dsdk/graph/model.py:263` | compare | `exit 4` |
| 45 | `src/dsdk/graph/model.py:265` | return-none | `exit 4` |
| 46 | `src/dsdk/graph/model.py:277` | negate-if | `exit 4` |
| 47 | `src/dsdk/graph/model.py:277` | drop-not | `exit 4` |
| 48 | `src/dsdk/graph/model.py:277` | boolop | `exit 4` |
| 49 | `src/dsdk/graph/model.py:281` | negate-if | `exit 4` |
| 50 | `src/dsdk/graph/model.py:287` | return-none | `exit 4` |
| 51 | `src/dsdk/graph/model.py:287` | compare | `exit 4` |
| 52 | `src/dsdk/graph/model.py:302` | negate-if | `exit 4` |
| 53 | `src/dsdk/graph/model.py:302` | drop-not | `exit 4` |
| 54 | `src/dsdk/graph/model.py:305` | return-none | `exit 4` |
| 55 | `src/dsdk/graph/model.py:310` | return-none | `exit 4` |
| 56 | `src/dsdk/graph/model.py:320` | int+1 | `exit 4` |
| 57 | `src/dsdk/graph/model.py:324` | drop-not | `exit 4` |
| 58 | `src/dsdk/graph/model.py:326` | return-none | `exit 4` |
| 59 | `src/dsdk/graph/model.py:337` | int+1 | `exit 4` |
| 60 | `src/dsdk/graph/model.py:339` | negate-if | `exit 4` |
| 61 | `src/dsdk/graph/model.py:346` | drop-not | `exit 4` |
| 62 | `src/dsdk/graph/model.py:349` | flip-bool | `exit 4` |
| 63 | `src/dsdk/graph/model.py:359` | negate-if | `exit 4` |
| 64 | `src/dsdk/graph/model.py:362` | negate-if | `exit 4` |
| 65 | `src/dsdk/graph/model.py:362` | compare | `exit 4` |
| 66 | `src/dsdk/graph/proofs.py:72` | negate-if | `exit 4` |
| 67 | `src/dsdk/graph/proofs.py:87` | negate-if | `exit 4` |
| 68 | `src/dsdk/graph/proofs.py:87` | boolop | `exit 4` |
| 69 | `src/dsdk/graph/proofs.py:87` | drop-not | `exit 4` |
| 70 | `src/dsdk/graph/proofs.py:121` | compare | `exit 4` |
| 71 | `src/dsdk/graph/proofs.py:126` | boolop | `exit 4` |
| 72 | `src/dsdk/graph/proofs.py:126` | compare | `exit 4` |
| 73 | `src/dsdk/graph/proofs.py:132` | negate-if | `exit 4` |
| 74 | `src/dsdk/graph/proofs.py:134` | int+1 | `exit 4` |
| 75 | `src/dsdk/graph/proofs.py:137` | binop | `exit 4` |
| 76 | `src/dsdk/graph/proofs.py:137` | binop | `exit 4` |
| 77 | `src/dsdk/graph/proofs.py:140` | negate-if | `exit 4` |
| 78 | `src/dsdk/graph/proofs.py:141` | binop | `exit 4` |
| 79 | `src/dsdk/graph/proofs.py:160` | drop-not | `exit 4` |
| 80 | `src/dsdk/graph/proofs.py:164` | return-none | `exit 4` |
| 81 | `src/dsdk/graph/proofs.py:166` | negate-if | `exit 4` |
| 82 | `src/dsdk/graph/proofs.py:167` | return-none | `exit 4` |
| 83 | `src/dsdk/graph/proofs.py:171` | compare | `exit 4` |
| 84 | `src/dsdk/graph/proofs.py:172` | binop | `exit 4` |
| 85 | `src/dsdk/graph/proofs.py:175` | drop-not | `exit 4` |
| 86 | `src/dsdk/graph/proofs.py:176` | return-none | `exit 4` |
| 87 | `src/dsdk/graph/proofs.py:177` | negate-if | `exit 4` |
| 88 | `src/dsdk/graph/proofs.py:179` | negate-if | `exit 4` |
| 89 | `src/dsdk/graph/proofs.py:179` | compare | `exit 4` |
| 90 | `src/dsdk/graph/proofs.py:186` | flip-bool | `exit 4` |
| 91 | `src/dsdk/graph/proofs.py:203` | negate-if | `exit 4` |
| 92 | `src/dsdk/graph/proofs.py:206` | negate-if | `exit 4` |
| 93 | `src/dsdk/graph/proofs.py:209` | return-none | `exit 4` |
| 94 | `src/dsdk/graph/relational.py:91` | binop | `exit 4` |
| 95 | `src/dsdk/graph/traverse.py:76` | compare | `exit 4` |
| 96 | `src/dsdk/graph/traverse.py:77` | int+1 | `exit 4` |
| 97 | `src/dsdk/graph/traverse.py:95` | negate-if | `exit 4` |
| 98 | `src/dsdk/graph/traverse.py:99` | flip-bool | `exit 4` |
| 99 | `src/dsdk/graph/traverse.py:124` | int+1 | `exit 4` |
| 100 | `src/dsdk/graph/traverse.py:134` | negate-if | `exit 4` |
| 101 | `src/dsdk/graph/traverse.py:134` | compare | `exit 4` |
| 102 | `src/dsdk/graph/traverse.py:144` | compare | `exit 4` |
| 103 | `src/dsdk/graph/traverse.py:152` | compare | `exit 4` |
| 104 | `src/dsdk/graph/traverse.py:179` | compare | `exit 4` |
| 105 | `src/dsdk/graph/traverse.py:184` | int+1 | `exit 4` |
| 106 | `src/dsdk/graph/traverse.py:191` | drop-not | `exit 4` |
| 107 | `src/dsdk/graph/traverse.py:227` | compare | `exit 4` |
| 108 | `src/dsdk/graph/traverse.py:234` | int+1 | `exit 4` |
| 109 | `src/dsdk/graph/traverse.py:235` | negate-if | `exit 4` |
| 110 | `src/dsdk/graph/traverse.py:251` | negate-if | `exit 4` |
| 111 | `src/dsdk/graph/traverse.py:251` | compare | `exit 4` |
| 112 | `src/dsdk/graph/traverse.py:259` | compare | `exit 4` |
| 113 | `src/dsdk/graph/traverse.py:262` | return-none | `exit 4` |
| 114 | `src/dsdk/graph/traverse.py:286` | negate-if | `exit 4` |
| 115 | `src/dsdk/graph/traverse.py:287` | return-none | `exit 4` |
| 116 | `src/dsdk/graph/traverse.py:291` | compare | `exit 4` |
| 117 | `src/dsdk/graph/traverse.py:299` | negate-if | `exit 4` |
| 118 | `src/dsdk/graph/traverse.py:299` | compare | `exit 4` |
| 119 | `src/dsdk/graph/traverse.py:302` | return-none | `exit 4` |
