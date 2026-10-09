# Mutation evidence: dsdk.core (A0)

Commit `7147e27bd249`. 111 mutation sites in the shipped source; 80 sampled with seed 20261009.
**80 killed, 0 survived** (100% kill rate).

Reproduce: `.venv/bin/python tools/mutants/run.py dsdk.core tests/core --max 80 --seed 20261009`

A survivor is either equivalent (no observable change) or a test gap. Each one is listed for triage.

## Survivors

| # | Where | Kind | Original | Mutant |
|---|---|---|---|---|

## Killed (first failing test)

| # | Where | Kind | Killed by |
|---|---|---|---|
| 0 | `src/dsdk/core/pxc.py:103` | return-none | `tests/core/test_pxc.py::test_part_captures_value_at_construction` |
| 1 | `src/dsdk/core/pxc.py:107` | return-none | `tests/core/test_pxc.py::test_compose_without_inputs_calls_with_empty_dict[kwargs0]` |
| 2 | `src/dsdk/core/pxc.py:175` | drop-not | `tests/core/test_pxc.py::test_tick_commits_all_composes_in_order_with_receipts` |
| 3 | `src/dsdk/core/pxc.py:184` | negate-if | `tests/core/test_pxc.py::test_tick_commits_all_composes_in_order_with_receipts` |
| 4 | `src/dsdk/core/pxc.py:184` | compare | `tests/core/test_pxc.py::test_tick_commits_all_composes_in_order_with_receipts` |
| 5 | `src/dsdk/core/pxc.py:187` | return-none | `tests/core/test_pxc.py::test_tick_commits_all_composes_in_order_with_receipts` |
| 6 | `src/dsdk/core/pxc.py:193` | return-none | `tests/core/test_pxc.py::test_tick_later_compose_can_read_earlier_staged_part_by_address` |
| 7 | `src/dsdk/core/pxc.py:194` | return-none | `tests/core/test_pxc.py::test_tick_commits_all_composes_in_order_with_receipts` |
| 8 | `src/dsdk/core/pxc.py:199` | return-none | `tests/core/test_pxc.py::test_tick_later_compose_can_read_earlier_staged_part_by_address` |
| 9 | `src/dsdk/core/pxc.py:230` | negate-if | `tests/core/test_pxc.py::test_tick_commits_all_composes_in_order_with_receipts` |
| 10 | `src/dsdk/core/pxc.py:230` | drop-not | `tests/core/test_pxc.py::test_tick_commits_all_composes_in_order_with_receipts` |
| 11 | `src/dsdk/core/pxc.py:232` | drop-not | `tests/core/test_pxc.py::test_tick_commits_all_composes_in_order_with_receipts` |
| 12 | `src/dsdk/core/pxc.py:236` | return-none | `tests/core/test_pxc.py::test_tick_commits_all_composes_in_order_with_receipts` |
| 13 | `src/dsdk/core/pxc.py:242` | negate-if | `tests/core/test_pxc.py::test_tick_commits_all_composes_in_order_with_receipts` |
| 14 | `src/dsdk/core/pxc.py:242` | compare | `tests/core/test_pxc.py::test_tick_commits_all_composes_in_order_with_receipts` |
| 15 | `src/dsdk/core/pxc.py:243` | negate-if | `tests/core/test_pxc.py::test_tick_commits_all_composes_in_order_with_receipts` |
| 16 | `src/dsdk/core/pxc.py:243` | compare | `tests/core/test_pxc.py::test_tick_commits_all_composes_in_order_with_receipts` |
| 17 | `src/dsdk/core/pxc.py:248` | negate-if | `tests/core/test_pxc.py::test_tick_scope_is_dead_after_exit` |
| 18 | `src/dsdk/core/pxc.py:249` | flip-bool | `tests/core/test_pxc.py::test_tick_scope_is_dead_after_exit` |
| 19 | `src/dsdk/core/pxc.py:250` | flip-bool | `tests/core/test_pxc.py::test_tick_blocks_store_writes_and_nested_ticks_while_open` |
| 20 | `src/dsdk/core/pxc.py:251` | flip-bool | `tests/core/test_pxc.py::test_tick_exception_rolls_back_everything_and_marks_every_compose_failed` |
| 21 | `src/dsdk/core/pxc.py:259` | negate-if | `tests/core/test_pxc.py::test_part_captures_value_at_construction` |
| 22 | `src/dsdk/core/pxc.py:260` | return-none | `tests/core/test_pxc.py::test_part_keeps_callables_by_reference` |
| 23 | `src/dsdk/core/pxc.py:267` | drop-not | `tests/core/test_pxc.py::test_malformed_address_string_is_valueerror[-compose_into]` |
| 24 | `src/dsdk/core/pxc.py:269` | negate-if | `tests/core/test_pxc.py::test_malformed_address_string_is_valueerror[-compose_into]` |
| 25 | `src/dsdk/core/pxc.py:269` | compare | `tests/core/test_pxc.py::test_malformed_address_string_is_valueerror[-compose_into]` |
| 26 | `src/dsdk/core/pxc.py:278` | return-none | `tests/core/test_pxc.py::test_compose_binds_and_returns_the_output_part` |
| 27 | `src/dsdk/core/pxc.py:288` | flip-bool | `tests/core/test_pxc.py::test_malformed_address_string_is_valueerror[-compose_into]` |
| 28 | `src/dsdk/core/pxc.py:297` | negate-if | `tests/core/test_pxc.py::test_wellformed_addresses_accepted[px.a]` |
| 29 | `src/dsdk/core/pxc.py:297` | drop-not | `tests/core/test_pxc.py::test_wellformed_addresses_accepted[px.a]` |
| 30 | `src/dsdk/core/pxc.py:299` | drop-not | `tests/core/test_pxc.py::test_wellformed_addresses_accepted[fn.f]` |
| 31 | `src/dsdk/core/pxc.py:310` | negate-if | `tests/core/test_pxc.py::test_set_returns_same_part_and_get_returns_same_object` |
| 32 | `src/dsdk/core/pxc.py:310` | compare | `tests/core/test_pxc.py::test_set_returns_same_part_and_get_returns_same_object` |
| 33 | `src/dsdk/core/pxc.py:312` | return-none | `tests/core/test_pxc.py::test_set_returns_same_part_and_get_returns_same_object` |
| 34 | `src/dsdk/core/pxc.py:317` | return-none | `tests/core/test_pxc.py::test_wellformed_addresses_accepted[px.a]` |
| 35 | `src/dsdk/core/pxc.py:323` | return-none | `tests/core/test_pxc.py::test_invalid_set_leaves_store_empty` |
| 36 | `src/dsdk/core/pxc.py:329` | return-none | `tests/core/test_pxc.py::test_invalid_set_leaves_store_empty` |
| 37 | `src/dsdk/core/pxc.py:363` | negate-if | `tests/core/test_pxc.py::test_compose_binds_and_returns_the_output_part` |
| 38 | `src/dsdk/core/pxc.py:363` | compare | `tests/core/test_pxc.py::test_compose_binds_and_returns_the_output_part` |
| 39 | `src/dsdk/core/pxc.py:366` | return-none | `tests/core/test_pxc.py::test_compose_binds_and_returns_the_output_part` |
| 40 | `src/dsdk/core/pxc.py:371` | negate-if | `tests/core/test_pxc.py::test_malformed_address_string_is_valueerror[-compose_into]` |
| 41 | `src/dsdk/core/pxc.py:386` | negate-if | `tests/core/test_pxc.py::test_compose_binds_and_returns_the_output_part` |
| 42 | `src/dsdk/core/pxc.py:395` | negate-if | `tests/core/test_pxc.py::test_wellformed_addresses_accepted[px.a]` |
| 43 | `src/dsdk/core/pxc.py:395` | boolop | `tests/core/test_pxc.py::test_set_into_occupied_address_raises_and_keeps_original` |
| 44 | `src/dsdk/core/pxc.py:395` | compare | `tests/core/test_pxc.py::test_wellformed_addresses_accepted[px.a]` |
| 45 | `src/dsdk/core/pxc.py:395` | compare | `tests/core/test_pxc.py::test_wellformed_addresses_accepted[px.a]` |
| 46 | `src/dsdk/core/pxc.py:396` | return-none | `tests/core/test_pxc.py::test_set_into_occupied_address_raises_and_keeps_original` |
| 47 | `src/dsdk/core/pxc.py:396` | flip-bool | `tests/core/test_pxc.py::test_set_into_occupied_address_raises_and_keeps_original` |
| 48 | `src/dsdk/core/pxc.py:397` | return-none | `tests/core/test_pxc.py::test_tick_preflight_failures_inside_tick_raise_without_receipt` |
| 49 | `src/dsdk/core/pxc.py:397` | compare | `tests/core/test_pxc.py::test_tick_commits_all_composes_in_order_with_receipts` |
| 50 | `src/dsdk/core/pxc.py:401` | negate-if | `tests/core/test_pxc.py::test_compose_binds_and_returns_the_output_part` |
| 51 | `src/dsdk/core/pxc.py:402` | compare | `tests/core/test_pxc.py::test_compose_binds_and_returns_the_output_part` |
| 52 | `src/dsdk/core/pxc.py:403` | negate-if | `tests/core/test_pxc.py::test_compose_accepts_parts_or_addresses_for_calculation_and_inputs` |
| 53 | `src/dsdk/core/pxc.py:407` | negate-if | `tests/core/test_pxc.py::test_compose_binds_and_returns_the_output_part` |
| 54 | `src/dsdk/core/pxc.py:407` | drop-not | `tests/core/test_pxc.py::test_compose_binds_and_returns_the_output_part` |
| 55 | `src/dsdk/core/pxc.py:409` | return-none | `tests/core/test_pxc.py::test_compose_binds_and_returns_the_output_part` |
| 56 | `src/dsdk/core/pxc.py:416` | negate-if | `tests/core/test_pxc.py::test_compose_binds_and_returns_the_output_part` |
| 57 | `src/dsdk/core/pxc.py:417` | return-none | `tests/core/test_pxc.py::test_compose_without_inputs_calls_with_empty_dict[kwargs0]` |
| 58 | `src/dsdk/core/pxc.py:418` | negate-if | `tests/core/test_pxc.py::test_compose_binds_and_returns_the_output_part` |
| 59 | `src/dsdk/core/pxc.py:418` | drop-not | `tests/core/test_pxc.py::test_compose_binds_and_returns_the_output_part` |
| 60 | `src/dsdk/core/pxc.py:422` | negate-if | `tests/core/test_pxc.py::test_compose_binds_and_returns_the_output_part` |
| 61 | `src/dsdk/core/pxc.py:422` | boolop | `tests/core/test_pxc.py::test_bad_inputs_fail_preflight_without_running[<lambda>-TypeError3]` |
| 62 | `src/dsdk/core/pxc.py:422` | drop-not | `tests/core/test_pxc.py::test_compose_binds_and_returns_the_output_part` |
| 63 | `src/dsdk/core/pxc.py:422` | drop-not | `tests/core/test_pxc.py::test_compose_binds_and_returns_the_output_part` |
| 64 | `src/dsdk/core/pxc.py:424` | negate-if | `tests/core/test_pxc.py::test_compose_binds_and_returns_the_output_part` |
| 65 | `src/dsdk/core/pxc.py:431` | return-none | `tests/core/test_pxc.py::test_compose_binds_and_returns_the_output_part` |
| 66 | `src/dsdk/core/pxc.py:446` | boolop | `tests/core/test_pxc.py::test_compose_binds_and_returns_the_output_part` |
| 67 | `src/dsdk/core/pxc.py:446` | drop-not | `tests/core/test_pxc.py::test_calculation_can_produce_a_calculation` |
| 68 | `src/dsdk/core/pxc.py:453` | return-none | `tests/core/test_pxc.py::test_compose_binds_and_returns_the_output_part` |
| 69 | `src/dsdk/core/pxc.py:478` | return-none | `tests/core/test_pxc.py::test_tick_commits_all_composes_in_order_with_receipts` |
| 70 | `src/dsdk/core/status.py:64` | drop-not | `tests/core/test_status.py::test_known_with_value_is_valid` |
| 71 | `src/dsdk/core/status.py:66` | negate-if | `tests/core/test_status.py::test_known_with_value_is_valid` |
| 72 | `src/dsdk/core/status.py:66` | drop-not | `tests/core/test_status.py::test_known_with_value_is_valid` |
| 73 | `src/dsdk/core/status.py:68` | negate-if | `tests/core/test_status.py::test_known_with_value_is_valid` |
| 74 | `src/dsdk/core/status.py:68` | compare | `tests/core/test_status.py::test_known_with_value_is_valid` |
| 75 | `src/dsdk/core/status.py:69` | compare | `tests/core/test_status.py::test_known_with_value_is_valid` |
| 76 | `src/dsdk/core/status.py:71` | compare | `tests/core/test_status.py::test_non_known_with_value_rejected[1-Status.UNKNOWN]` |
| 77 | `src/dsdk/core/status.py:73` | negate-if | `tests/core/test_status.py::test_known_with_value_is_valid` |
| 78 | `src/dsdk/core/status.py:73` | boolop | `tests/core/test_status.py::test_known_with_value_is_valid` |
| 79 | `src/dsdk/core/status.py:73` | compare | `tests/core/test_status.py::test_invalid_requires_nonblank_reason[]` |
