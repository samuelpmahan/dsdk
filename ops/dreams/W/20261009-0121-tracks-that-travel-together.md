# Tracks that travel together (across DJs, not within one set)
kind: hypothesis
idea: A pair of tracks that many DIFFERENT DJs each played in their own sets travels together more convincingly than a pair that merely shares one long set. Rank pairs by the number of distinct DJ credits that played both, and compare with the plain co-selection weight.
why it's interesting: The co-selection graph is dominated by one 169-track truncated credit (a quarter of all pairs). A DJ-count measure ignores it and should surface real scene staples. It also gives the six-degrees search a better notion of an "inferred" step: weight inferred steps by how many DJs support them.
smallest experiment: For tracks played by at least 3 DJ credits, count distinct credits playing both; list the top 20; check how many of them are co-selected only inside the mega set.
reuses: dsdk.worlds.coselection_graph (as the baseline), SixDegrees hop evidence, the selection table
probe: Top pairs have 5 distinct DJ credits each: Space Laces - Torque with PEEKABOO & G-REX - Babatunde, and with Excision & Space Laces - 1 On 1; Riot Ten - Rail Breaker with Space Laces & Getter - Choppaz. Torque appears in 3 of the top 5. Command: python3 tools/lab/lostlands_findings.py (finding 2 for the baseline), probe code in the report.
score: surprise=3 cost=2 reuse=4
