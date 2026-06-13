# Slice 3 Requirements: the Validation & Reconciliation Stage

**Status:** Requirements phase — settled after the owner walkthrough of 2026-06-13. Grounded only in the project's own docs. · **Last updated:** 2026-06-13

The canonical requirements register is section 9 of [project-plan.md](project-plan.md); slice 3 elaborates the **validation stage** (plan §6 card 3) plus carried findings (REQ-09 report-don't-coerce, REQ-15 conservation, REQ-20 canaries). The `V1`–`V7` ids are the slice-3 mined requirements on issue #17. Grounding (own docs only): [project-plan.md](project-plan.md) §3.4/§3.5/§4.5/§6/§9; [data-cleaning-protocol.md](data-cleaning-protocol.md) "Cross-validation"; [design-nclbgc.md](design-nclbgc.md) §5; the per-column schema in `data/DATA_DICTIONARY.md`.

**What slice 3 is (clarified at the walkthrough):** the **validation + reconciliation gate** between the matched data (slice 2) and the database load (slice 4). It is **not** re-matching — slice 2 already produced the per-vendor resolution. Slice 3 (a) **reconciles** the licenses slice 2 discovered, (b) **validates** the result against thresholds, (c) reports a **metric**, and (d) emits a **promote/halt verdict**. It runs **offline** on the processed frames — no live acquisition, so no D3 terms gate. Report, don't coerce (REQ-09): no value is silently altered; the one authoritative enrichment (filling a board-confirmed license) is **logged as a correction**, never imputed. No database write occurs (load is slice 4).

## Inputs (V1)

| ID | Implementation notes | Acceptance tests |
|---|---|---|
| V1 | **Offline input contract.** Reads the slice-1 deliverable (`evp-vendor-master-…csv`), the slice-2 license master (`nclbgc-license-master-…csv`), and the slice-2 **`vendor → discovered-license` linkage** (the slice-2 follow-up below) — all from `data/processed/`. No live source, no DB write. Reports keyed by run id. | `test_validation.py::test_inputs_read_from_processed_only`; `::test_report_keyed_by_run_id` |

## Reconciliation — the deliverable (V2, V3)

| ID | Implementation notes | Acceptance tests |
|---|---|---|
| V2 | **Reconcile the discovered licenses into the vendor master.** Consume the slice-2 resolution (matched-by-license / matched-by-name / unresolved — **a match is a match**, by either path). For each **matched** vendor, write the board-confirmed GC license into the vendor record: **fill** a blank, **overwrite** an invalid/out-of-state value — each **logged as a correction** (authoritative enrichment, not imputation; REQ-09). The **license master is read-only** — the source of truth for the GC license. **Unresolved** vendors are left exactly as slice 2 flagged them (no license) and are the difference, not separately handled. Output: the **corrected eVP vendor master**, the slice-4 input. | `test_validation.py::test_blank_license_filled_from_match`; `::test_invalid_license_overwritten_from_match`; `::test_fill_logged_as_correction`; `::test_license_master_untouched` |
| V3 | **Reconciliation metric (the statistics).** Summarize V2 into per-run figures: match rate %, the three bucket counts, the fix counts (blanks filled, invalids overwritten), and a run-over-run trend (first run = baseline). Keyed by run id; values-free. | `test_validation.py::test_metric_reports_match_rate_and_fix_counts` |

## Aggregate validation (V4)

| ID | Implementation notes | Acceptance tests |
|---|---|---|
| V4 | **Aggregate vocabulary/format checks vs thresholds.** Cleaning (slices 1/2) already flagged vocab/format violations; slice 3 **tallies** those counts and gates them against **configured thresholds** (values set from the Analysis profile at the checkpoint; §4.5). Counts policy (REQ-20, §3.5): thresholds gate, never equality; a zero where tens are expected is a red flag. **No cross-field date check and no HUB check** — both deliberately out of scope (see "Deliberately not done"). | `test_validation.py::test_violation_tally_within_threshold_passes`; `::test_violation_tally_over_threshold_fails` *(threshold values pinned at the checkpoint)* |

## The gate and its proof (V5, V6)

| ID | Implementation notes | Acceptance tests |
|---|---|---|
| V5 | **Promotion gate — report the match rate, halt on failure (A + zero-floor).** PROMOTE only when: row conservation holds (the cleaning identity **and** the reconciliation accounting `matched + unresolved = total`), the vocab/format tally is within threshold, and the suite is green (§3.4). A low match rate is **reported, not a halt** (we keep the matched; the unresolved are the difference) — **except** a collapse to ~zero matches, which **halts** (§3.5: a zero where tens are expected means matching itself broke). On PROMOTE the corrected vendor master + license master proceed to slice 4; on HALT, a red report and **no load**. | `test_validation.py::test_clean_run_promotes`; `::test_zero_match_rate_halts`; `::test_threshold_breach_halts` |
| V6 | **Poisoned-fixture red test.** A fixture seeded with an orphan and an out-of-vocabulary value must produce a **red report and halt before any load** — the proof the gate is not vacuous. | `test_validation.py::test_poisoned_fixture_halts_red_before_load` |

## The report (V7)

| ID | Implementation notes | Acceptance tests |
|---|---|---|
| V7 | **Validation report — values-free, keyed by run id.** Contains: the reconciliation metric (match rate %, bucket counts, trend), the fix counts, the vocab/format violation counts vs thresholds, the conservation accounting, and the **verdict** (PROMOTE/HALT). **Counts and percentages only — never a vendor name, a license number, or any cell value** (§2.2). The detailed per-record audit (which vendors unresolved, which licenses filled) goes only to the **gitignored audit zone**, exactly like slices 1/2. | `test_validation.py::test_report_is_values_free`; `::test_report_contains_metric_and_verdict` |

## Carried requirements (hold by construction)

REQ-09 (report-don't-coerce — the reconciliation fill is a logged-correction enrichment, not imputation), REQ-15 (conservation), REQ-20 (canaries are orientation only). The **mid-slice owner checkpoint** pins V4's threshold values against the Analysis profile before implementation (§8.2 step 3).

## Deliberately not done (recorded so they are not silent gaps)

- **Subcontractor license-format check** (`data-cleaning-protocol.md` cross-validation rule 2): the non-GC trade licenses are stored, not matched; any standardization is a cleaning concern, not a slice-3 cross-validation.
- **HUB license-appropriateness** (rule 3): a PWC-specific analysis; out of scope for the independent rebuild.
- **Cross-field date rules:** no documented date anomaly exists in this data (`findings-summary.md` shows HUB/geography gaps, not dates), and dates are never altered. An optional flag-only safety net is deferred to the checkpoint if the profile surprises us.

## Dependencies / follow-ups this slice opens

- **Slice-2 follow-up (prerequisite):** persist the `vendor → discovered-license` linkage in a processed artifact, so V2 can join the blanks. Today slice 2's `resolution-report.json` carries only `{index, input-license, status}` — it drops the discovered license and the board key. Tracked as a separate issue.
- **Slice-4 verification:** settle where the license `status` field (Active/Invalid/Archived) truly lives — eVP vs NCLBGC — by reading the current data when the schema places it (`design-nclbgc.md` §4.2 cited Part-1 figures that may be mis-attributed).
