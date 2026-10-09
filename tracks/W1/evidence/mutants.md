# Mutation evidence: dsdk.worlds (W1)

Commit `8b38ee83f47f`. 301 mutation sites in the shipped source; 120 sampled with seed 20261009.
**119 killed, 1 survived** (99% kill rate).

Reproduce: `.venv/bin/python tools/mutants/run.py dsdk.worlds 'tests/worlds/test_worlds_wumpus.py tests/worlds/test_worlds_buildlog.py tests/worlds/test_worlds_buildlog_summary.py' --max 120 --seed 20261009`

A survivor is either equivalent (no observable change) or a test gap. Each one is listed for triage.

## Survivors

| # | Where | Kind | Original | Mutant |
|---|---|---|---|---|
| 94 | `src/dsdk/worlds/wumpus.py:212` | return-none | `return Judgment(Status.INVALID, None, ex.reason)` | `return None` |

## Killed (first failing test)

| # | Where | Kind | Killed by |
|---|---|---|---|
| 0 | `src/dsdk/worlds/buildlog.py:67` | negate-if | `tests/worlds/test_worlds_buildlog.py::test_sample_loads_as_typed_records` |
| 1 | `src/dsdk/worlds/buildlog.py:70` | return-none | `tests/worlds/test_worlds_buildlog.py::test_sample_loads_as_typed_records` |
| 2 | `src/dsdk/worlds/buildlog.py:74` | return-none | `tests/worlds/test_worlds_buildlog.py::test_sample_loads_as_typed_records` |
| 3 | `src/dsdk/worlds/buildlog.py:78` | return-none | `tests/worlds/test_worlds_buildlog.py::test_malformed_lines_raise_ledger_error_with_the_line_number[invalid` |
| 4 | `src/dsdk/worlds/buildlog.py:83` | boolop | `tests/worlds/test_worlds_buildlog.py::test_malformed_lines_raise_ledger_error_with_the_line_number[wall` |
| 5 | `src/dsdk/worlds/buildlog.py:89` | negate-if | `tests/worlds/test_worlds_buildlog.py::test_sample_loads_as_typed_records` |
| 6 | `src/dsdk/worlds/buildlog.py:96` | negate-if | `tests/worlds/test_worlds_buildlog.py::test_sample_loads_as_typed_records` |
| 7 | `src/dsdk/worlds/buildlog.py:98` | negate-if | `tests/worlds/test_worlds_buildlog.py::test_sample_loads_as_typed_records` |
| 8 | `src/dsdk/worlds/buildlog.py:98` | drop-not | `tests/worlds/test_worlds_buildlog.py::test_sample_loads_as_typed_records` |
| 9 | `src/dsdk/worlds/buildlog.py:108` | drop-not | `tests/worlds/test_worlds_buildlog.py::test_sample_loads_as_typed_records` |
| 10 | `src/dsdk/worlds/buildlog.py:114` | boolop | `tests/worlds/test_worlds_buildlog.py::test_sample_loads_as_typed_records` |
| 11 | `src/dsdk/worlds/buildlog.py:114` | compare | `tests/worlds/test_worlds_buildlog.py::test_sample_loads_as_typed_records` |
| 12 | `src/dsdk/worlds/buildlog.py:118` | drop-not | `tests/worlds/test_worlds_buildlog.py::test_sample_loads_as_typed_records` |
| 13 | `src/dsdk/worlds/buildlog.py:121` | negate-if | `tests/worlds/test_worlds_buildlog.py::test_sample_loads_as_typed_records` |
| 14 | `src/dsdk/worlds/buildlog.py:124` | compare | `tests/worlds/test_worlds_buildlog.py::test_sample_loads_as_typed_records` |
| 15 | `src/dsdk/worlds/buildlog.py:127` | boolop | `tests/worlds/test_worlds_buildlog.py::test_malformed_lines_raise_ledger_error_with_the_line_number[attempt` |
| 16 | `src/dsdk/worlds/buildlog.py:127` | compare | `tests/worlds/test_worlds_buildlog.py::test_sample_loads_as_typed_records` |
| 17 | `src/dsdk/worlds/buildlog.py:130` | negate-if | `tests/worlds/test_worlds_buildlog.py::test_sample_loads_as_typed_records` |
| 18 | `src/dsdk/worlds/buildlog.py:133` | negate-if | `tests/worlds/test_worlds_buildlog.py::test_sample_loads_as_typed_records` |
| 19 | `src/dsdk/worlds/buildlog.py:133` | compare | `tests/worlds/test_worlds_buildlog.py::test_sample_loads_as_typed_records` |
| 20 | `src/dsdk/worlds/buildlog.py:138` | negate-if | `tests/worlds/test_worlds_buildlog.py::test_sample_loads_as_typed_records` |
| 21 | `src/dsdk/worlds/buildlog.py:142` | negate-if | `tests/worlds/test_worlds_buildlog.py::test_sample_loads_as_typed_records` |
| 22 | `src/dsdk/worlds/buildlog.py:142` | boolop | `tests/worlds/test_worlds_buildlog.py::test_sample_loads_as_typed_records` |
| 23 | `src/dsdk/worlds/buildlog.py:142` | compare | `tests/worlds/test_worlds_buildlog.py::test_sample_loads_as_typed_records` |
| 24 | `src/dsdk/worlds/buildlog.py:142` | drop-not | `tests/worlds/test_worlds_buildlog.py::test_sample_loads_as_typed_records` |
| 25 | `src/dsdk/worlds/buildlog.py:145` | drop-not | `tests/worlds/test_worlds_buildlog.py::test_sample_loads_as_typed_records` |
| 26 | `src/dsdk/worlds/buildlog.py:190` | compare | `tests/worlds/test_worlds_buildlog.py::test_first_try_rate_known` |
| 27 | `src/dsdk/worlds/buildlog.py:191` | return-none | `tests/worlds/test_worlds_buildlog.py::test_not_observed_unknown_and_invalid_stay_distinct` |
| 28 | `src/dsdk/worlds/buildlog.py:192` | drop-not | `tests/worlds/test_worlds_buildlog.py::test_first_try_rate_known` |
| 29 | `src/dsdk/worlds/buildlog.py:192` | compare | `tests/worlds/test_worlds_buildlog.py::test_first_try_rate_known` |
| 30 | `src/dsdk/worlds/buildlog.py:192` | int+1 | `tests/worlds/test_worlds_buildlog.py::test_first_try_rate_known` |
| 31 | `src/dsdk/worlds/buildlog.py:198` | negate-if | `tests/worlds/test_worlds_buildlog.py::test_first_try_rate_known` |
| 32 | `src/dsdk/worlds/buildlog.py:198` | int+1 | `tests/worlds/test_worlds_buildlog.py::test_first_try_rate_known` |
| 33 | `src/dsdk/worlds/buildlog.py:200` | compare | `tests/worlds/test_worlds_buildlog.py::test_first_try_rate_known` |
| 34 | `src/dsdk/worlds/buildlog.py:203` | compare | `tests/worlds/test_worlds_buildlog.py::test_first_try_rate_known` |
| 35 | `src/dsdk/worlds/buildlog.py:205` | negate-if | `tests/worlds/test_worlds_buildlog.py::test_first_try_rate_known` |
| 36 | `src/dsdk/worlds/buildlog.py:205` | compare | `tests/worlds/test_worlds_buildlog.py::test_zero_percent_is_a_known_value_not_a_missing_one` |
| 37 | `src/dsdk/worlds/buildlog.py:206` | return-none | `tests/worlds/test_worlds_buildlog.py::test_not_observed_unknown_and_invalid_stay_distinct` |
| 38 | `src/dsdk/worlds/buildlog.py:207` | return-none | `tests/worlds/test_worlds_buildlog.py::test_first_try_rate_known` |
| 39 | `src/dsdk/worlds/buildlog.py:248` | negate-if | `tests/worlds/test_worlds_buildlog_summary.py::test_haiku_first_try_summary_on_the_sample_is_nine_of_ten_with_the_textbook_exact_interval` |
| 40 | `src/dsdk/worlds/buildlog.py:248` | boolop | `tests/worlds/test_worlds_buildlog_summary.py::test_no_first_attempts_is_not_observed_and_a_bad_question_is_invalid` |
| 41 | `src/dsdk/worlds/buildlog.py:248` | compare | `tests/worlds/test_worlds_buildlog_summary.py::test_haiku_first_try_summary_on_the_sample_is_nine_of_ten_with_the_textbook_exact_interval` |
| 42 | `src/dsdk/worlds/buildlog.py:249` | return-none | `tests/worlds/test_worlds_buildlog_summary.py::test_no_first_attempts_is_not_observed_and_a_bad_question_is_invalid` |
| 43 | `src/dsdk/worlds/buildlog.py:250` | negate-if | `tests/worlds/test_worlds_buildlog_summary.py::test_haiku_first_try_summary_on_the_sample_is_nine_of_ten_with_the_textbook_exact_interval` |
| 44 | `src/dsdk/worlds/buildlog.py:251` | boolop | `tests/worlds/test_worlds_buildlog_summary.py::test_no_first_attempts_is_not_observed_and_a_bad_question_is_invalid` |
| 45 | `src/dsdk/worlds/buildlog.py:255` | return-none | `tests/worlds/test_worlds_buildlog_summary.py::test_no_first_attempts_is_not_observed_and_a_bad_question_is_invalid` |
| 46 | `src/dsdk/worlds/buildlog.py:262` | negate-if | `tests/worlds/test_worlds_buildlog_summary.py::test_haiku_first_try_summary_on_the_sample_is_nine_of_ten_with_the_textbook_exact_interval` |
| 47 | `src/dsdk/worlds/buildlog.py:266` | return-none | `tests/worlds/test_worlds_buildlog_summary.py::test_no_first_attempts_is_not_observed_and_a_bad_question_is_invalid` |
| 48 | `src/dsdk/worlds/buildlog.py:306` | negate-if | `tests/worlds/test_worlds_buildlog_summary.py::test_round_throughput_on_the_sample_matches_the_hand_count` |
| 49 | `src/dsdk/worlds/buildlog.py:313` | compare | `tests/worlds/test_worlds_buildlog_summary.py::test_round_throughput_on_the_sample_matches_the_hand_count` |
| 50 | `src/dsdk/worlds/buildlog.py:313` | int+1 | `tests/worlds/test_worlds_buildlog_summary.py::test_round_throughput_on_the_sample_matches_the_hand_count` |
| 51 | `src/dsdk/worlds/buildlog.py:314` | boolop | `tests/worlds/test_worlds_buildlog_summary.py::test_round_throughput_on_the_sample_matches_the_hand_count` |
| 52 | `src/dsdk/worlds/buildlog.py:314` | compare | `tests/worlds/test_worlds_buildlog_summary.py::test_round_throughput_on_the_sample_matches_the_hand_count` |
| 53 | `src/dsdk/worlds/buildlog.py:319` | int+1 | `tests/worlds/test_worlds_buildlog_summary.py::test_round_throughput_on_the_sample_matches_the_hand_count` |
| 54 | `src/dsdk/worlds/buildlog.py:321` | int+1 | `tests/worlds/test_worlds_buildlog_summary.py::test_round_throughput_on_the_sample_matches_the_hand_count` |
| 55 | `src/dsdk/worlds/buildlog.py:321` | compare | `tests/worlds/test_worlds_buildlog_summary.py::test_round_throughput_on_the_sample_matches_the_hand_count` |
| 56 | `src/dsdk/worlds/wumpus.py:56` | int+1 | `tests/worlds/test_worlds_wumpus.py::test_the_random_stream_matches_the_pages_mulberry32_to_ten_decimals` |
| 57 | `src/dsdk/worlds/wumpus.py:65` | int+1 | `tests/worlds/test_worlds_wumpus.py::test_the_random_stream_matches_the_pages_mulberry32_to_ten_decimals` |
| 58 | `src/dsdk/worlds/wumpus.py:66` | int+1 | `tests/worlds/test_worlds_wumpus.py::test_the_random_stream_matches_the_pages_mulberry32_to_ten_decimals` |
| 59 | `src/dsdk/worlds/wumpus.py:68` | int+1 | `tests/worlds/test_worlds_wumpus.py::test_the_random_stream_matches_the_pages_mulberry32_to_ten_decimals` |
| 60 | `src/dsdk/worlds/wumpus.py:70` | return-none | `tests/worlds/test_worlds_wumpus.py::test_the_random_stream_matches_the_pages_mulberry32_to_ten_decimals` |
| 61 | `src/dsdk/worlds/wumpus.py:82` | return-none | `tests/worlds/test_worlds_wumpus.py::test_the_demo_cave_is_the_fixture_cave` |
| 62 | `src/dsdk/worlds/wumpus.py:82` | int+1 | `tests/worlds/test_worlds_wumpus.py::test_the_demo_cave_is_the_fixture_cave` |
| 63 | `src/dsdk/worlds/wumpus.py:82` | int+1 | `tests/worlds/test_worlds_wumpus.py::test_the_demo_cave_is_the_fixture_cave` |
| 64 | `src/dsdk/worlds/wumpus.py:87` | int+1 | `tests/worlds/test_worlds_wumpus.py::test_seeded_caves_match_the_pages_generator` |
| 65 | `src/dsdk/worlds/wumpus.py:87` | int+1 | `tests/worlds/test_worlds_wumpus.py::test_seeded_caves_match_the_pages_generator` |
| 66 | `src/dsdk/worlds/wumpus.py:87` | binop | `tests/worlds/test_worlds_wumpus.py::test_seeded_caves_match_the_pages_generator` |
| 67 | `src/dsdk/worlds/wumpus.py:87` | int+1 | `tests/worlds/test_worlds_wumpus.py::test_seeded_caves_match_the_pages_generator` |
| 68 | `src/dsdk/worlds/wumpus.py:87` | compare | `tests/worlds/test_worlds_wumpus.py::test_seeded_caves_match_the_pages_generator` |
| 69 | `src/dsdk/worlds/wumpus.py:90` | binop | `tests/worlds/test_worlds_wumpus.py::test_seeded_caves_match_the_pages_generator` |
| 70 | `src/dsdk/worlds/wumpus.py:96` | int+1 | `tests/worlds/test_worlds_wumpus.py::test_neighbours_are_the_orthogonal_squares_inside_the_cave_in_sorted_order` |
| 71 | `src/dsdk/worlds/wumpus.py:96` | binop | `tests/worlds/test_worlds_wumpus.py::test_neighbours_are_the_orthogonal_squares_inside_the_cave_in_sorted_order` |
| 72 | `src/dsdk/worlds/wumpus.py:96` | int+1 | `tests/worlds/test_worlds_wumpus.py::test_neighbours_are_the_orthogonal_squares_inside_the_cave_in_sorted_order` |
| 73 | `src/dsdk/worlds/wumpus.py:96` | int+1 | `tests/worlds/test_worlds_wumpus.py::test_neighbours_are_the_orthogonal_squares_inside_the_cave_in_sorted_order` |
| 74 | `src/dsdk/worlds/wumpus.py:110` | boolop | `tests/worlds/test_worlds_wumpus.py::test_percepts_in_the_demo_cave` |
| 75 | `src/dsdk/worlds/wumpus.py:111` | boolop | `tests/worlds/test_worlds_wumpus.py::test_percepts_in_the_demo_cave` |
| 76 | `src/dsdk/worlds/wumpus.py:111` | compare | `tests/worlds/test_worlds_wumpus.py::test_percepts_in_the_demo_cave` |
| 77 | `src/dsdk/worlds/wumpus.py:122` | return-none | `tests/worlds/test_worlds_wumpus.py::test_frontier_is_the_unvisited_squares_next_to_visited_ones_sorted` |
| 78 | `src/dsdk/worlds/wumpus.py:131` | compare | `tests/worlds/test_worlds_wumpus.py::test_knowledge_sentences_for_the_demo_stuck_state` |
| 79 | `src/dsdk/worlds/wumpus.py:132` | negate-if | `tests/worlds/test_worlds_wumpus.py::test_knowledge_sentences_for_the_demo_stuck_state` |
| 80 | `src/dsdk/worlds/wumpus.py:137` | negate-if | `tests/worlds/test_worlds_wumpus.py::test_knowledge_sentences_for_the_demo_stuck_state` |
| 81 | `src/dsdk/worlds/wumpus.py:142` | return-none | `tests/worlds/test_worlds_wumpus.py::test_knowledge_sentences_for_the_demo_stuck_state` |
| 82 | `src/dsdk/worlds/wumpus.py:184` | negate-if | `tests/worlds/test_worlds_wumpus.py::test_risk_with_a_breeze_at_the_start_is_five_ninths_for_each_neighbour` |
| 83 | `src/dsdk/worlds/wumpus.py:187` | negate-if | `tests/worlds/test_worlds_wumpus.py::test_risk_with_a_breeze_at_the_start_is_five_ninths_for_each_neighbour` |
| 84 | `src/dsdk/worlds/wumpus.py:187` | drop-not | `tests/worlds/test_worlds_wumpus.py::test_risk_with_a_breeze_at_the_start_is_five_ninths_for_each_neighbour` |
| 85 | `src/dsdk/worlds/wumpus.py:188` | return-none | `tests/worlds/test_worlds_wumpus.py::test_a_fully_explored_cave_has_an_empty_frontier` |
| 86 | `src/dsdk/worlds/wumpus.py:188` | int+1 | `tests/worlds/test_worlds_wumpus.py::test_a_fully_explored_cave_has_an_empty_frontier` |
| 87 | `src/dsdk/worlds/wumpus.py:202` | negate-if | `tests/worlds/test_worlds_wumpus.py::test_risk_with_a_breeze_at_the_start_is_five_ninths_for_each_neighbour` |
| 88 | `src/dsdk/worlds/wumpus.py:203` | return-none | `tests/worlds/test_worlds_wumpus.py::test_contradictory_pit_percepts_are_invalid_not_a_number` |
| 89 | `src/dsdk/worlds/wumpus.py:207` | binop | `tests/worlds/test_worlds_wumpus.py::test_risk_with_a_breeze_at_the_start_is_five_ninths_for_each_neighbour` |
| 90 | `src/dsdk/worlds/wumpus.py:207` | binop | `tests/worlds/test_worlds_wumpus.py::test_risk_with_a_breeze_at_the_start_is_five_ninths_for_each_neighbour` |
| 91 | `src/dsdk/worlds/wumpus.py:207` | binop | `tests/worlds/test_worlds_wumpus.py::test_risk_with_a_breeze_at_the_start_is_five_ninths_for_each_neighbour` |
| 92 | `src/dsdk/worlds/wumpus.py:207` | int+1 | `tests/worlds/test_worlds_wumpus.py::test_risk_with_a_breeze_at_the_start_is_five_ninths_for_each_neighbour` |
| 93 | `src/dsdk/worlds/wumpus.py:211` | negate-if | `tests/worlds/test_worlds_wumpus.py::test_risk_with_a_breeze_at_the_start_is_five_ninths_for_each_neighbour` |
| 95 | `src/dsdk/worlds/wumpus.py:213` | return-none | `tests/worlds/test_worlds_wumpus.py::test_risk_with_a_breeze_at_the_start_is_five_ninths_for_each_neighbour` |
| 96 | `src/dsdk/worlds/wumpus.py:221` | return-none | `tests/worlds/test_worlds_wumpus.py::test_provably_safe_squares` |
| 97 | `src/dsdk/worlds/wumpus.py:235` | flip-bool | `tests/worlds/test_worlds_wumpus.py::test_the_logic_agent_on_the_demo_cave_gets_stuck_and_leaves` |
| 98 | `src/dsdk/worlds/wumpus.py:255` | negate-if | `tests/worlds/test_worlds_wumpus.py::test_risk_matches_a_brute_force_oracle_on_every_stuck_state_of_forty_caves` |
| 99 | `src/dsdk/worlds/wumpus.py:263` | negate-if | `tests/worlds/test_worlds_wumpus.py::test_the_logic_agent_on_the_demo_cave_gets_stuck_and_leaves` |
| 100 | `src/dsdk/worlds/wumpus.py:266` | compare | `tests/worlds/test_worlds_wumpus.py::test_risk_matches_a_brute_force_oracle_on_every_stuck_state_of_forty_caves` |
| 101 | `src/dsdk/worlds/wumpus.py:268` | int+1 | `tests/worlds/test_worlds_wumpus.py::test_the_probabilistic_agent_can_survive_a_gamble_and_still_leave_empty_handed` |
| 102 | `src/dsdk/worlds/wumpus.py:269` | negate-if | `tests/worlds/test_worlds_wumpus.py::test_risk_matches_a_brute_force_oracle_on_every_stuck_state_of_forty_caves` |
| 103 | `src/dsdk/worlds/wumpus.py:269` | drop-not | `tests/worlds/test_worlds_wumpus.py::test_risk_matches_a_brute_force_oracle_on_every_stuck_state_of_forty_caves` |
| 104 | `src/dsdk/worlds/wumpus.py:270` | return-none | `tests/worlds/test_worlds_wumpus.py::test_risk_matches_a_brute_force_oracle_on_every_stuck_state_of_forty_caves` |
| 105 | `src/dsdk/worlds/wumpus.py:274` | boolop | `tests/worlds/test_worlds_wumpus.py::test_risk_matches_a_brute_force_oracle_on_every_stuck_state_of_forty_caves` |
| 106 | `src/dsdk/worlds/wumpus.py:274` | compare | `tests/worlds/test_worlds_wumpus.py::test_the_probabilistic_agent_on_the_demo_cave_takes_the_least_risky_step_and_dies` |
| 107 | `src/dsdk/worlds/wumpus.py:275` | return-none | `tests/worlds/test_worlds_wumpus.py::test_risk_matches_a_brute_force_oracle_on_every_stuck_state_of_forty_caves` |
| 108 | `src/dsdk/worlds/wumpus.py:294` | int+1 | `tests/worlds/test_worlds_wumpus.py::test_death_and_escape_rates_over_three_hundred_seeds` |
| 109 | `src/dsdk/worlds/wumpus.py:295` | negate-if | `tests/worlds/test_worlds_wumpus.py::test_death_and_escape_rates_over_three_hundred_seeds` |
| 110 | `src/dsdk/worlds/wumpus.py:295` | compare | `tests/worlds/test_worlds_wumpus.py::test_death_and_escape_rates_over_three_hundred_seeds` |
| 111 | `src/dsdk/worlds/wumpus.py:296` | int+1 | `tests/worlds/test_worlds_wumpus.py::test_death_and_escape_rates_over_three_hundred_seeds` |
| 112 | `src/dsdk/worlds/wumpus.py:299` | return-none | `tests/worlds/test_worlds_wumpus.py::test_the_logic_agent_never_dies_on_seeds_one_to_three_hundred` |
| 113 | `src/dsdk/worlds/wumpus.py:303` | return-none | `tests/worlds/test_worlds_wumpus.py::test_lab_data_has_a_risk_table_for_every_stuck_state_either_agent_reaches` |
| 114 | `src/dsdk/worlds/wumpus.py:306` | int+1 | `tests/worlds/test_worlds_wumpus.py::test_lab_data_has_a_risk_table_for_every_stuck_state_either_agent_reaches` |
| 115 | `src/dsdk/worlds/wumpus.py:314` | binop | `tests/worlds/test_worlds_wumpus.py::test_lab_data_has_a_risk_table_for_every_stuck_state_either_agent_reaches` |
| 116 | `src/dsdk/worlds/wumpus.py:315` | flip-bool | `tests/worlds/test_worlds_wumpus.py::test_lab_data_has_a_risk_table_for_every_stuck_state_either_agent_reaches` |
| 117 | `src/dsdk/worlds/wumpus.py:318` | negate-if | `tests/worlds/test_worlds_wumpus.py::test_lab_data_has_a_risk_table_for_every_stuck_state_either_agent_reaches` |
| 118 | `src/dsdk/worlds/wumpus.py:321` | compare | `tests/worlds/test_worlds_wumpus.py::test_lab_data_has_a_risk_table_for_every_stuck_state_either_agent_reaches` |
| 119 | `src/dsdk/worlds/wumpus.py:328` | flip-bool | `tests/worlds/test_worlds_wumpus.py::test_lab_data_rates_and_prior_and_size` |
