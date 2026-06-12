# Requirements Traceability Matrix: Slice 1 (eVP pipeline)

**Status:** closed at the slice-1 gate · **Last updated:** 2026-06-12

A traceability matrix lets a requirement be followed in both directions:
forward (requirement to design to code to test to verification) and backward
(any test or module back to the requirement that justifies it). This document
closes the loop for slice 1: it pairs each carried-forward requirement with the
named tests that prove it, so the build can be reviewed by requirement id rather
than by reading the diff, and so no requirement is silently unimplemented or
covered only by a vacuous assertion.

The requirement text is in [requirements-evp.md](requirements-evp.md) and
section 9 of [project-plan.md](project-plan.md); the same ids are used here.

## Coverage matrix

| REQ | Requirement (short) | Covering tests | Status |
|---|---|---|---|
| 01 | Browserless fast-path parse; raise on template miss | `test_evp_parse.py::test_parses_records_from_captured_fixture`, `::test_template_miss_raises_specific_error`; `test_evp_client.py::test_clean_pull_freezes_raw_with_matching_checksums` | pass |
| 02 | Parity filters held in config | `test_drift.py::test_clean_fixture_summary_parses_to_expected_clauses`, `::test_clause_set_exact_comparison` | pass |
| 03 | Drift detection: clause set, count floor, HUB tri-state | `test_drift.py` (clean, non-active, added-clause, single-state-hub, floor, clause-set); `test_evp_client.py::test_record_floor_breach_halts`, `::test_drift_halts_but_raw_is_already_frozen` | pass |
| 04 | Loud halt naming the runbook; no auto-repair | `test_evp_client.py::test_drift_halts_but_raw_is_already_frozen`, `test_cli.py::test_acquire_evp_drift_exits_nonzero_and_names_runbook`; deliverable `runbook-evp-drift.md` | pass |
| 05 | Raw written before any check can abort | `test_evp_client.py::test_clean_pull_freezes_raw_with_matching_checksums`, `::test_drift_halts_but_raw_is_already_frozen`, `::test_template_miss_raises_but_html_is_frozen` | pass |
| 06 | Text-mode reads; "NA" and leading zeros survive | `test_tabular.py::test_text_mode_round_trip_preserves_na_zeros_and_blanks`; `test_idempotency.py::test_idempotent_through_serialized_round_trip` | pass |
| 07 | JSON booleans stringified; flags land Yes/No | `test_evp_parse.py::test_json_booleans_become_true_false_strings`; `test_cleaning_engine.py::test_flags_land_yes_no_end_to_end_on_fixture` | pass |
| 08 | Vocabularies read from source; config equals dictionary | `test_cleaning_config.py::test_every_configured_vocabulary_term_is_documented`, `::test_red_set_matches_dictionary` | pass |
| 09 | Report, don't coerce; identifiers never prefix-stripped | `test_cleaning_engine.py::test_report_dont_coerce_leaves_value_and_flags_violation`, `::test_real_license_oddities_surface_as_violations`; `test_transforms.py::test_license_id_never_prefix_stripped` | pass |
| 10 | Hybrid business-name casing; digit-led tokens unchanged | `test_transforms.py::test_business_name_hybrid_casing` | pass |
| 11 | Dedup semantics and the named drop record | `test_cleaning_engine.py::test_dedup_blank_key_rows_never_match`, `::test_dedup_most_complete_survives_and_drop_is_recorded`, `::test_dedup_tie_breaks_by_original_order` | pass |
| 12 | `row_key` ordinal; written to both files; lossless join | `test_tabular.py::test_pii_split_is_lossless_and_drops_red_from_deliverable`; `test_cleaning_engine.py::test_dedup_most_complete_survives_and_drop_is_recorded` | pass |
| 13 | `EXPECTED_COLUMNS` single source; manifest hard check | `test_cleaning_config.py::test_manifest_is_the_41_observed_fields`, `::test_config_keyset_is_the_manifest`; `test_tabular.py::test_manifest_check_passes_on_expected_and_fails_on_rename` | pass |
| 14 | Idempotency permanent; missing column hard-fails | `test_idempotency.py::test_idempotent_in_memory`, `::test_idempotent_through_serialized_round_trip`; `test_cleaning_engine.py::test_missing_configured_column_hard_fails` | pass |
| 15 | Conservation identity reconciles | `test_cleaning_engine.py::test_conservation_identity_reconciles_on_seeded_duplicate` | pass |
| 16 | Red columns never appear; two-file split; fixtures swept | `test_fixtures_no_pii.py::test_no_email_or_phone_pattern_in_any_fixture`; `test_tabular.py::test_pii_split_is_lossless_and_drops_red_from_deliverable`; `test_profiling.py::test_red_columns_are_counts_only_never_values` | pass |
| 17 | Multi-value cells standardize to `'; '` | `test_transforms.py::test_list_standardizes_to_semicolon_space` | pass |
| 20 | Orientation canaries, never gated | Verification-phase artifact, not a test (see below) | verify |
| 18 | NCLBGC acquisition | Deferred to slice 2 | deferred |
| 19 | Load order; embedding dimension | Deferred to slice 4 | deferred |

## Closure properties

The loop is closed when three properties hold, all confirmed at the gate:

1. **Coverage.** Every in-scope requirement (01 to 17) has at least one named,
   passing test. REQ-20 is intentionally not a test (below); REQ-18 and REQ-19
   are out of scope for this slice.
2. **No orphans.** Every slice-1 test traces back to a requirement above.
   `test_paths.py` and `test_imports.py` trace to the slice-0a harness rather
   than to a slice-1 requirement, and are foundational rather than orphaned.
3. **Currency.** As of the gate: 52 tests collected, 51 pass, 1 opt-in live test
   skipped offline; the live test passes on a local opt-in run.

## REQ-20 is a verification artifact, not a test

REQ-20 records the prior vintage's counts as orientation canaries only. A test
that gated equality against them would defeat their purpose: a new pull is a new
vintage and is expected to diverge. It is therefore checked in the verification
phase by human-read reconciliation (recorded on the slice card), not by an
automated assertion. The hard, machine-checked invariants are the
pipeline-controlled properties instead: manifest match, idempotency,
conservation, preserved leading zeros, and no imputation.

## Keeping this current

When a requirement changes or a test is renamed, update the matching row here in
the same change. Later slices append their own matrices (a NCLBGC section, a
validation section), so the document grows into the project-wide map from
requirements to the tests that prove them.
