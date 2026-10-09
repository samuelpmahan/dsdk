# Mutation evidence: dsdk.prob (A3)

Commit `d7eaad01b20b`. 712 mutation sites in the shipped source; 120 sampled with seed 20261009.
**119 killed, 1 survived** (99% kill rate).

Reproduce: `.venv/bin/python tools/mutants/run.py dsdk.prob 'tests/prob tests/integration/test_prob_text.py tests/integration/test_prob_expectation.py' --max 120 --seed 20261009`

A survivor is either equivalent (no observable change) or a test gap. Each one is listed for triage.

## Survivors

| # | Where | Kind | Original | Mutant |
|---|---|---|---|---|
| 61 | `src/dsdk/prob/sampling.py:388` | compare | `_binom_tail_le(n, k, mid, logc) > half` | `_binom_tail_le(n, k, mid, logc) >= half` |

## Killed (first failing test)

| # | Where | Kind | Killed by |
|---|---|---|---|
| 0 | `src/dsdk/prob/ask.py:49` | binop | `tests/integration/test_prob_text.py::test_unparseable_query_text_is_invalid_and_names_the_offset[A` |
| 1 | `src/dsdk/prob/ask.py:61` | compare | `tests/integration/test_prob_text.py::test_the_headline_question_as_text_gives_five_ninths` |
| 2 | `src/dsdk/prob/ask.py:63` | compare | `tests/integration/test_prob_text.py::test_the_headline_question_as_text_gives_five_ninths` |
| 3 | `src/dsdk/prob/ask.py:94` | negate-if | `tests/integration/test_prob_text.py::test_text_questions_on_the_sprinkler_network_give_the_textbook_values` |
| 4 | `src/dsdk/prob/ask.py:98` | return-none | `tests/integration/test_prob_text.py::test_net_questions_with_bad_text_or_unknown_node_or_impossible_evidence` |
| 5 | `src/dsdk/prob/ask.py:113` | negate-if | `tests/integration/test_prob_text.py::test_compare_text_puts_the_exact_value_next_to_a_seeded_estimate` |
| 6 | `src/dsdk/prob/ask.py:127` | return-none | `tests/integration/test_prob_text.py::test_observing_text_that_does_not_parse_leaves_the_store_untouched` |
| 7 | `src/dsdk/prob/bayesnet.py:78` | negate-if | `tests/prob/test_sampling_worlds.py` |
| 8 | `src/dsdk/prob/bayesnet.py:94` | compare | `tests/prob/test_sampling_worlds.py` |
| 9 | `src/dsdk/prob/bayesnet.py:114` | flip-bool | `tests/prob/test_bayesnet_build.py::test_parent_order_is_the_graphs_node_order_not_the_edge_listing_order` |
| 10 | `src/dsdk/prob/bayesnet.py:115` | int+1 | `tests/prob/test_bayesnet_build.py::test_single_node_and_isolated_nodes_are_fine` |
| 11 | `src/dsdk/prob/bayesnet.py:118` | int+1 | `tests/prob/test_bayesnet_build.py::test_parent_order_is_the_graphs_node_order_not_the_edge_listing_order` |
| 12 | `src/dsdk/prob/bayesnet.py:140` | negate-if | `tests/prob/test_bayesnet_graph.py::test_ancestral_net_of_a_leaf_keeps_only_what_it_depends_on` |
| 13 | `src/dsdk/prob/bayesnet.py:142` | drop-not | `tests/prob/test_bayesnet_graph.py::test_ancestral_net_of_a_leaf_keeps_only_what_it_depends_on` |
| 14 | `src/dsdk/prob/bayesnet.py:145` | negate-if | `tests/prob/test_bayesnet_graph.py::test_ancestral_net_of_a_leaf_keeps_only_what_it_depends_on` |
| 15 | `src/dsdk/prob/bayesnet.py:154` | boolop | `tests/prob/test_bayesnet_graph.py::test_ancestral_net_of_a_leaf_keeps_only_what_it_depends_on` |
| 16 | `src/dsdk/prob/exact.py:26` | negate-if | `tests/prob/test_sampling_worlds.py` |
| 17 | `src/dsdk/prob/expect.py:63` | negate-if | `tests/integration/test_prob_expectation.py::test_expected_number_of_pits_among_p22_and_p31_is_ten_ninths` |
| 18 | `src/dsdk/prob/expect.py:66` | negate-if | `tests/integration/test_prob_expectation.py::test_expected_number_of_pits_among_p22_and_p31_is_ten_ninths` |
| 19 | `src/dsdk/prob/expect.py:67` | return-none | `tests/integration/test_prob_expectation.py::test_a_type_error_is_invalid_with_the_type_checkers_own_reason` |
| 20 | `src/dsdk/prob/expect.py:89` | drop-not | `tests/integration/test_prob_expectation.py::test_expected_number_of_pits_among_p22_and_p31_is_ten_ninths` |
| 21 | `src/dsdk/prob/expect.py:94` | negate-if | `tests/integration/test_prob_expectation.py::test_expected_number_of_pits_among_p22_and_p31_is_ten_ninths` |
| 22 | `src/dsdk/prob/expect.py:94` | compare | `tests/integration/test_prob_expectation.py::test_expected_number_of_pits_among_p22_and_p31_is_ten_ninths` |
| 23 | `src/dsdk/prob/expect.py:137` | compare | `tests/integration/test_prob_expectation.py::test_the_sampled_estimate_is_within_four_standard_errors_of_ten_ninths` |
| 24 | `src/dsdk/prob/expect.py:138` | return-none | `tests/integration/test_prob_expectation.py::test_sampling_verdicts_for_zero_draws_dead_belief_and_text_problems` |
| 25 | `src/dsdk/prob/sampling.py:42` | drop-not | `tests/prob/test_exact_interval.py::test_the_exact_interval_matches_known_values_to_four_decimals[5-10-0.1871-0.8129]` |
| 26 | `src/dsdk/prob/sampling.py:44` | compare | `tests/prob/test_exact_interval.py::test_the_exact_interval_matches_known_values_to_four_decimals[0-10-0.0-0.3085]` |
| 27 | `src/dsdk/prob/sampling.py:52` | int+1 | `tests/prob/test_sampling_stats.py::test_standard_error_known_values` |
| 28 | `src/dsdk/prob/sampling.py:72` | int+1 | `tests/prob/test_sampling_stats.py::test_wilson_does_not_collapse_at_the_extremes_unlike_the_plain_interval` |
| 29 | `src/dsdk/prob/sampling.py:73` | int+1 | `tests/prob/test_exact_interval.py::test_the_wilson_interval_fails_the_same_coverage_test[10]` |
| 30 | `src/dsdk/prob/sampling.py:74` | negate-if | `tests/prob/test_exact_interval.py::test_the_wilson_interval_fails_the_same_coverage_test[10]` |
| 31 | `src/dsdk/prob/sampling.py:76` | drop-not | `tests/prob/test_exact_interval.py::test_the_wilson_interval_fails_the_same_coverage_test[10]` |
| 32 | `src/dsdk/prob/sampling.py:82` | int+1 | `tests/prob/test_exact_interval.py::test_the_exact_interval_is_wider_than_wilson_at_the_centre_and_at_zero_successes` |
| 33 | `src/dsdk/prob/sampling.py:85` | binop | `tests/prob/test_sampling_stats.py::test_wilson_known_values` |
| 34 | `src/dsdk/prob/sampling.py:89` | negate-if | `tests/prob/test_exact_interval.py::test_the_exact_interval_is_wider_than_wilson_at_the_centre_and_at_zero_successes` |
| 35 | `src/dsdk/prob/sampling.py:89` | compare | `tests/prob/test_exact_interval.py::test_the_exact_interval_is_wider_than_wilson_at_the_centre_and_at_zero_successes` |
| 36 | `src/dsdk/prob/sampling.py:117` | int+1 | `tests/prob/test_sampling_stats.py::test_make_estimate_accepts_a_single_trial` |
| 37 | `src/dsdk/prob/sampling.py:119` | compare | `tests/prob/test_sampling_stats.py::test_make_estimate_accepts_a_single_trial` |
| 38 | `src/dsdk/prob/sampling.py:175` | int+1 | `tests/prob/test_sampling_stats.py::test_draws_match_the_documented_algorithm` |
| 39 | `src/dsdk/prob/sampling.py:178` | negate-if | `tests/prob/test_sampling_stats.py::test_draws_match_the_documented_algorithm` |
| 40 | `src/dsdk/prob/sampling.py:201` | int+1 | `tests/prob/test_sampling_worlds.py::test_sample_zero_draws_is_known_empty` |
| 41 | `src/dsdk/prob/sampling.py:226` | negate-if | `tests/prob/test_sampling_worlds.py::test_unconditional_estimate_counts_hits_among_the_draws` |
| 42 | `src/dsdk/prob/sampling.py:238` | binop | `tests/prob/test_sampling_worlds.py::test_unmodelled_variables_are_unknown_with_the_probability_reason` |
| 43 | `src/dsdk/prob/sampling.py:242` | int+1 | `tests/prob/test_sampling_worlds.py::test_unconditional_estimate_counts_hits_among_the_draws` |
| 44 | `src/dsdk/prob/sampling.py:243` | int+1 | `tests/prob/test_sampling_worlds.py::test_unconditional_estimate_counts_hits_among_the_draws` |
| 45 | `src/dsdk/prob/sampling.py:271` | negate-if | `tests/prob/test_sampling_worlds.py::test_comparison_pairs_the_exact_fraction_with_the_estimate` |
| 46 | `src/dsdk/prob/sampling.py:272` | return-none | `tests/prob/test_sampling_worlds.py::test_sampler_unknown_passes_through_when_exact_is_known` |
| 47 | `src/dsdk/prob/sampling.py:289` | boolop | `tests/prob/test_sampling_worlds.py::test_forward_sample_argument_errors[args3]` |
| 48 | `src/dsdk/prob/sampling.py:313` | binop | `tests/prob/test_exact_interval.py::test_the_exact_interval_matches_known_values_to_four_decimals[5-10-0.1871-0.8129]` |
| 49 | `src/dsdk/prob/sampling.py:313` | int+1 | `tests/prob/test_exact_interval.py::test_the_exact_interval_matches_known_values_to_four_decimals[5-10-0.1871-0.8129]` |
| 50 | `src/dsdk/prob/sampling.py:313` | int+1 | `tests/prob/test_exact_interval.py::test_the_exact_interval_matches_known_values_to_four_decimals[5-10-0.1871-0.8129]` |
| 51 | `src/dsdk/prob/sampling.py:324` | binop | `tests/prob/test_exact_interval.py::test_the_exact_interval_matches_known_values_to_four_decimals[5-10-0.1871-0.8129]` |
| 52 | `src/dsdk/prob/sampling.py:324` | binop | `tests/prob/test_exact_interval.py::test_the_exact_interval_matches_known_values_to_four_decimals[5-10-0.1871-0.8129]` |
| 53 | `src/dsdk/prob/sampling.py:324` | binop | `tests/prob/test_exact_interval.py::test_the_exact_interval_matches_known_values_to_four_decimals[5-10-0.1871-0.8129]` |
| 54 | `src/dsdk/prob/sampling.py:331` | binop | `tests/prob/test_exact_interval.py::test_the_exact_interval_matches_known_values_to_four_decimals[5-10-0.1871-0.8129]` |
| 55 | `src/dsdk/prob/sampling.py:331` | int+1 | `tests/prob/test_exact_interval.py::test_the_exact_interval_matches_known_values_to_four_decimals[5-10-0.1871-0.8129]` |
| 56 | `src/dsdk/prob/sampling.py:363` | compare | `tests/prob/test_exact_interval.py::test_the_exact_interval_matches_known_values_to_four_decimals[10-10-0.6915-1.0]` |
| 57 | `src/dsdk/prob/sampling.py:366` | boolop | `tests/prob/test_exact_interval.py::test_confidence_must_lie_strictly_between_zero_and_one[0-ValueError]` |
| 58 | `src/dsdk/prob/sampling.py:368` | int+1 | `tests/prob/test_exact_interval.py::test_the_exact_interval_matches_known_values_to_four_decimals[5-10-0.1871-0.8129]` |
| 59 | `src/dsdk/prob/sampling.py:372` | int+1 | `tests/prob/test_exact_interval.py::test_the_exact_interval_matches_known_values_to_four_decimals[1-10-0.0025-0.445]` |
| 60 | `src/dsdk/prob/sampling.py:384` | negate-if | `tests/prob/test_exact_interval.py::test_the_exact_interval_matches_known_values_to_four_decimals[5-10-0.1871-0.8129]` |
| 62 | `src/dsdk/prob/sampling.py:404` | binop | `tests/prob/test_prob_exact_interval_speed.py::test_the_slow_exact_fraction_version_is_kept_as_a_private_reference_and_still_reproduces_the_fixture_bit_for_bit` |
| 63 | `src/dsdk/prob/sampling.py:404` | int+1 | `tests/prob/test_prob_exact_interval_speed.py::test_the_slow_exact_fraction_version_is_kept_as_a_private_reference_and_still_reproduces_the_fixture_bit_for_bit` |
| 64 | `src/dsdk/prob/sampling.py:404` | binop | `tests/prob/test_prob_exact_interval_speed.py::test_the_slow_exact_fraction_version_is_kept_as_a_private_reference_and_still_reproduces_the_fixture_bit_for_bit` |
| 65 | `src/dsdk/prob/sampling.py:409` | int+1 | `tests/prob/test_prob_exact_interval_speed.py::test_the_slow_exact_fraction_version_is_kept_as_a_private_reference_and_still_reproduces_the_fixture_bit_for_bit` |
| 66 | `src/dsdk/prob/sampling.py:420` | int+1 | `tests/prob/test_prob_exact_interval_speed.py::test_the_slow_exact_fraction_version_is_kept_as_a_private_reference_and_still_reproduces_the_fixture_bit_for_bit` |
| 67 | `src/dsdk/prob/sampling.py:421` | int+1 | `tests/prob/test_prob_exact_interval_speed.py::test_the_slow_exact_fraction_version_is_kept_as_a_private_reference_and_still_reproduces_the_fixture_bit_for_bit` |
| 68 | `src/dsdk/prob/sampling.py:425` | compare | `tests/prob/test_prob_exact_interval_speed.py::test_the_slow_exact_fraction_version_is_kept_as_a_private_reference_and_still_reproduces_the_fixture_bit_for_bit` |
| 69 | `src/dsdk/prob/sampling.py:425` | compare | `tests/prob/test_prob_exact_interval_speed.py::test_the_slow_exact_fraction_version_is_kept_as_a_private_reference_and_still_reproduces_the_fixture_bit_for_bit` |
| 70 | `src/dsdk/prob/sampling.py:427` | int+1 | `tests/prob/test_prob_exact_interval_speed.py::test_the_slow_exact_fraction_version_is_kept_as_a_private_reference_and_still_reproduces_the_fixture_bit_for_bit` |
| 71 | `src/dsdk/prob/sampling.py:443` | int+1 | `tests/prob/test_prob_exact_interval_speed.py::test_the_slow_exact_fraction_version_is_kept_as_a_private_reference_and_still_reproduces_the_fixture_bit_for_bit` |
| 72 | `src/dsdk/prob/sampling.py:445` | int+1 | `tests/prob/test_prob_exact_interval_speed.py::test_the_slow_exact_fraction_version_is_kept_as_a_private_reference_and_still_reproduces_the_fixture_bit_for_bit` |
| 73 | `src/dsdk/prob/sampling.py:446` | negate-if | `tests/prob/test_prob_exact_interval_speed.py::test_the_slow_exact_fraction_version_is_kept_as_a_private_reference_and_still_reproduces_the_fixture_bit_for_bit` |
| 74 | `src/dsdk/prob/transitions.py:71` | compare | `tests/prob/test_transitions_sampling.py` |
| 75 | `src/dsdk/prob/transitions.py:98` | drop-not | `tests/prob/test_transitions_model.py::test_model_from_graph_reads_known_edge_weights_as_counts` |
| 76 | `src/dsdk/prob/transitions.py:105` | negate-if | `tests/prob/test_transitions_model.py::test_model_from_graph_reads_known_edge_weights_as_counts` |
| 77 | `src/dsdk/prob/transitions.py:108` | negate-if | `tests/prob/test_transitions_model.py::test_model_from_graph_reads_known_edge_weights_as_counts` |
| 78 | `src/dsdk/prob/transitions.py:117` | drop-not | `tests/prob/test_transitions_model.py::test_model_from_graph_reads_known_edge_weights_as_counts` |
| 79 | `src/dsdk/prob/transitions.py:128` | negate-if | `tests/prob/test_transitions_model.py::test_extra_vocabulary_and_tuples_and_generators_are_accepted` |
| 80 | `src/dsdk/prob/transitions.py:133` | return-none | `tests/prob/test_transitions_model.py::test_alpha_zero_and_nothing_observed_is_unknown_not_uniform` |
| 81 | `src/dsdk/prob/transitions.py:137` | return-none | `tests/prob/test_transitions_model.py::test_extra_vocabulary_and_tuples_and_generators_are_accepted` |
| 82 | `src/dsdk/prob/transitions.py:137` | binop | `tests/prob/test_transitions_model.py::test_extra_vocabulary_and_tuples_and_generators_are_accepted` |
| 83 | `src/dsdk/prob/transitions.py:168` | negate-if | `tests/prob/test_transitions_model.py::test_top_next_orders_by_probability_then_canonical_order` |
| 84 | `src/dsdk/prob/transitions.py:173` | int+1 | `tests/prob/test_transitions_model.py::test_top_next_orders_by_probability_then_canonical_order` |
| 85 | `src/dsdk/prob/transitions.py:175` | return-none | `tests/prob/test_transitions_model.py::test_top_next_orders_by_probability_then_canonical_order` |
| 86 | `src/dsdk/prob/transitions.py:196` | negate-if | `tests/prob/test_transitions_sampling.py::test_comparison_exact_value_and_counts` |
| 87 | `src/dsdk/prob/transitions.py:202` | compare | `tests/prob/test_transitions_sampling.py::test_comparison_exact_value_and_counts` |
| 88 | `src/dsdk/prob/transitions.py:204` | compare | `tests/prob/test_transitions_sampling.py::test_comparison_exact_value_and_counts` |
| 89 | `src/dsdk/prob/transitions.py:218` | drop-not | `tests/prob/test_transitions_sampling.py::test_log_loss_by_hand` |
| 90 | `src/dsdk/prob/transitions.py:222` | negate-if | `tests/prob/test_transitions_sampling.py::test_log_loss_by_hand` |
| 91 | `src/dsdk/prob/transitions.py:224` | negate-if | `tests/prob/test_transitions_sampling.py::test_log_loss_by_hand` |
| 92 | `src/dsdk/prob/transitions.py:224` | drop-not | `tests/prob/test_transitions_sampling.py::test_log_loss_by_hand` |
| 93 | `src/dsdk/prob/transitions.py:225` | return-none | `tests/prob/test_transitions_sampling.py::test_no_pairs_is_unknown` |
| 94 | `src/dsdk/prob/transitions.py:228` | negate-if | `tests/prob/test_transitions_sampling.py::test_log_loss_by_hand` |
| 95 | `src/dsdk/prob/transitions.py:228` | compare | `tests/prob/test_transitions_sampling.py::test_log_loss_by_hand` |
| 96 | `src/dsdk/prob/transitions.py:234` | compare | `tests/prob/test_transitions_sampling.py::test_log_loss_by_hand` |
| 97 | `src/dsdk/prob/transitions.py:238` | int+1 | `tests/prob/test_transitions_sampling.py::test_smoothing_rescues_a_held_out_transition_the_raw_model_calls_impossible` |
| 98 | `src/dsdk/prob/updates.py:53` | compare | `tests/prob/test_updates.py::test_start_series_binds_a_raw_part_at_belief_0` |
| 99 | `src/dsdk/prob/updates.py:109` | binop | `tests/prob/test_updates.py::test_unmodelled_evidence_is_unknown_and_leaves_no_trace` |
| 100 | `src/dsdk/prob/updates.py:111` | int+1 | `tests/prob/test_updates.py::test_impossible_evidence_is_invalid_and_leaves_no_trace` |
| 101 | `src/dsdk/prob/updates.py:112` | return-none | `tests/prob/test_updates.py::test_impossible_evidence_is_invalid_and_leaves_no_trace` |
| 102 | `src/dsdk/prob/updates.py:116` | return-none | `tests/prob/test_updates.py::test_observe_returns_known_with_the_new_belief_part_bound_at_belief_1` |
| 103 | `src/dsdk/prob/worlds.py:67` | compare | `tests/prob/test_sampling_worlds.py` |
| 104 | `src/dsdk/prob/worlds.py:123` | negate-if | `tests/prob/test_bayesnet_build.py::test_parent_order_is_the_graphs_node_order_not_the_edge_listing_order` |
| 105 | `src/dsdk/prob/worlds.py:155` | drop-not | `tests/prob/test_prob_reuse.py::test_worlds_are_exactly_the_logic_models_not_a_second_enumeration` |
| 106 | `src/dsdk/prob/worlds.py:187` | negate-if | `tests/prob/test_sampling_worlds.py` |
| 107 | `src/dsdk/prob/worlds.py:187` | drop-not | `tests/prob/test_sampling_worlds.py` |
| 108 | `src/dsdk/prob/worlds.py:206` | drop-not | `tests/prob/test_sampling_worlds.py` |
| 109 | `src/dsdk/prob/worlds.py:226` | negate-if | `tests/prob/test_bayesnet_build.py::test_parent_order_is_the_graphs_node_order_not_the_edge_listing_order` |
| 110 | `src/dsdk/prob/worlds.py:228` | drop-not | `tests/prob/test_bayesnet_build.py::test_parent_order_is_the_graphs_node_order_not_the_edge_listing_order` |
| 111 | `src/dsdk/prob/worlds.py:235` | binop | `tests/prob/test_bayesnet_build.py::test_parent_order_is_the_graphs_node_order_not_the_edge_listing_order` |
| 112 | `src/dsdk/prob/worlds.py:237` | return-none | `tests/prob/test_sampling_worlds.py::test_unmodelled_and_dead_belief_pass_through` |
| 113 | `src/dsdk/prob/worlds.py:237` | binop | `tests/prob/test_sampling_worlds.py::test_unmodelled_and_dead_belief_pass_through` |
| 114 | `src/dsdk/prob/worlds.py:241` | return-none | `tests/prob/test_sampling_worlds.py::test_unmodelled_and_dead_belief_pass_through` |
| 115 | `src/dsdk/prob/worlds.py:244` | compare | `tests/prob/test_bayesnet_build.py::test_parent_order_is_the_graphs_node_order_not_the_edge_listing_order` |
| 116 | `src/dsdk/prob/worlds.py:245` | return-none | `tests/prob/test_bayesnet_build.py::test_conditioning_the_joint_on_an_impossible_event_is_invalid` |
| 117 | `src/dsdk/prob/worlds.py:257` | return-none | `tests/prob/test_worlds_query.py::test_conditioning_then_asking_on_impossible_evidence_is_invalid` |
| 118 | `src/dsdk/prob/worlds.py:271` | int+1 | `tests/prob/test_worlds_query.py::test_conditioning_then_asking_on_impossible_evidence_is_invalid` |
| 119 | `src/dsdk/prob/worlds.py:272` | return-none | `tests/prob/test_worlds_query.py::test_conditioning_then_asking_on_impossible_evidence_is_invalid` |
