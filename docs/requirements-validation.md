# Slice 3 Requirements: the Validation, Re-resolution & Retrofit Stage

**Status:** Requirements — **substantially revised 2026-06-13** after a deep owner walkthrough of the *real* matched data. The earlier version of this document (the "offline, not re-matching" reconciliation gate) is **superseded**: profiling the live matches showed slice-2 resolution both **under-matched** (it never extracted the number from decorated values) and **mis-matched** (~11% of by-license matches point at the wrong company). Slice 3 therefore now **owns a corrected, live two-factor re-resolution** before it validates. · **Last updated:** 2026-06-13

The canonical requirements register is section 9 of [project-plan.md](project-plan.md); slice 3 elaborates plan §6 card 3 (the validation stage) plus the cross-validation rule that was always part of the method ([methodology.md](../reports/methodology.md) §3: *"every vendor `License_Number` is checked against the NCLBGC license table… catches typos, stale numbers"*) and the carried findings (REQ-09 report-don't-coerce, REQ-15 conservation, REQ-18 NCLBGC acquisition, REQ-20 canaries). The `V1`–`V11` ids are the slice-3 mined requirements on issue #17. Grounding (own docs only): [project-plan.md](project-plan.md) §3.4/§3.5/§4.5/§6/§9; [methodology.md](../reports/methodology.md) §1/§3; [data-cleaning-protocol.md](data-cleaning-protocol.md) "Cross-validation"; the join key in `data/DATA_DICTIONARY.md` (eVP `general_contractor_license_number` ↔ NCLBGC `License_Number`); the slice-2 client primitives in [design-nclbgc.md](design-nclbgc.md) §5.

## What slice 3 is (revised at the walkthrough)

The **validation gate** between the two sources and the database load (slice 4) — and, because the cross-validation that the gate depends on found slice-2's matching to be wrong, slice 3 now **corrects the matching first**. In order:

1. **Re-resolve, live, two-factor.** For every eVP vendor, find its real NC GC license by **number first, name second**, accepting a board record only when the board's **company name corresponds** to the vendor (reusing the slice-2 tokenless client; [design-nclbgc.md](design-nclbgc.md) §5).
2. **Retrofit.** Write each confirmed board license into the eVP `general_contractor_license_number` — fill blanks, overwrite invalid or wrong-company values — each logged as a correction (REQ-09: a confirmed enrichment, never imputation).
3. **Validate & gate.** Report the reconciliation metric, tally vocabulary/format violations against thresholds, assert conservation, and emit a **promote/halt** verdict.

It runs **live** against `portal.nclbgc.org` (the re-resolution needs board answers we do not have frozen), so the D3 tier-1 terms/robots note applies — already on file from slice 2. It regenerates a **new vintage** of the NCLBGC license master as a by-product. **Report, don't coerce (REQ-09):** the stored eVP cell is never altered except by a name-confirmed board match; no database write occurs (load is slice 4).

## Resolution — number first, name second, name-confirmed (V1–V4)

| ID | Implementation notes | Acceptance tests |
|---|---|---|
| V1 | **Live re-resolution, raw frozen first.** Drive from the slice-1 eVP deliverable (`name`, `general_contractor_license_number`). Resolve each vendor against the live portal one at a time with the politeness delay (REQ-18), reusing the slice-2 client's search/fetch/decode primitives. Verbatim fragments + decoded JSON + checksum manifest + the resolution report land in `data/raw/nclbgc/<run-id>/` **before** any check can abort (REQ-05 analog). New vintage; reproducible offline from the frozen bytes. Report keyed by run id. | `test_validation.py::test_reresolution_freezes_raw_then_decodes`; `::test_report_keyed_by_run_id` |
| V2 | **Number extraction → search by number (condition 1).** Derive the candidate number(s) from `general_contractor_license_number` by stripping **extraneous** decoration (any non-digit prefix/suffix/punctuation — `GC`, `WV`, `UL`, `CLG`, `PU`/`PW`, `L.`, dashes), trying every distinct digit-run and the leading-zero variant. Search the board by `AccountNumber`. A by-number hit is taken as **matched-by-license only if the board company name corresponds (V4).** The stored eVP cell is **not** mutated here (REQ-09: the search key is derived; the value is preserved until a confirmed retrofit). | `test_validation.py::test_number_extracted_from_decorated_value`; `::test_number_hit_with_corresponding_name_is_matched_by_license`; `::test_number_hit_without_name_correspondence_is_rejected` |
| V3 | **Name fallback (condition 2).** When no number is accepted — no usable number, no board hit, or a hit whose company name does **not** correspond — search by normalized company name. A name hit whose company corresponds is **matched-by-name**. Resolved by neither path is **unresolved** (recorded, never silently dropped; the difference). | `test_validation.py::test_name_fallback_when_number_not_accepted`; `::test_resolved_by_neither_is_unresolved` |
| V4 | **Name correspondence — name only, never imputed.** "Corresponds" is decided on the **company name alone**. Address and every other circumstantial signal are **rejected** (using them to keep a name we cannot otherwise tie together is imputation — REQ-09; recorded under "Deliberately not done"). The matcher normalizes case, punctuation, spacing, and legal suffixes, and recognizes the **same name written differently**, including `T/A`/`DBA` person↔business overlap (`Phillipsconstructionllc` ↔ `Phillips Construction, LLC`; `Christopher E Rhodes` ↔ `Christopher Egan Rhodes, T/A`). Names that genuinely share nothing do not correspond → unresolved. The acceptance threshold ("how close is close enough") is **pinned at the mid-slice owner checkpoint** against the live numbers (§8.2 step 3 analog). | `test_validation.py::test_name_matcher_accepts_spacing_suffix_and_ta_variants`; `::test_name_matcher_rejects_unrelated_names`; `::test_correspondence_uses_name_not_address` |

## Retrofit — the deliverable (V5, V6)

| ID | Implementation notes | Acceptance tests |
|---|---|---|
| V5 | **Retrofit the confirmed license into the eVP vendor master.** For each matched vendor, write the board-confirmed GC license into the **one** target column `general_contractor_license_number`: **fill** a blank, **overwrite** an invalid-format value, **overwrite** a valid-but-wrong-company value (a number that resolved to a different company) — each logged as a `Correction` with its reason (`reconcile-fill` / `reconcile-overwrite` / `reconcile-wrong-company`). The board is the source of truth; the stored cell is never altered except by a name-confirmed match (REQ-09). `license_number` is the NCLBGC table's field, **not** an eVP column — there is no second target. Output: the **corrected eVP vendor master** (the slice-4 input); the regenerated NCLBGC **license master** is the new-vintage source of truth and is not mutated by the retrofit. | `test_validation.py::test_blank_license_filled_from_match`; `::test_invalid_license_overwritten_from_match`; `::test_wrong_company_number_overwritten_from_name_match`; `::test_fill_logged_as_correction`; `::test_corresponding_match_is_byte_identical_noop` |
| V6 | **Reconciliation metric (the statistics).** Per-run, values-free: match rate %, the three bucket counts (matched-by-license / matched-by-name / unresolved), the fix counts (blanks filled, invalids overwritten, **wrong-company corrected**), and a run-over-run trend (first run = baseline). Keyed by run id. | `test_validation.py::test_metric_reports_match_rate_and_fix_counts` |

## Aggregate validation (V7, V8)

| ID | Implementation notes | Acceptance tests |
|---|---|---|
| V7 | **Vocabulary/format tally vs thresholds.** Tally the cleaning violation counts (eVP and the regenerated NCLBGC master) and gate each against **configured thresholds** — per-rule upper control limits at the ~95% one-sided edge of the baseline count (`x + 1.645·√x`), the total as a backstop. Threshold values are **re-derived from the live re-run profile at the checkpoint** (the earlier figures were computed on the flawed resolution and are provisional). Counts policy (REQ-20, §3.5): thresholds gate, never equality; a zero where tens are expected is a red flag. | `test_validation.py::test_violation_tally_within_threshold_passes`; `::test_violation_tally_over_threshold_fails` *(threshold values pinned at the checkpoint)* |
| V8 | **Cross-validation / referential check.** Every retrofitted license exists in the regenerated NCLBGC license master (true by construction; a violation is a structural failure → halt). The **wrong-company catches** — numbers that existed at the board but did not correspond, now corrected or sent unresolved — are **counted and reported**: methodology §3's "typos, stale numbers" made measurable. | `test_validation.py::test_every_retrofitted_license_exists_in_master`; `::test_wrong_company_count_reported` |

## The gate and its proof (V9, V10)

| ID | Implementation notes | Acceptance tests |
|---|---|---|
| V9 | **Promotion gate — report the match rate, halt on failure (A + zero-floor).** PROMOTE only when: row conservation holds (the cleaning identity **and** the reconciliation accounting `matched + unresolved = total`), the vocab/format tally is within threshold, the referential check holds, and the suite is green (§3.4). A low match rate is **reported, not a halt** (we keep the matched; the unresolved are the difference — and after the correction some real-but-unconfirmable licenses honestly stay unresolved rather than be guessed) — **except** a collapse to ~zero matches, which **halts** (§3.5). On PROMOTE the corrected vendor master + license master proceed to slice 4; on HALT, a red report and **no load**. | `test_validation.py::test_clean_run_promotes`; `::test_zero_match_rate_halts`; `::test_threshold_breach_halts` |
| V10 | **Poisoned-fixture red test.** A fixture seeded with an orphan (a confirmed license absent from the license master) and an out-of-vocabulary value must produce a **red report and halt before any load** — the proof the gate is not vacuous. | `test_validation.py::test_poisoned_fixture_halts_red_before_load` |

## The report (V11)

| ID | Implementation notes | Acceptance tests |
|---|---|---|
| V11 | **Validation report — values-free, keyed by run id.** Contains: the reconciliation metric (match rate %, bucket counts, fix counts incl. wrong-company, trend), the vocab/format violation counts vs thresholds, the conservation accounting, and the **verdict** (PROMOTE/HALT). **Counts and percentages only — never a vendor name, a license number, or any cell value** (§2.2). The per-record detail (which vendors unresolved, which licenses filled/overwritten, which numbers were wrong-company) goes only to the **gitignored audit zone**, exactly like slices 1/2. | `test_validation.py::test_report_is_values_free`; `::test_report_contains_metric_and_verdict` |

## Carried requirements (hold by construction)

REQ-09 (report-don't-coerce — the retrofit is a name-confirmed enrichment, not imputation; the search-key derivation does not mutate the stored value), REQ-15 (conservation), REQ-18 (NCLBGC acquisition primitives reused), REQ-20 (canaries are orientation only). The **mid-slice owner checkpoint** pins both the V4 name-correspondence threshold and the V7 vocab/format thresholds against the live re-run profile before the gate is closed.

## Deliberately not done (recorded so they are not silent gaps)

- **Address (or any non-name) match signal.** Correspondence is **name only**. Address would have rescued some name-mismatched number hits, but using it to keep a match we cannot confirm by name is imputation — the very thing REQ-09 forbids. Honest **unresolved** is preferred over a guessed match. *(Owner decision, 2026-06-13.)*
- **Subcontractor license-format check** (`data-cleaning-protocol.md` rule 2): non-GC trade licenses are stored, not matched; standardization is a cleaning concern, not slice-3 cross-validation.
- **HUB license-appropriateness** (rule 3): a PWC-specific analysis; out of scope for the independent rebuild.
- **Cross-field date rules:** no documented date anomaly exists in this data (`findings-summary.md` shows HUB/geography gaps, not dates), and dates are never altered. An optional flag-only safety net is deferred to the checkpoint if the live profile surprises us.

## Dependencies / follow-ups this slice opens

- **Requirement revisions (this slice authorizes them):** `requirements-nclbgc.md` **R4** ("a slice-1-flagged or blank number goes straight to name") and **REQ-09** ("identifiers are never prefix-stripped") are reworded to separate the **stored value** (never stripped; surfaces as a violation at cleaning) from the **derived search key** (a number extracted only to look the board up), and to add the **name-correspondence** rule on number hits. The slice-2 client's `resolve()` `isdigit()` gate is replaced by the V2/V3/V4 logic.
- **Live re-run = new vintage:** the re-resolution regenerates the NCLBGC license master and the resolution linkage; a golden re-baseline is captured at slice exit (§3.5).
- **Slice-4 verification:** settle where the license `status` field (Active/Invalid/Archived) truly lives — eVP vs NCLBGC — by reading the current data when the schema places it.
