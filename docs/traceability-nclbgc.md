# Requirements Traceability Matrix: Slice 2 (NCLBGC pipeline)

**Status:** closed at the slice-2 gate · **Last updated:** 2026-06-12

This matrix closes the requirements loop for slice 2, the companion to
[traceability-evp.md](traceability-evp.md): it pairs each slice-2 requirement
with the named tests that prove it, so the build can be reviewed by requirement id
rather than by reading the diff, and so no requirement is silently unimplemented
or covered only by a vacuous assertion.

The requirement text is in [requirements-nclbgc.md](requirements-nclbgc.md)
(the `R1`–`R9` mined ids, elaborating REQ-18 + carried findings) and section 9 of
[project-plan.md](project-plan.md) (the `REQ-*` register); the same ids are used
here.

## Coverage matrix

| ID | Requirement (short) | Covering tests | Status |
|---|---|---|---|
| R1 | Tokenless session flow: prime, search POST, opaque keys | `test_nclbgc_client.py::test_raw_frozen_and_reparsable`; `test_nclbgc_cli.py::test_acquire_nclbgc_freezes_a_run` | pass |
| R2 | Per-key detail/qualifiers/matters fragments; raw frozen first | `test_nclbgc_client.py::test_raw_frozen_and_reparsable`; `test_nclbgc_parse.py::test_decode_record_combines_detail_with_packed_qualifiers` | pass |
| R3 | Stdlib parsing; empty search → no key; template miss raises | `test_nclbgc_parse.py::test_search_keys_extracted_from_onclick`, `::test_empty_search_yields_no_keys`, `::test_detail_parses_to_part_ii_fields`, `::test_template_miss_raises` | pass |
| R4 | Iterate slice-1 licenses; license-first match, name fallback; resolve-or-flag | `test_nclbgc_client.py::test_resolution_statuses`, `::test_flagged_license_goes_straight_to_name`; live `test_integration_nclbgc.py::test_live_resolve_matches_expectations` | pass / live opt-in |
| R5 | Qualifier cell-split, `Status` header-bleed scrub, child-table shape | `test_nclbgc_parse.py::test_qualifiers_parse_to_rows`, `::test_qualifiers_scrub_status_header_bleed`; `test_nclbgc_clean.py::test_packed_qualifier_columns_clean_per_element` | pass |
| R6 | License vocabulary incl. Invalid/Archived; report-don't-coerce; sigil strip | `test_nclbgc_clean.py::test_report_dont_coerce_on_out_of_vocabulary_status`, `::test_sigils_stripped_on_license_and_qualifier_numbers`; `test_cleaning_config.py::test_license_every_configured_vocabulary_term_is_documented` | pass |
| R7 | PII split: red = Phone, Qualifier_Name; two files; fixtures swept | `test_nclbgc_cli.py::test_clean_nclbgc_writes_license_pair_without_red_columns`; `test_cleaning_config.py::test_license_red_set_matches_dictionary`; `test_fixtures_no_pii.py::test_no_email_or_phone_pattern_in_any_fixture` | pass |
| R8 | Config reconciliation: manifest = config = parser = dictionary | `test_cleaning_config.py::test_license_manifest_is_the_12_documented_fields`, `::test_license_snake_case_rename_matches_dictionary`, `::test_license_config_keyset_is_the_manifest`; `test_nclbgc_clean.py::test_license_config_manifest_matches_the_parser_fields` | pass |
| R9 | Join/dedup on License_Number; conservation + idempotency on the table | `test_nclbgc_clean.py::test_license_keys_and_red_set`, `::test_conservation_and_idempotency` | pass |

## Reused slice-1 requirements (re-exercised, not re-implemented)

The pure core is shared, so these hold by construction and are re-exercised by the
NCLBGC tests above rather than by new code.

| REQ | Held by | Re-exercised by |
|---|---|---|
| 06 | text-mode tabular IO | `test_nclbgc_clean.py::test_conservation_and_idempotency` (serialized round-trip) |
| 09 | engine report-don't-coerce | `test_nclbgc_clean.py::test_report_dont_coerce_on_out_of_vocabulary_status` |
| 13 | `LICENSE_EXPECTED_COLUMNS` manifest, hard read-time check | `test_cleaning_config.py::test_license_config_keyset_is_the_manifest`; `test_nclbgc_cli.py::test_clean_nclbgc_writes_license_pair_without_red_columns` |
| 14 | permanent idempotency | `test_nclbgc_clean.py::test_conservation_and_idempotency` |
| 15 | conservation identity | `test_nclbgc_clean.py::test_conservation_and_idempotency` |
| 16 | red-column split + fixture sweep | `test_fixtures_no_pii.py`; `test_nclbgc_cli.py::test_clean_nclbgc_writes_license_pair_without_red_columns` |
| 17 | `'; '` multi-value packing | `test_nclbgc_clean.py::test_packed_qualifier_columns_clean_per_element` |
| 18 | NCLBGC acquisition | R1, R2, R4 above |

## Closure properties

The loop is closed when three properties hold, all confirmed at the gate:

1. **Coverage.** Every slice-2 requirement (R1–R9) has at least one named,
   passing test; the reused REQ rows above show each carried slice-1 requirement
   is re-exercised on the license table, not assumed.
2. **No orphans.** Every slice-2 test traces back to a requirement above.
   `test_nclbgc_parse.py`, `test_nclbgc_client.py`, `test_nclbgc_clean.py`,
   `test_nclbgc_cli.py`, the NCLBGC half of `test_cleaning_config.py`, and the
   live `test_integration_nclbgc.py` all map to an `R*` id.
3. **Currency.** As of the gate: 76 tests collected, 75 pass, 1 opt-in live test
   skipped offline; the live test passes on a local opt-in run.

## No drift detector (decision N5)

Slice 1's `drift.py` row in the eVP matrix has no analog here. NCLBGC has no
shared, publicly mutable saved-search filter to drift, so there is nothing for a
drift detector to guard. Integrity is instead the parser's template-miss error
(R3), the resolve-or-flag outcome (R4), and the fact that a by-number hit is
itself the confirmation that the number matched — recorded so a future reader does
not mistake the missing detector for an omission.

## Keeping this current

When a requirement changes or a test is renamed, update the matching row here in
the same change. The project-wide map from requirements to proving tests is the
union of this matrix and [traceability-evp.md](traceability-evp.md); later slices
append their own.
