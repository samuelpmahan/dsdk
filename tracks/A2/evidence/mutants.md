# Mutation evidence: dsdk.lang (A2)

Commit `34fd121e2e10`. 592 mutation sites in the shipped source; 120 sampled with seed 20261009.
**115 killed, 5 survived** (96% kill rate).

Reproduce: `.venv/bin/python tools/mutants/run.py dsdk.lang tests/lang --max 120 --seed 20261009`

A survivor is either equivalent (no observable change) or a test gap. Each one is listed for triage.

## Survivors

| # | Where | Kind | Original | Mutant |
|---|---|---|---|---|
| 32 | `src/dsdk/lang/calc.py:432` | compare | `min_prec == 0` | `min_prec != 0` |
| 48 | `src/dsdk/lang/calc.py:538` | return-none | `return None` | `return None` |
| 55 | `src/dsdk/lang/calc.py:560` | return-none | `return None` | `return None` |
| 59 | `src/dsdk/lang/calc.py:577` | return-none | `return None` | `return None` |
| 95 | `src/dsdk/lang/formula_syntax.py:191` | int+1 | `0` | `1` |

## Killed (first failing test)

| # | Where | Kind | Killed by |
|---|---|---|---|
| 0 | `src/dsdk/lang/bridge.py:36` | return-none | `tests/lang/test_bridge.py::test_from_formula_has_the_exact_documented_shape[2]` |
| 1 | `src/dsdk/lang/bridge.py:46` | return-none | `tests/lang/test_bridge.py::test_from_formula_has_the_exact_documented_shape[7]` |
| 2 | `src/dsdk/lang/bridge.py:60` | flip-bool | `tests/lang/test_bridge.py::test_bind_assignment_wraps_in_sorted_lets_first_name_outermost` |
| 3 | `src/dsdk/lang/bridge.py:97` | drop-not | `tests/lang/test_bridge.py::test_trace_is_recorded_as_one_part_per_step_with_exact_records` |
| 4 | `src/dsdk/lang/bridge.py:115` | return-none | `tests/lang/test_bridge.py::test_trace_is_recorded_as_one_part_per_step_with_exact_records` |
| 5 | `src/dsdk/lang/bridge.py:120` | return-none | `tests/lang/test_bridge.py::test_trace_is_recorded_as_one_part_per_step_with_exact_records` |
| 6 | `src/dsdk/lang/bridge.py:127` | compare | `tests/lang/test_bridge.py::test_trace_is_recorded_as_one_part_per_step_with_exact_records` |
| 7 | `src/dsdk/lang/calc.py:142` | compare | `tests/lang/test_bridge.py::test_from_formula_has_the_exact_documented_shape[0]` |
| 8 | `src/dsdk/lang/calc.py:215` | drop-not | `tests/lang/test_bridge.py::test_from_formula_translation_is_a_closed_bool_fragment` |
| 9 | `src/dsdk/lang/calc.py:224` | negate-if | `tests/lang/test_bridge.py::test_translation_is_well_typed_bool_and_keeps_variables` |
| 10 | `src/dsdk/lang/calc.py:253` | negate-if | `tests/lang/test_bridge.py::test_from_formula_translation_is_a_closed_bool_fragment` |
| 11 | `src/dsdk/lang/calc.py:273` | drop-not | `tests/lang/test_bridge.py::test_small_step_trace_also_reaches_the_logic_value` |
| 12 | `src/dsdk/lang/calc.py:275` | negate-if | `tests/lang/test_bridge.py::test_small_step_trace_also_reaches_the_logic_value` |
| 13 | `src/dsdk/lang/calc.py:277` | return-none | `tests/lang/test_bridge.py::test_small_step_trace_also_reaches_the_logic_value` |
| 14 | `src/dsdk/lang/calc.py:282` | return-none | `tests/lang/test_bridge.py::test_small_step_trace_also_reaches_the_logic_value` |
| 15 | `src/dsdk/lang/calc.py:285` | negate-if | `tests/lang/test_bridge.py::test_small_step_trace_also_reaches_the_logic_value` |
| 16 | `src/dsdk/lang/calc.py:288` | return-none | `tests/lang/test_bridge.py::test_small_step_trace_also_reaches_the_logic_value` |
| 17 | `src/dsdk/lang/calc.py:289` | negate-if | `tests/lang/test_bridge.py::test_small_step_trace_also_reaches_the_logic_value` |
| 18 | `src/dsdk/lang/calc.py:294` | return-none | `tests/lang/test_bridge.py::test_small_step_trace_also_reaches_the_logic_value` |
| 19 | `src/dsdk/lang/calc.py:315` | negate-if | `tests/lang/test_calc_ast.py::test_to_python_and_from_python` |
| 20 | `src/dsdk/lang/calc.py:335` | return-none | `tests/lang/test_bridge.py::test_a_missing_variable_is_unassigned_in_logic_and_stuck_in_calc` |
| 21 | `src/dsdk/lang/calc.py:337` | return-none | `tests/lang/test_bridge.py::test_source_round_trip_through_the_parser` |
| 22 | `src/dsdk/lang/calc.py:341` | return-none | `tests/lang/test_bridge.py::test_records_always_match_calc_trace_and_chain_length` |
| 23 | `src/dsdk/lang/calc.py:365` | int+1 | `tests/lang/test_calc_parse.py::test_parse_builds_the_intended_tree[a` |
| 24 | `src/dsdk/lang/calc.py:392` | negate-if | `tests/lang/test_bridge.py::test_source_round_trip_through_the_parser` |
| 25 | `src/dsdk/lang/calc.py:392` | boolop | `tests/lang/test_bridge.py::test_source_round_trip_through_the_parser` |
| 26 | `src/dsdk/lang/calc.py:406` | compare | `tests/lang/test_calc_parse.py::test_parse_builds_the_intended_tree[not` |
| 27 | `src/dsdk/lang/calc.py:409` | negate-if | `tests/lang/test_bridge.py::test_source_round_trip_through_the_parser` |
| 28 | `src/dsdk/lang/calc.py:419` | compare | `tests/lang/test_bridge.py::test_source_round_trip_through_the_parser` |
| 29 | `src/dsdk/lang/calc.py:422` | negate-if | `tests/lang/test_bridge.py::test_source_round_trip_through_the_parser` |
| 30 | `src/dsdk/lang/calc.py:423` | return-none | `tests/lang/test_bridge.py::test_source_round_trip_through_the_parser` |
| 31 | `src/dsdk/lang/calc.py:426` | int+1 | `tests/lang/test_bridge.py::test_the_calculations_really_compute_from_their_inputs` |
| 33 | `src/dsdk/lang/calc.py:439` | compare | `tests/lang/test_bridge.py::test_source_round_trip_through_the_parser` |
| 34 | `src/dsdk/lang/calc.py:443` | negate-if | `tests/lang/test_bridge.py::test_source_round_trip_through_the_parser` |
| 35 | `src/dsdk/lang/calc.py:443` | compare | `tests/lang/test_bridge.py::test_source_round_trip_through_the_parser` |
| 36 | `src/dsdk/lang/calc.py:443` | int+1 | `tests/lang/test_calc_parse.py::test_comparison_is_non_associative` |
| 37 | `src/dsdk/lang/calc.py:443` | int+1 | `tests/lang/test_calc_parse.py::test_comparison_is_non_associative` |
| 38 | `src/dsdk/lang/calc.py:444` | return-none | `tests/lang/test_bridge.py::test_source_round_trip_through_the_parser` |
| 39 | `src/dsdk/lang/calc.py:447` | binop | `tests/lang/test_calc_parse.py::test_parse_builds_the_intended_tree[1` |
| 40 | `src/dsdk/lang/calc.py:473` | negate-if | `tests/lang/test_bridge.py::test_a_missing_variable_is_unassigned_in_logic_and_stuck_in_calc` |
| 41 | `src/dsdk/lang/calc.py:487` | compare | `tests/lang/test_bridge.py::test_from_formula_translation_is_a_closed_bool_fragment` |
| 42 | `src/dsdk/lang/calc.py:491` | negate-if | `tests/lang/test_bridge.py::test_from_formula_translation_is_a_closed_bool_fragment` |
| 43 | `src/dsdk/lang/calc.py:491` | compare | `tests/lang/test_bridge.py::test_from_formula_translation_is_a_closed_bool_fragment` |
| 44 | `src/dsdk/lang/calc.py:502` | negate-if | `tests/lang/test_calc_properties.py::test_progress_well_typed_closed_terms_are_never_stuck` |
| 45 | `src/dsdk/lang/calc.py:502` | compare | `tests/lang/test_calc_properties.py::test_progress_well_typed_closed_terms_are_never_stuck` |
| 46 | `src/dsdk/lang/calc.py:534` | negate-if | `tests/lang/test_bridge.py::test_small_step_trace_also_reaches_the_logic_value` |
| 47 | `src/dsdk/lang/calc.py:537` | negate-if | `tests/lang/test_bridge.py::test_small_step_trace_also_reaches_the_logic_value` |
| 49 | `src/dsdk/lang/calc.py:542` | drop-not | `tests/lang/test_bridge.py::test_small_step_trace_also_reaches_the_logic_value` |
| 50 | `src/dsdk/lang/calc.py:545` | negate-if | `tests/lang/test_bridge.py::test_small_step_trace_also_reaches_the_logic_value` |
| 51 | `src/dsdk/lang/calc.py:550` | compare | `tests/lang/test_bridge.py::test_trace_is_recorded_as_one_part_per_step_with_exact_records` |
| 52 | `src/dsdk/lang/calc.py:552` | compare | `tests/lang/test_bridge.py::test_the_calculations_really_compute_from_their_inputs` |
| 53 | `src/dsdk/lang/calc.py:555` | binop | `tests/lang/test_bridge.py::test_the_calculations_really_compute_from_their_inputs` |
| 54 | `src/dsdk/lang/calc.py:557` | return-none | `tests/lang/test_calc_properties.py::test_type_safety_trace_ends_in_a_value_of_the_static_type` |
| 56 | `src/dsdk/lang/calc.py:562` | return-none | `tests/lang/test_bridge.py::test_small_step_trace_also_reaches_the_logic_value` |
| 57 | `src/dsdk/lang/calc.py:562` | compare | `tests/lang/test_bridge.py::test_small_step_trace_also_reaches_the_logic_value` |
| 58 | `src/dsdk/lang/calc.py:567` | return-none | `tests/lang/test_bridge.py::test_small_step_trace_also_reaches_the_logic_value` |
| 60 | `src/dsdk/lang/calc.py:581` | compare | `tests/lang/test_bridge.py::test_records_always_match_calc_trace_and_chain_length` |
| 61 | `src/dsdk/lang/calc.py:601` | compare | `tests/lang/test_bridge.py::test_small_step_trace_also_reaches_the_logic_value` |
| 62 | `src/dsdk/lang/calc.py:602` | return-none | `tests/lang/test_bridge.py::test_small_step_trace_also_reaches_the_logic_value` |
| 63 | `src/dsdk/lang/calc.py:615` | negate-if | `tests/lang/test_bridge.py::test_calc_evaluation_agrees_with_logic_evaluation` |
| 64 | `src/dsdk/lang/calc.py:615` | compare | `tests/lang/test_bridge.py::test_calc_evaluation_agrees_with_logic_evaluation` |
| 65 | `src/dsdk/lang/calc.py:618` | negate-if | `tests/lang/test_bridge.py::test_calc_evaluation_agrees_with_logic_evaluation` |
| 66 | `src/dsdk/lang/calc.py:620` | negate-if | `tests/lang/test_bridge.py::test_calc_evaluation_agrees_with_logic_evaluation` |
| 67 | `src/dsdk/lang/calc.py:622` | return-none | `tests/lang/test_bridge.py::test_calc_evaluation_agrees_with_logic_evaluation` |
| 68 | `src/dsdk/lang/calc.py:625` | compare | `tests/lang/test_calc_eval.py::test_evaluate_returns_the_python_value_with_the_right_type[(if` |
| 69 | `src/dsdk/lang/calc.py:627` | return-none | `tests/lang/test_calc_eval.py::test_evaluate_returns_the_python_value_with_the_right_type[(if` |
| 70 | `src/dsdk/lang/calc.py:633` | compare | `tests/lang/test_bridge.py::test_calc_evaluation_agrees_with_logic_evaluation` |
| 71 | `src/dsdk/lang/calc.py:640` | negate-if | `tests/lang/test_calc_eval.py::test_evaluate_returns_the_python_value_with_the_right_type[(1` |
| 72 | `src/dsdk/lang/calc.py:640` | compare | `tests/lang/test_calc_eval.py::test_evaluate_returns_the_python_value_with_the_right_type[(1` |
| 73 | `src/dsdk/lang/calc.py:641` | compare | `tests/lang/test_calc_eval.py::test_evaluate_returns_the_python_value_with_the_right_type[(1` |
| 74 | `src/dsdk/lang/calc.py:642` | return-none | `tests/lang/test_calc_eval.py::test_evaluate_returns_the_python_value_with_the_right_type[(1` |
| 75 | `src/dsdk/lang/calc.py:644` | return-none | `tests/lang/test_calc_eval.py::test_evaluate_returns_the_python_value_with_the_right_type[(10` |
| 76 | `src/dsdk/lang/calc.py:647` | negate-if | `tests/lang/test_calc_eval.py::test_evaluate_returns_the_python_value_with_the_right_type[(1` |
| 77 | `src/dsdk/lang/calc.py:649` | compare | `tests/lang/test_calc_eval.py::test_evaluate_returns_the_python_value_with_the_right_type[(3` |
| 78 | `src/dsdk/lang/calc.py:650` | compare | `tests/lang/test_bridge.py::test_calc_evaluation_agrees_with_logic_evaluation` |
| 79 | `src/dsdk/lang/calc.py:651` | compare | `tests/lang/test_bridge.py::test_calc_evaluation_agrees_with_logic_evaluation` |
| 80 | `src/dsdk/lang/calc.py:662` | return-none | `tests/lang/test_bridge.py::test_calc_evaluation_agrees_with_logic_evaluation` |
| 81 | `src/dsdk/lang/formula_syntax.py:63` | flip-bool | `tests/lang/test_formula_syntax.py::test_strict_rejects_non_canonical_with_offset_and_expected['']` |
| 82 | `src/dsdk/lang/formula_syntax.py:98` | negate-if | `tests/lang/test_formula_syntax.py::test_without_precedence_a_or_b_and_c_has_two_parse_trees` |
| 83 | `src/dsdk/lang/formula_syntax.py:107` | negate-if | `tests/lang/test_formula_syntax.py::test_without_precedence_a_or_b_and_c_has_two_parse_trees` |
| 84 | `src/dsdk/lang/formula_syntax.py:115` | return-none | `tests/lang/test_formula_syntax.py::test_without_precedence_a_or_b_and_c_has_two_parse_trees` |
| 85 | `src/dsdk/lang/formula_syntax.py:123` | binop | `tests/lang/test_formula_syntax.py::test_without_precedence_a_or_b_and_c_has_two_parse_trees` |
| 86 | `src/dsdk/lang/formula_syntax.py:126` | return-none | `tests/lang/test_formula_syntax.py::test_without_precedence_a_or_b_and_c_has_two_parse_trees` |
| 87 | `src/dsdk/lang/formula_syntax.py:128` | int+1 | `tests/lang/test_formula_syntax.py::test_without_precedence_a_or_b_and_c_has_two_parse_trees` |
| 88 | `src/dsdk/lang/formula_syntax.py:142` | compare | `tests/lang/test_bridge.py::test_calc_reproduces_every_row_of_the_logic_fixture_truth_tables[const_true]` |
| 89 | `src/dsdk/lang/formula_syntax.py:153` | return-none | `tests/lang/test_formula_syntax.py::test_strict_rejects_non_canonical_with_offset_and_expected['']` |
| 90 | `src/dsdk/lang/formula_syntax.py:159` | negate-if | `tests/lang/test_bridge.py::test_source_round_trip_through_the_parser` |
| 91 | `src/dsdk/lang/formula_syntax.py:159` | compare | `tests/lang/test_bridge.py::test_source_round_trip_through_the_parser` |
| 92 | `src/dsdk/lang/formula_syntax.py:161` | return-none | `tests/lang/test_bridge.py::test_source_round_trip_through_the_parser` |
| 93 | `src/dsdk/lang/formula_syntax.py:174` | compare | `tests/lang/test_bridge.py::test_source_round_trip_through_the_parser` |
| 94 | `src/dsdk/lang/formula_syntax.py:181` | compare | `tests/lang/test_bridge.py::test_source_round_trip_through_the_parser` |
| 96 | `src/dsdk/lang/formula_syntax.py:204` | compare | `tests/lang/test_formula_syntax.py::test_relaxed_precedence_and_associativity[a` |
| 97 | `src/dsdk/lang/formula_syntax.py:205` | return-none | `tests/lang/test_bridge.py::test_source_round_trip_through_the_parser` |
| 98 | `src/dsdk/lang/formula_syntax.py:207` | int+1 | `tests/lang/test_formula_syntax.py::test_relaxed_precedence_and_associativity[a` |
| 99 | `src/dsdk/lang/formula_syntax.py:221` | flip-bool | `tests/lang/test_bridge.py::test_calc_reproduces_every_row_of_the_logic_fixture_truth_tables[const_true]` |
| 100 | `src/dsdk/lang/formula_syntax.py:226` | negate-if | `tests/lang/test_bridge.py::test_calc_reproduces_every_row_of_the_logic_fixture_truth_tables[const_true]` |
| 101 | `src/dsdk/lang/formula_syntax.py:230` | boolop | `tests/lang/test_bridge.py::test_calc_reproduces_every_row_of_the_logic_fixture_truth_tables[and_ab]` |
| 102 | `src/dsdk/lang/formula_syntax.py:242` | flip-bool | `tests/lang/test_bridge.py::test_calc_reproduces_every_row_of_the_logic_fixture_truth_tables[const_true]` |
| 103 | `src/dsdk/lang/formula_syntax.py:244` | negate-if | `tests/lang/test_bridge.py::test_calc_reproduces_every_row_of_the_logic_fixture_truth_tables[const_true]` |
| 104 | `src/dsdk/lang/formula_syntax.py:251` | negate-if | `tests/lang/test_bridge.py::test_calc_reproduces_every_row_of_the_logic_fixture_truth_tables[and_ab]` |
| 105 | `src/dsdk/lang/formula_syntax.py:251` | boolop | `tests/lang/test_formula_syntax.py::test_strict_rejects_non_canonical_with_offset_and_expected['(a` |
| 106 | `src/dsdk/lang/formula_syntax.py:251` | int+1 | `tests/lang/test_bridge.py::test_calc_reproduces_every_row_of_the_logic_fixture_truth_tables[and_ab]` |
| 107 | `src/dsdk/lang/formula_syntax.py:253` | int+1 | `tests/lang/test_bridge.py::test_calc_reproduces_every_row_of_the_logic_fixture_truth_tables[and_ab]` |
| 108 | `src/dsdk/lang/formula_syntax.py:254` | boolop | `tests/lang/test_formula_syntax.py::test_strict_rejects_non_canonical_with_offset_and_expected['(a` |
| 109 | `src/dsdk/lang/formula_syntax.py:255` | int+1 | `tests/lang/test_formula_syntax.py::test_strict_rejects_non_canonical_with_offset_and_expected['(a` |
| 110 | `src/dsdk/lang/formula_syntax.py:259` | negate-if | `tests/lang/test_bridge.py::test_calc_reproduces_every_row_of_the_logic_fixture_truth_tables[not_a]` |
| 111 | `src/dsdk/lang/formula_syntax.py:263` | compare | `tests/lang/test_bridge.py::test_calc_reproduces_every_row_of_the_logic_fixture_truth_tables[not_a]` |
| 112 | `src/dsdk/lang/formula_syntax.py:263` | int+1 | `tests/lang/test_bridge.py::test_calc_reproduces_every_row_of_the_logic_fixture_truth_tables[not_a]` |
| 113 | `src/dsdk/lang/formula_syntax.py:266` | int+1 | `tests/lang/test_bridge.py::test_calc_reproduces_every_row_of_the_logic_fixture_truth_tables[and_ab]` |
| 114 | `src/dsdk/lang/lexer.py:156` | int+1 | `tests/lang/test_bridge.py::test_calc_reproduces_every_row_of_the_logic_fixture_truth_tables[const_true]` |
| 115 | `src/dsdk/lang/lexer.py:163` | negate-if | `tests/lang/test_bridge.py::test_calc_reproduces_every_row_of_the_logic_fixture_truth_tables[const_true]` |
| 116 | `src/dsdk/lang/lexer.py:173` | negate-if | `tests/lang/test_bridge.py::test_calc_reproduces_every_row_of_the_logic_fixture_truth_tables[const_true]` |
| 117 | `src/dsdk/lang/lexer.py:175` | negate-if | `tests/lang/test_bridge.py::test_calc_reproduces_every_row_of_the_logic_fixture_truth_tables[const_true]` |
| 118 | `src/dsdk/lang/lexer.py:175` | compare | `tests/lang/test_bridge.py::test_source_round_trip_through_the_parser` |
| 119 | `src/dsdk/lang/lexer.py:178` | return-none | `tests/lang/test_bridge.py::test_calc_reproduces_every_row_of_the_logic_fixture_truth_tables[const_true]` |
