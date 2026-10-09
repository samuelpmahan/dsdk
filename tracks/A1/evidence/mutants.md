# Mutation evidence: dsdk.logic (A1)

Commit `a52c6ca09116`. 264 mutation sites in the shipped source; 100 sampled with seed 20261009.
**99 killed, 1 survived** (99% kill rate).

Reproduce: `.venv/bin/python tools/mutants/run.py dsdk.logic tests/logic --max 100 --seed 20261009`

A survivor is either equivalent (no observable change) or a test gap. Each one is listed for triage.

## Survivors

| # | Where | Kind | Original | Mutant |
|---|---|---|---|---|
| 67 | `src/dsdk/logic/semantics.py:63` | return-none | `return None` | `return None` |

## Killed (first failing test)

| # | Where | Kind | Killed by |
|---|---|---|---|
| 0 | `src/dsdk/logic/formula.py:67` | compare | `tests/logic/test_fixtures.py::test_to_str_matches_fixture_string[const_true]` |
| 1 | `src/dsdk/logic/formula.py:68` | compare | `tests/logic/test_fixtures.py::test_to_str_matches_fixture_string[const_true]` |
| 2 | `src/dsdk/logic/formula.py:70` | negate-if | `tests/logic/test_fixtures.py::test_to_str_matches_fixture_string[var_a]` |
| 3 | `src/dsdk/logic/formula.py:71` | drop-not | `tests/logic/test_fixtures.py::test_to_str_matches_fixture_string[var_a]` |
| 4 | `src/dsdk/logic/formula.py:73` | negate-if | `tests/logic/test_fixtures.py::test_to_str_matches_fixture_string[var_a]` |
| 5 | `src/dsdk/logic/formula.py:157` | int+1 | `tests/logic/test_fixtures.py::test_variables_and_size_match_fixture[const_true]` |
| 6 | `src/dsdk/logic/formula.py:160` | negate-if | `tests/logic/test_fixtures.py::test_variables_and_size_match_fixture[const_true]` |
| 7 | `src/dsdk/logic/formula.py:163` | return-none | `tests/logic/test_fixtures.py::test_variables_and_size_match_fixture[const_true]` |
| 8 | `src/dsdk/logic/formula.py:171` | flip-bool | `tests/logic/test_fixtures.py::test_to_str_matches_fixture_string[not_a]` |
| 9 | `src/dsdk/logic/formula.py:174` | negate-if | `tests/logic/test_fixtures.py::test_to_str_matches_fixture_string[const_true]` |
| 10 | `src/dsdk/logic/formula.py:180` | negate-if | `tests/logic/test_fixtures.py::test_to_str_matches_fixture_string[not_a]` |
| 11 | `src/dsdk/logic/formula.py:192` | binop | `tests/logic/test_fixtures.py::test_to_str_matches_fixture_string[and_ab]` |
| 12 | `src/dsdk/logic/formula.py:193` | int+1 | `tests/logic/test_fixtures.py::test_to_str_matches_fixture_string[const_true]` |
| 13 | `src/dsdk/logic/proof.py:64` | drop-not | `tests/logic/test_proof.py::test_step_default_cites_is_empty_tuple` |
| 14 | `src/dsdk/logic/proof.py:69` | negate-if | `tests/logic/test_proof.py::test_step_rejects_malformed_fields[<lambda>4]` |
| 15 | `src/dsdk/logic/proof.py:105` | int+1 | `tests/logic/test_proof.py::test_modus_ponens_valid` |
| 16 | `src/dsdk/logic/proof.py:125` | return-none | `tests/logic/test_proof.py::test_premise_step_must_not_cite` |
| 17 | `src/dsdk/logic/proof.py:128` | int+1 | `tests/logic/test_proof.py::test_modus_ponens_valid` |
| 18 | `src/dsdk/logic/proof.py:134` | negate-if | `tests/logic/test_proof.py::test_premises_only_and_repeated_premise` |
| 19 | `src/dsdk/logic/proof.py:134` | compare | `tests/logic/test_proof.py::test_premises_only_and_repeated_premise` |
| 20 | `src/dsdk/logic/proof.py:136` | return-none | `tests/logic/test_proof.py::test_premise_step_must_be_one_of_the_premises` |
| 21 | `src/dsdk/logic/proof.py:137` | compare | `tests/logic/test_proof.py::test_modus_ponens_valid` |
| 22 | `src/dsdk/logic/proof.py:139` | compare | `tests/logic/test_proof.py::test_modus_ponens_valid` |
| 23 | `src/dsdk/logic/proof.py:141` | compare | `tests/logic/test_proof.py::test_modus_tollens_valid` |
| 24 | `src/dsdk/logic/proof.py:143` | negate-if | `tests/logic/test_proof.py::test_modus_tollens_valid` |
| 25 | `src/dsdk/logic/proof.py:143` | drop-not | `tests/logic/test_proof.py::test_modus_tollens_valid` |
| 26 | `src/dsdk/logic/proof.py:143` | boolop | `tests/logic/test_proof.py::test_denying_the_antecedent_is_rejected` |
| 27 | `src/dsdk/logic/proof.py:144` | compare | `tests/logic/test_proof.py::test_modus_tollens_valid` |
| 28 | `src/dsdk/logic/proof.py:146` | negate-if | `tests/logic/test_proof.py::test_and_rules_valid_including_same_cite_twice` |
| 29 | `src/dsdk/logic/proof.py:148` | negate-if | `tests/logic/test_proof.py::test_and_rules_valid_including_same_cite_twice` |
| 30 | `src/dsdk/logic/proof.py:149` | return-none | `tests/logic/test_proof.py::test_and_intro_order_matters` |
| 31 | `src/dsdk/logic/proof.py:150` | compare | `tests/logic/test_proof.py::test_and_rules_valid_including_same_cite_twice` |
| 32 | `src/dsdk/logic/proof.py:152` | negate-if | `tests/logic/test_proof.py::test_and_rules_valid_including_same_cite_twice` |
| 33 | `src/dsdk/logic/proof.py:152` | compare | `tests/logic/test_proof.py::test_and_rules_valid_including_same_cite_twice` |
| 34 | `src/dsdk/logic/proof.py:153` | return-none | `tests/logic/test_proof.py::test_and_elimination_picks_the_right_side[<lambda>-and_elim_left]` |
| 35 | `src/dsdk/logic/proof.py:154` | negate-if | `tests/logic/test_proof.py::test_and_rules_valid_including_same_cite_twice` |
| 36 | `src/dsdk/logic/proof.py:154` | compare | `tests/logic/test_proof.py::test_and_rules_valid_including_same_cite_twice` |
| 37 | `src/dsdk/logic/proof.py:156` | negate-if | `tests/logic/test_proof.py::test_and_rules_valid_including_same_cite_twice` |
| 38 | `src/dsdk/logic/proof.py:156` | compare | `tests/logic/test_proof.py::test_and_rules_valid_including_same_cite_twice` |
| 39 | `src/dsdk/logic/proof.py:157` | return-none | `tests/logic/test_proof.py::test_and_elimination_picks_the_right_side[<lambda>-and_elim_right]` |
| 40 | `src/dsdk/logic/proof.py:160` | boolop | `tests/logic/test_proof.py::test_or_intro_must_keep_the_cited_formula_on_the_correct_side` |
| 41 | `src/dsdk/logic/proof.py:162` | negate-if | `tests/logic/test_proof.py::test_or_introduction_with_arbitrary_other_disjunct` |
| 42 | `src/dsdk/logic/proof.py:162` | compare | `tests/logic/test_proof.py::test_or_introduction_with_arbitrary_other_disjunct` |
| 43 | `src/dsdk/logic/proof.py:164` | negate-if | `tests/logic/test_proof.py::test_or_introduction_with_arbitrary_other_disjunct` |
| 44 | `src/dsdk/logic/proof.py:164` | boolop | `tests/logic/test_proof.py::test_or_intro_must_keep_the_cited_formula_on_the_correct_side` |
| 45 | `src/dsdk/logic/proof.py:165` | return-none | `tests/logic/test_proof.py::test_or_intro_must_keep_the_cited_formula_on_the_correct_side` |
| 46 | `src/dsdk/logic/proof.py:168` | drop-not | `tests/logic/test_proof.py::test_double_negation_elimination_valid_and_odd_depth` |
| 47 | `src/dsdk/logic/proof.py:168` | compare | `tests/logic/test_proof.py::test_double_negation_elimination_valid_and_odd_depth` |
| 48 | `src/dsdk/logic/proof.py:169` | return-none | `tests/logic/test_proof.py::test_double_negation_elim_needs_two_negations` |
| 49 | `src/dsdk/logic/proof.py:175` | flip-bool | `tests/logic/test_proof.py::test_empty_proof_is_valid` |
| 50 | `src/dsdk/logic/semantics.py:35` | return-none | `tests/logic/test_semantics.py::test_evaluate_missing_variable_raises_unassigned` |
| 51 | `src/dsdk/logic/semantics.py:35` | int+1 | `tests/logic/test_semantics.py::test_evaluate_missing_variable_raises_unassigned` |
| 52 | `src/dsdk/logic/semantics.py:41` | negate-if | `tests/logic/test_fixtures.py::test_truth_table_matches_fixture_including_order[var_a]` |
| 53 | `src/dsdk/logic/semantics.py:41` | boolop | `tests/logic/test_fixtures.py::test_truth_table_matches_fixture_including_order[var_a]` |
| 54 | `src/dsdk/logic/semantics.py:41` | compare | `tests/logic/test_semantics.py::test_evaluate_missing_variable_raises_unassigned` |
| 55 | `src/dsdk/logic/semantics.py:48` | compare | `tests/logic/test_fixtures.py::test_truth_table_matches_fixture_including_order[not_a]` |
| 56 | `src/dsdk/logic/semantics.py:52` | boolop | `tests/logic/test_fixtures.py::test_truth_table_matches_fixture_including_order[and_ab]` |
| 57 | `src/dsdk/logic/semantics.py:52` | compare | `tests/logic/test_fixtures.py::test_truth_table_matches_fixture_including_order[and_ab]` |
| 58 | `src/dsdk/logic/semantics.py:52` | flip-bool | `tests/logic/test_fixtures.py::test_truth_table_matches_fixture_including_order[and_ab]` |
| 59 | `src/dsdk/logic/semantics.py:56` | return-none | `tests/logic/test_fixtures.py::test_truth_table_matches_fixture_including_order[and_ab]` |
| 60 | `src/dsdk/logic/semantics.py:56` | flip-bool | `tests/logic/test_fixtures.py::test_truth_table_matches_fixture_including_order[and_ab]` |
| 61 | `src/dsdk/logic/semantics.py:60` | boolop | `tests/logic/test_fixtures.py::test_truth_table_matches_fixture_including_order[or_ab]` |
| 62 | `src/dsdk/logic/semantics.py:60` | flip-bool | `tests/logic/test_fixtures.py::test_truth_table_matches_fixture_including_order[or_ab]` |
| 63 | `src/dsdk/logic/semantics.py:61` | flip-bool | `tests/logic/test_fixtures.py::test_truth_table_matches_fixture_including_order[or_ab]` |
| 64 | `src/dsdk/logic/semantics.py:62` | negate-if | `tests/logic/test_fixtures.py::test_truth_table_matches_fixture_including_order[or_ab]` |
| 65 | `src/dsdk/logic/semantics.py:62` | compare | `tests/logic/test_fixtures.py::test_truth_table_matches_fixture_including_order[or_ab]` |
| 66 | `src/dsdk/logic/semantics.py:62` | compare | `tests/logic/test_fixtures.py::test_truth_table_matches_fixture_including_order[or_ab]` |
| 68 | `src/dsdk/logic/semantics.py:64` | return-none | `tests/logic/test_fixtures.py::test_truth_table_matches_fixture_including_order[or_ab]` |
| 69 | `src/dsdk/logic/semantics.py:64` | flip-bool | `tests/logic/test_fixtures.py::test_truth_table_matches_fixture_including_order[or_ab]` |
| 70 | `src/dsdk/logic/semantics.py:76` | flip-bool | `tests/logic/test_fixtures.py::test_truth_table_matches_fixture_including_order[not_a]` |
| 71 | `src/dsdk/logic/semantics.py:97` | negate-if | `tests/logic/test_fixtures.py::test_truth_table_matches_fixture_including_order[and_ab]` |
| 72 | `src/dsdk/logic/semantics.py:104` | compare | `tests/logic/test_fixtures.py::test_truth_table_matches_fixture_including_order[iff_ab]` |
| 73 | `src/dsdk/logic/semantics.py:104` | compare | `tests/logic/test_fixtures.py::test_truth_table_matches_fixture_including_order[iff_ab]` |
| 74 | `src/dsdk/logic/semantics.py:164` | negate-if | `tests/logic/test_semantics.py::test_kleene_binary_tables_all_nine_combinations[True-True-And]` |
| 75 | `src/dsdk/logic/semantics.py:165` | return-none | `tests/logic/test_semantics.py::test_kleene_binary_tables_all_nine_combinations[True-None-And]` |
| 76 | `src/dsdk/logic/semantics.py:192` | binop | `tests/logic/test_fixtures.py::test_wumpus_kb_has_exactly_the_hand_derived_models` |
| 77 | `src/dsdk/logic/semantics.py:193` | negate-if | `tests/logic/test_fixtures.py::test_wumpus_kb_has_exactly_the_hand_derived_models` |
| 78 | `src/dsdk/logic/semantics.py:214` | return-none | `tests/logic/test_fixtures.py::test_models_count_and_flags_match_fixture[const_true]` |
| 79 | `src/dsdk/logic/semantics.py:220` | drop-not | `tests/logic/test_fixtures.py::test_models_count_and_flags_match_fixture[const_true]` |
| 80 | `src/dsdk/logic/semantics.py:233` | compare | `tests/logic/test_fixtures.py::test_wumpus_entailments[not_P12]` |
| 81 | `src/dsdk/logic/semantics.py:246` | return-none | `tests/logic/test_fixtures.py::test_wumpus_entailments[P12]` |
| 82 | `src/dsdk/logic/structures.py:27` | negate-if | `tests/logic/test_structures.py::test_mirror_base_and_step_cases` |
| 83 | `src/dsdk/logic/structures.py:29` | negate-if | `tests/logic/test_structures.py::test_mirror_base_and_step_cases` |
| 84 | `src/dsdk/logic/structures.py:35` | flip-bool | `timeout >150s (hang)` |
| 85 | `src/dsdk/logic/structures.py:40` | return-none | `tests/logic/test_structures.py::test_mirror_base_and_step_cases` |
| 86 | `src/dsdk/logic/structures.py:48` | negate-if | `tests/logic/test_structures.py::test_leaf_and_node_are_trees_with_value_equality` |
| 87 | `src/dsdk/logic/structures.py:48` | compare | `tests/logic/test_structures.py::test_leaf_and_node_are_trees_with_value_equality` |
| 88 | `src/dsdk/logic/structures.py:50` | return-none | `tests/logic/test_structures.py::test_leaf_and_node_are_trees_with_value_equality` |
| 89 | `src/dsdk/logic/structures.py:56` | negate-if | `tests/logic/test_structures.py::test_leaf_and_node_are_trees_with_value_equality` |
| 90 | `src/dsdk/logic/structures.py:58` | negate-if | `tests/logic/test_structures.py::test_leaf_and_node_are_trees_with_value_equality` |
| 91 | `src/dsdk/logic/structures.py:58` | drop-not | `tests/logic/test_structures.py::test_leaf_and_node_are_trees_with_value_equality` |
| 92 | `src/dsdk/logic/structures.py:90` | int+1 | `tests/logic/test_structures.py::test_size_and_height_base_cases` |
| 93 | `src/dsdk/logic/structures.py:90` | binop | `tests/logic/test_structures.py::test_size_and_height_small_trees` |
| 94 | `src/dsdk/logic/structures.py:96` | int+1 | `tests/logic/test_structures.py::test_mirror_deep_tree_depth_200` |
| 95 | `src/dsdk/logic/structures.py:105` | negate-if | `tests/logic/test_structures.py::test_triangular_known_values[0-0]` |
| 96 | `src/dsdk/logic/structures.py:105` | compare | `tests/logic/test_structures.py::test_triangular_known_values[0-0]` |
| 97 | `src/dsdk/logic/structures.py:107` | negate-if | `tests/logic/test_structures.py::test_triangular_known_values[0-0]` |
| 98 | `src/dsdk/logic/structures.py:107` | compare | `tests/logic/test_structures.py::test_triangular_known_values[0-0]` |
| 99 | `src/dsdk/logic/structures.py:110` | int+1 | `tests/logic/test_structures.py::test_triangular_known_values[0-0]` |
