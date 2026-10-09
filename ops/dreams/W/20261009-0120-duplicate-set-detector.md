# Duplicate-set detector for the corpus
kind: instrument
idea: Score every pair of sets on the same date by how many identical back-to-back moves they share, and flag pairs far above the background as "probably the same stretch of music credited twice". Show the flagged pairs with the shared chain, and show how selection counts and "who played it" change if the duplicate is merged.
why it's interesting: It is a bug-finder for Sam's own pipeline. The corpus is built from per-DJ files, and a b2b credit plus a solo credit can describe the same music. Every DJ-overlap and "tracks that travel together" result inherits that error until it is found.
smallest experiment: For all 54 sets, count shared transitions per pair on the same date; report pairs above 3 shared moves; list the shared chain; recompute the DJ graph with the flagged pair merged and see which edges vanish.
reuses: dsdk.worlds.LostLands.sets, check_transitions, dj_graph, the evidence viewer's table and cross-check helpers
probe: Exactly one pair stands out. "Figure & Space Laces & Kill The Noise & Bare & Kill Rex" and "Kill The Noise" (both 2018-09-14) share 6 identical moves, including Darude - Sandstorm -> Cardi B - Bodak Yellow -> Calcium & K-Nine - Damn Son -> PEEKABOO & G-REX - Babatunde; the next best pair shares 2. Command: python3 tools/lab/lostlands_findings.py
score: surprise=4 cost=2 reuse=4
