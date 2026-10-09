# Mutation evidence: dsdk.graph (A5)

Commit `57bdb3fb04c9`. 303 mutation sites in the shipped source; 120 sampled with seed 20261009.
**114 killed, 6 survived** (95% kill rate).

Reproduce: `.venv/bin/python tools/mutants/run.py dsdk.graph tests/graph --max 120 --seed 20261009`

A survivor is either equivalent (no observable change) or a test gap. Each one is listed for triage.

## Survivors

| # | Where | Kind | Original | Mutant |
|---|---|---|---|---|
| 14 | `src/dsdk/graph/bridges.py:181` | compare | `drop >= len(pkg)` | `drop > len(pkg)` |
| 31 | `src/dsdk/graph/evidence.py:87` | return-none | `return None` | `return None` |
| 55 | `src/dsdk/graph/model.py:155` | compare | `index[u] > index[v]` | `index[u] >= index[v]` |
| 61 | `src/dsdk/graph/model.py:237` | boolop | `self.has_node(u) and self.has_node(v)` | `self.has_node(u) or self.has_node(v)` |
| 90 | `src/dsdk/graph/traverse.py:96` | return-none | `return None` | `return None` |
| 106 | `src/dsdk/graph/traverse.py:207` | return-none | `return None` | `return None` |

## Killed (first failing test)

| # | Where | Kind | Killed by |
|---|---|---|---|
| 0 | `src/dsdk/graph/bridges.py:38` | compare | `tests/graph/test_graph_bridges.py::test_lineage_of_a_raw_part_is_a_single_node` |
| 1 | `src/dsdk/graph/bridges.py:53` | negate-if | `tests/graph/test_graph_bridges.py::test_lineage_nodes_are_part_objects_identified_by_identity` |
| 2 | `src/dsdk/graph/bridges.py:96` | negate-if | `tests/graph/test_graph_bridges.py::test_lineage_of_a_raw_part_is_a_single_node` |
| 3 | `src/dsdk/graph/bridges.py:101` | return-none | `tests/graph/test_graph_bridges.py::test_lineage_of_a_raw_part_is_a_single_node` |
| 4 | `src/dsdk/graph/bridges.py:101` | flip-bool | `tests/graph/test_graph_bridges.py::test_lineage_diamond_exact_nodes_edges_and_labels` |
| 5 | `src/dsdk/graph/bridges.py:136` | negate-if | `tests/graph/test_graph_bridges.py::test_formula_graph_of_a_variable_is_one_node` |
| 6 | `src/dsdk/graph/bridges.py:139` | compare | `tests/graph/test_graph_bridges.py::test_formula_graph_of_a_variable_is_one_node` |
| 7 | `src/dsdk/graph/bridges.py:140` | flip-bool | `tests/graph/test_graph_bridges.py::test_formula_graph_is_a_tree_with_size_nodes_and_formula_height` |
| 8 | `src/dsdk/graph/bridges.py:153` | negate-if | `tests/graph/test_graph_bridges.py::test_formula_graph_preorder_numbering_and_labels_on_a_small_formula` |
| 9 | `src/dsdk/graph/bridges.py:174` | boolop | `tests/graph/test_graph_bridges.py::test_import_graph_ignores_stdlib_third_party_other_tops_and_self_imports` |
| 10 | `src/dsdk/graph/bridges.py:174` | compare | `tests/graph/test_graph_bridges.py::test_import_graph_absolute_imports_point_from_importer_to_dependency` |
| 11 | `src/dsdk/graph/bridges.py:174` | int+1 | `tests/graph/test_graph_bridges.py::test_import_graph_counts_function_level_and_type_checking_imports_but_not_comments_or_strings` |
| 12 | `src/dsdk/graph/bridges.py:175` | int+1 | `tests/graph/test_graph_bridges.py::test_import_graph_absolute_imports_point_from_importer_to_dependency` |
| 13 | `src/dsdk/graph/bridges.py:180` | int+1 | `tests/graph/test_graph_bridges.py::test_import_graph_resolves_relative_imports_and_skips_own_package` |
| 15 | `src/dsdk/graph/bridges.py:183` | binop | `tests/graph/test_graph_bridges.py::test_import_graph_resolves_relative_imports_and_skips_own_package` |
| 16 | `src/dsdk/graph/bridges.py:184` | compare | `tests/graph/test_graph_bridges.py::test_import_graph_absolute_imports_point_from_importer_to_dependency` |
| 17 | `src/dsdk/graph/bridges.py:186` | negate-if | `tests/graph/test_graph_bridges.py::test_import_graph_absolute_imports_point_from_importer_to_dependency` |
| 18 | `src/dsdk/graph/bridges.py:186` | compare | `tests/graph/test_graph_bridges.py::test_import_graph_absolute_imports_point_from_importer_to_dependency` |
| 19 | `src/dsdk/graph/bridges.py:186` | int+1 | `tests/graph/test_graph_bridges.py::test_import_graph_absolute_imports_point_from_importer_to_dependency` |
| 20 | `src/dsdk/graph/bridges.py:221` | drop-not | `tests/graph/test_graph_bridges.py::test_import_graph_nodes_are_sorted_subpackages_only` |
| 21 | `src/dsdk/graph/bridges.py:224` | boolop | `tests/graph/test_graph_bridges.py::test_import_graph_nodes_are_sorted_subpackages_only` |
| 22 | `src/dsdk/graph/bridges.py:231` | negate-if | `tests/graph/test_graph_bridges.py::test_import_graph_absolute_imports_point_from_importer_to_dependency` |
| 23 | `src/dsdk/graph/bridges.py:231` | compare | `tests/graph/test_graph_bridges.py::test_import_graph_absolute_imports_point_from_importer_to_dependency` |
| 24 | `src/dsdk/graph/bridges.py:237` | flip-bool | `tests/graph/test_graph_bridges.py::test_import_graph_nodes_are_sorted_subpackages_only` |
| 25 | `src/dsdk/graph/evidence.py:77` | negate-if | `tests/graph/test_graph_evidence.py::test_unknown_edge_on_the_only_path_makes_the_answer_unknown_not_false` |
| 26 | `src/dsdk/graph/evidence.py:77` | compare | `tests/graph/test_graph_evidence.py::test_unknown_edge_on_the_only_path_makes_the_answer_unknown_not_false` |
| 27 | `src/dsdk/graph/evidence.py:82` | compare | `tests/graph/test_graph_evidence.py::test_unknown_edge_on_the_only_path_makes_the_answer_unknown_not_false` |
| 28 | `src/dsdk/graph/evidence.py:85` | boolop | `tests/graph/test_graph_evidence.py::test_candidate_path_prefers_fewer_uncertain_edges_over_fewer_hops` |
| 29 | `src/dsdk/graph/evidence.py:85` | compare | `tests/graph/test_graph_evidence.py::test_candidate_path_prefers_fewer_uncertain_edges_over_fewer_hops` |
| 30 | `src/dsdk/graph/evidence.py:86` | binop | `tests/graph/test_graph_evidence.py::test_candidate_path_prefers_fewer_uncertain_edges_over_fewer_hops` |
| 32 | `src/dsdk/graph/evidence.py:95` | return-none | `tests/graph/test_graph_evidence.py::test_missing_nodes_give_an_invalid_judgment_not_an_exception` |
| 33 | `src/dsdk/graph/evidence.py:99` | return-none | `tests/graph/test_graph_evidence.py::test_known_path_gives_known_true_with_the_path_in_the_reason` |
| 34 | `src/dsdk/graph/evidence.py:99` | flip-bool | `tests/graph/test_graph_evidence.py::test_known_path_gives_known_true_with_the_path_in_the_reason` |
| 35 | `src/dsdk/graph/evidence.py:102` | negate-if | `tests/graph/test_graph_evidence.py::test_unknown_edge_on_the_only_path_makes_the_answer_unknown_not_false` |
| 36 | `src/dsdk/graph/evidence.py:102` | compare | `tests/graph/test_graph_evidence.py::test_unknown_edge_on_the_only_path_makes_the_answer_unknown_not_false` |
| 37 | `src/dsdk/graph/evidence.py:104` | int+1 | `tests/graph/test_graph_evidence.py::test_unknown_edge_on_the_only_path_makes_the_answer_unknown_not_false` |
| 38 | `src/dsdk/graph/evidence.py:106` | negate-if | `tests/graph/test_graph_evidence.py::test_unknown_edge_on_the_only_path_makes_the_answer_unknown_not_false` |
| 39 | `src/dsdk/graph/evidence.py:106` | boolop | `tests/graph/test_graph_evidence.py::test_unknown_edge_on_the_only_path_makes_the_answer_unknown_not_false` |
| 40 | `src/dsdk/graph/evidence.py:106` | compare | `tests/graph/test_graph_evidence.py::test_unknown_edge_on_the_only_path_makes_the_answer_unknown_not_false` |
| 41 | `src/dsdk/graph/evidence.py:108` | return-none | `tests/graph/test_graph_evidence.py::test_unknown_edge_on_the_only_path_makes_the_answer_unknown_not_false` |
| 42 | `src/dsdk/graph/evidence.py:108` | binop | `tests/graph/test_graph_evidence.py::test_unknown_edge_on_the_only_path_makes_the_answer_unknown_not_false` |
| 43 | `src/dsdk/graph/evidence.py:110` | negate-if | `tests/graph/test_graph_evidence.py::test_open_world_without_any_path_is_unknown` |
| 44 | `src/dsdk/graph/model.py:110` | compare | `tests/graph/test_graph_bridges.py::test_lineage_of_a_raw_part_is_a_single_node` |
| 45 | `src/dsdk/graph/model.py:124` | negate-if | `tests/graph/test_graph_model.py::test_edge_input_forms_are_equivalent` |
| 46 | `src/dsdk/graph/model.py:128` | drop-not | `tests/graph/test_graph_bridges.py::test_lineage_nodes_are_part_objects_identified_by_identity` |
| 47 | `src/dsdk/graph/model.py:132` | boolop | `tests/graph/test_graph_bridges.py::test_lineage_nodes_are_part_objects_identified_by_identity` |
| 48 | `src/dsdk/graph/model.py:132` | drop-not | `tests/graph/test_graph_bridges.py::test_lineage_nodes_are_part_objects_identified_by_identity` |
| 49 | `src/dsdk/graph/model.py:137` | negate-if | `tests/graph/test_graph_bridges.py::test_lineage_of_a_raw_part_is_a_single_node` |
| 50 | `src/dsdk/graph/model.py:137` | compare | `tests/graph/test_graph_bridges.py::test_lineage_of_a_raw_part_is_a_single_node` |
| 51 | `src/dsdk/graph/model.py:140` | negate-if | `tests/graph/test_graph_evidence.py::test_known_path_gives_known_true_with_the_path_in_the_reason` |
| 52 | `src/dsdk/graph/model.py:144` | negate-if | `tests/graph/test_graph_bridges.py::test_lineage_of_a_raw_part_is_a_single_node` |
| 53 | `src/dsdk/graph/model.py:149` | negate-if | `tests/graph/test_graph_bridges.py::test_lineage_nodes_are_part_objects_identified_by_identity` |
| 54 | `src/dsdk/graph/model.py:149` | compare | `tests/graph/test_graph_bridges.py::test_lineage_nodes_are_part_objects_identified_by_identity` |
| 56 | `src/dsdk/graph/model.py:163` | negate-if | `tests/graph/test_graph_bridges.py::test_lineage_same_part_under_two_input_names_merges_edges_and_joins_labels` |
| 57 | `src/dsdk/graph/model.py:166` | compare | `tests/graph/test_graph_bridges.py::test_lineage_diamond_exact_nodes_edges_and_labels` |
| 58 | `src/dsdk/graph/model.py:206` | int+1 | `tests/graph/test_graph_model.py::test_from_records_missing_required_key_is_graph_error[record0]` |
| 59 | `src/dsdk/graph/model.py:214` | compare | `tests/graph/test_graph_bridges.py::test_lineage_same_part_under_two_input_names_merges_edges_and_joins_labels` |
| 60 | `src/dsdk/graph/model.py:225` | return-none | `tests/graph/test_graph_bridges.py::test_lineage_edges_point_from_dependency_to_dependent_so_topological_order_is_a_valid_run_order` |
| 62 | `src/dsdk/graph/model.py:240` | compare | `tests/graph/test_graph_bridges.py::test_lineage_same_part_under_two_input_names_merges_edges_and_joins_labels` |
| 63 | `src/dsdk/graph/model.py:241` | return-none | `tests/graph/test_graph_bridges.py::test_lineage_same_part_under_two_input_names_merges_edges_and_joins_labels` |
| 64 | `src/dsdk/graph/model.py:242` | negate-if | `tests/graph/test_graph_bridges.py::test_lineage_same_part_under_two_input_names_merges_edges_and_joins_labels` |
| 65 | `src/dsdk/graph/model.py:242` | boolop | `tests/graph/test_graph_bridges.py::test_lineage_through_a_committed_tick` |
| 66 | `src/dsdk/graph/model.py:242` | drop-not | `tests/graph/test_graph_evidence.py::test_undirected_uncertain_edge_is_reported_in_the_walking_direction` |
| 67 | `src/dsdk/graph/model.py:243` | return-none | `tests/graph/test_graph_evidence.py::test_undirected_uncertain_edge_is_reported_in_the_walking_direction` |
| 68 | `src/dsdk/graph/model.py:248` | compare | `tests/graph/test_graph_bridges.py::test_store_lineage_graph_unions_all_bound_parts_in_binding_order` |
| 69 | `src/dsdk/graph/model.py:262` | negate-if | `tests/graph/test_graph_bridges.py::test_lineage_shared_calculation_is_one_node` |
| 70 | `src/dsdk/graph/model.py:262` | boolop | `tests/graph/test_graph_bridges.py::test_lineage_of_a_1500_deep_chain_needs_no_recursion` |
| 71 | `src/dsdk/graph/model.py:262` | compare | `tests/graph/test_graph_evidence.py::test_direction_matters_for_reachability` |
| 72 | `src/dsdk/graph/model.py:291` | binop | `tests/graph/test_graph_fixtures.py::test_fixture_views[curriculum_8]` |
| 73 | `src/dsdk/graph/model.py:295` | negate-if | `tests/graph/test_graph_fixtures.py::test_fixture_views[curriculum_8]` |
| 74 | `src/dsdk/graph/model.py:295` | drop-not | `tests/graph/test_graph_fixtures.py::test_fixture_views[curriculum_8]` |
| 75 | `src/dsdk/graph/model.py:310` | drop-not | `tests/graph/test_graph_model.py::test_weight_matrix_distinguishes_zero_weight_from_no_edge_and_defaults_to_one` |
| 76 | `src/dsdk/graph/model.py:312` | return-none | `tests/graph/test_graph_model.py::test_weight_matrix_distinguishes_zero_weight_from_no_edge_and_defaults_to_one` |
| 77 | `src/dsdk/graph/model.py:317` | negate-if | `tests/graph/test_graph_fixtures.py::test_fixture_components_and_sccs[curriculum_8]` |
| 78 | `src/dsdk/graph/model.py:317` | drop-not | `tests/graph/test_graph_fixtures.py::test_fixture_components_and_sccs[curriculum_8]` |
| 79 | `src/dsdk/graph/model.py:318` | return-none | `tests/graph/test_graph_model.py::test_reverse_of_undirected_graph_is_equal` |
| 80 | `src/dsdk/graph/model.py:320` | flip-bool | `tests/graph/test_graph_fixtures.py::test_fixture_components_and_sccs[curriculum_8]` |
| 81 | `src/dsdk/graph/relational.py:49` | int+1 | `tests/graph/test_graph_relational.py::test_two_hop_join_missing_key_is_graph_error` |
| 82 | `src/dsdk/graph/relational.py:52` | compare | `tests/graph/test_graph_relational.py::test_two_hop_join_basic_chain` |
| 83 | `src/dsdk/graph/relational.py:54` | return-none | `tests/graph/test_graph_relational.py::test_two_hop_join_basic_chain` |
| 84 | `src/dsdk/graph/relational.py:69` | return-none | `tests/graph/test_graph_relational.py::test_duplicate_records_multiply_in_the_join_but_not_in_the_graph` |
| 85 | `src/dsdk/graph/relational.py:91` | binop | `tests/graph/test_graph_relational.py::test_duplicate_records_multiply_in_the_join_but_not_in_the_graph` |
| 86 | `src/dsdk/graph/traverse.py:68` | int+1 | `tests/graph/test_graph_bridges.py::test_formula_graph_2000_deep_not_chain` |
| 87 | `src/dsdk/graph/traverse.py:76` | negate-if | `tests/graph/test_graph_bridges.py::test_formula_graph_2000_deep_not_chain` |
| 88 | `src/dsdk/graph/traverse.py:95` | negate-if | `tests/graph/test_graph_evidence.py::test_known_path_gives_known_true_with_the_path_in_the_reason` |
| 89 | `src/dsdk/graph/traverse.py:95` | compare | `tests/graph/test_graph_evidence.py::test_known_path_gives_known_true_with_the_path_in_the_reason` |
| 91 | `src/dsdk/graph/traverse.py:101` | negate-if | `tests/graph/test_graph_evidence.py::test_known_path_gives_known_true_with_the_path_in_the_reason` |
| 92 | `src/dsdk/graph/traverse.py:101` | compare | `tests/graph/test_graph_evidence.py::test_known_path_gives_known_true_with_the_path_in_the_reason` |
| 93 | `src/dsdk/graph/traverse.py:118` | int+1 | `tests/graph/test_graph_fixtures.py::test_fixture_dfs_orders[curriculum_8]` |
| 94 | `src/dsdk/graph/traverse.py:124` | int+1 | `tests/graph/test_graph_fixtures.py::test_fixture_dfs_orders[curriculum_8]` |
| 95 | `src/dsdk/graph/traverse.py:144` | negate-if | `tests/graph/test_graph_fixtures.py::test_fixture_dfs_orders[curriculum_8]` |
| 96 | `src/dsdk/graph/traverse.py:160` | return-none | `tests/graph/test_graph_fixtures.py::test_fixture_dfs_orders[curriculum_8]` |
| 97 | `src/dsdk/graph/traverse.py:175` | int+1 | `tests/graph/test_graph_bridges.py::test_lineage_of_a_1500_deep_chain_needs_no_recursion` |
| 98 | `src/dsdk/graph/traverse.py:188` | flip-bool | `tests/graph/test_graph_bridges.py::test_lineage_of_a_1500_deep_chain_needs_no_recursion` |
| 99 | `src/dsdk/graph/traverse.py:191` | drop-not | `tests/graph/test_graph_bridges.py::test_import_graph_detects_an_import_cycle` |
| 100 | `src/dsdk/graph/traverse.py:192` | boolop | `tests/graph/test_graph_bridges.py::test_lineage_of_a_1500_deep_chain_needs_no_recursion` |
| 101 | `src/dsdk/graph/traverse.py:192` | compare | `tests/graph/test_graph_bridges.py::test_lineage_of_a_1500_deep_chain_needs_no_recursion` |
| 102 | `src/dsdk/graph/traverse.py:193` | binop | `tests/graph/test_graph_bridges.py::test_import_graph_detects_an_import_cycle` |
| 103 | `src/dsdk/graph/traverse.py:200` | flip-bool | `tests/graph/test_graph_bridges.py::test_lineage_of_a_1500_deep_chain_needs_no_recursion` |
| 104 | `src/dsdk/graph/traverse.py:202` | negate-if | `tests/graph/test_graph_bridges.py::test_lineage_of_a_1500_deep_chain_needs_no_recursion` |
| 105 | `src/dsdk/graph/traverse.py:202` | drop-not | `tests/graph/test_graph_bridges.py::test_lineage_of_a_1500_deep_chain_needs_no_recursion` |
| 107 | `src/dsdk/graph/traverse.py:222` | drop-not | `tests/graph/test_graph_bridges.py::test_lineage_edges_point_from_dependency_to_dependent_so_topological_order_is_a_valid_run_order` |
| 108 | `src/dsdk/graph/traverse.py:235` | compare | `tests/graph/test_graph_bridges.py::test_lineage_edges_point_from_dependency_to_dependent_so_topological_order_is_a_valid_run_order` |
| 109 | `src/dsdk/graph/traverse.py:235` | int+1 | `tests/graph/test_graph_bridges.py::test_lineage_edges_point_from_dependency_to_dependent_so_topological_order_is_a_valid_run_order` |
| 110 | `src/dsdk/graph/traverse.py:237` | negate-if | `tests/graph/test_graph_bridges.py::test_lineage_edges_point_from_dependency_to_dependent_so_topological_order_is_a_valid_run_order` |
| 111 | `src/dsdk/graph/traverse.py:237` | compare | `tests/graph/test_graph_bridges.py::test_lineage_edges_point_from_dependency_to_dependent_so_topological_order_is_a_valid_run_order` |
| 112 | `src/dsdk/graph/traverse.py:251` | negate-if | `tests/graph/test_graph_fixtures.py::test_fixture_components_and_sccs[curriculum_8]` |
| 113 | `src/dsdk/graph/traverse.py:251` | compare | `tests/graph/test_graph_fixtures.py::test_fixture_components_and_sccs[curriculum_8]` |
| 114 | `src/dsdk/graph/traverse.py:259` | compare | `tests/graph/test_graph_fixtures.py::test_fixture_components_and_sccs[curriculum_8]` |
| 115 | `src/dsdk/graph/traverse.py:262` | return-none | `tests/graph/test_graph_fixtures.py::test_fixture_components_and_sccs[curriculum_8]` |
| 116 | `src/dsdk/graph/traverse.py:286` | negate-if | `tests/graph/test_graph_fixtures.py::test_fixture_components_and_sccs[curriculum_8]` |
| 117 | `src/dsdk/graph/traverse.py:286` | drop-not | `tests/graph/test_graph_fixtures.py::test_fixture_components_and_sccs[curriculum_8]` |
| 118 | `src/dsdk/graph/traverse.py:291` | compare | `tests/graph/test_graph_fixtures.py::test_fixture_components_and_sccs[curriculum_8]` |
| 119 | `src/dsdk/graph/traverse.py:299` | compare | `tests/graph/test_graph_fixtures.py::test_fixture_components_and_sccs[curriculum_8]` |
