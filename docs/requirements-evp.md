# Slice 1 Requirements: the eVP Pipeline

**Status:** committed before design and code, per the plan's requirements phase · **Last updated:** 2026-06-12

The canonical requirements register is section 9 of [project-plan.md](project-plan.md); the IDs below are the same IDs. This document elaborates the slice-1 subset for implementation and binds each requirement to its acceptance tests, so the PR review checks the diff against REQ ids rather than prior code. Entry criterion (the dated terms/robots note) is recorded on the slice card. REQ-18 and REQ-19 are later-slice requirements and are not elaborated here.

## Acquisition (REQ-01 to REQ-05)

| ID | Implementation notes | Acceptance tests |
|---|---|---|
| REQ-01 | One GET of the saved-search results page (record id `20199579-3165-f111-a824-001dd812e0a9`, `page=1`). Extraction: a DOTALL regex over the inline `var data` script variable, then HTML-entity unescape, then JSON parse. The parser raises a specific exception when the variable is absent (template change). The record id is public by the portal's design; the defense is REQ-03, not secrecy. | `test_evp_parse.py`: extracts records from the sanitized captured fixture; raises on a fixture with the variable removed |
| REQ-02 | Expected filters: status Active (code `1`), classification Public Utilities (code `790550003`), HUB deliberately blank. These constants live in config, not inline. | `test_drift.py`: the clean fixture passes the expected-clause check |
| REQ-03 | Drift detection is pure predicates over the parsed page: (a) the filter summary clause set equals the expected set exactly, an added clause is drift; (b) record count is at or above the floor (seeded 500; confirmed at the owner checkpoint; stored in config); (c) HUB tri-state presence as a halt-and-inspect alarm with a recorded human override path. | `test_drift.py`: red on all three drift fixtures (non-Active record; added clause; single-category HUB); green on the clean fixture |
| REQ-04 | On drift the client halts loudly and prints the runbook path (`docs/runbook-evp-drift.md`, committed this slice). No automated repair (decision D2). | `test_cli.py`: drift path exits nonzero and names the runbook (offline, fixture-driven) |
| REQ-05 | The client writes the verbatim response bytes, the decoded JSON, and a checksum manifest to `data/raw/evp/<run-id>/` (run id `<YYYYMMDD>T<HHMMSS>-evp`) before any check can abort the run; the drift report is written separately after detection. | `test_evp_client.py` (mock transport): raw files exist and checksums match before the drift predicate is consulted |

## Ingest and parse boundary (REQ-06, REQ-07)

| ID | Implementation notes | Acceptance tests |
|---|---|---|
| REQ-06 | All tabular reads are text-mode: every cell a string, NA-token guessing off, `utf-8-sig`. A county literally named "NA" is data; leading zeros survive; dates stay `MM/DD/YYYY` text. The rules live in one chokepoint module (`tabular.py`). | `test_tabular.py`: round-trip preserves the string "NA", a leading-zero ZIP, and an empty cell |
| REQ-07 | The parse boundary stringifies JSON booleans via `str()` (so `True`/`False`), and the flag vocabulary map is case-folded; the ten trade flags land as canonical `Yes`/`No` end to end. | `test_evp_parse.py`: fixture booleans arrive as `True`/`False` strings; `test_cleaning_engine.py`: cleaned flags are exactly `Yes`/`No` |

## Cleaning (REQ-08 to REQ-12)

| ID | Implementation notes | Acceptance tests |
|---|---|---|
| REQ-08 | Vocabularies are encoded from the slice-1 profile of the live pull, not assumed; the dictionary records observed-vs-documented provenance per vocabulary (under the locked filter only Active status is observable). Known carried-forward sets: HUB and NCSBE (NC Small Business Enterprise certification) are Certified / Not Certified / blank with blank never imputed; NCeProcurement is three-valued; the GC limitation includes a literal `None`; the HUB category list includes `Asian American`. | `test_cleaning_config.py`: the config vocabularies equal the dictionary's (agreement test) |
| REQ-09 | Report, don't coerce: a violating value is flagged and left unchanged; no imputation; identifiers never prefix-stripped. | `test_cleaning_engine.py`: an out-of-vocabulary value yields a Violation and an unchanged cell |
| REQ-10 | Hybrid business-name casing; digit-led tokens (for example `42YL`, `51ST`) are left unchanged. | `test_transforms.py`: cases for all-caps input, acronym preservation, digit-led tokens |
| REQ-11 | Dedup semantics: blank-key rows never match each other; the most complete row survives (completeness = count of non-blank cells); ties break by original row order; each drop logs the named dedup-drop record carrying both the dropped and surviving `row_key`. | `test_cleaning_engine.py`: one test per semantic plus the drop-record shape |
| REQ-12 | `row_key` is the record's zero-padded ordinal in the decoded raw extract (per-run identity, unique by construction); written into both processed files; all audit records reference it. Cross-run identity is the dedup key (`Name` + `GeneralContractorLicenseNumber`). | `test_tabular.py`: the two processed files join losslessly on `row_key`, unique in both |

## Run contracts (REQ-13 to REQ-15)

| ID | Implementation notes | Acceptance tests |
|---|---|---|
| REQ-13 | `EXPECTED_COLUMNS` in config is the single source of the field manifest (41 fields as observed 2026-06-10; re-confirmed by this slice's profile). Tests assert against it, never a literal count. Read-time mismatch is a hard failure. Shape change procedure: config, dictionary, and fixtures regenerate in one commit. | `test_tabular.py`: doctored fixture (renamed field) hard-stops; the live-shape fixture passes |
| REQ-14 | Idempotency: re-cleaning cleaned output yields zero corrections, asserted in memory and through a serialized round-trip, in the raw header space before the snake_case rename. The engine hard-fails if a configured column is absent (no vacuous pass). | `test_idempotency.py` (permanent); `test_cleaning_engine.py`: missing-configured-column red test |
| REQ-15 | Conservation: `rows_in == rows_out + dedup_drops` asserted at end of run, consuming the dedup-drop records. | `test_cleaning_engine.py`: seeded-duplicate fixture produces one drop and the identity reconciles |

## PII and outputs (REQ-16, REQ-17)

| ID | Implementation notes | Acceptance tests |
|---|---|---|
| REQ-16 | Red columns this slice: `MainContactName`, `MainContactEmail`, `MainContactPhone`. Their values never appear in any tracked artifact, fixture, or card text; the columns are never tracked; audit logs are PII-bearing and never tracked; fixtures pass a pattern sweep (email and phone regexes over all fields). The cleaned output is a two-file split: the deliverable without red columns plus a contacts sibling (`row_key` + red columns), both gitignored. | `test_fixtures_no_pii.py` (permanent structural test); `test_tabular.py`: split files carry the right columns |
| REQ-17 | Multi-value cells standardize to `'; '` delimiting during cleaning; splitting into rows is the database slice's job. | `test_transforms.py`: list normalization cases |

## Verification inputs (REQ-20)

| ID | Implementation notes |
|---|---|
| REQ-20 | Orientation canaries only, never gate equality: about 7,100 corrections, 64 strict license-format violations, about 570 records, from the prior verified pull (a different vintage and filter scope from the published Part-1 study's 295). Divergence is explained in the run report, not forced to match. A zero where tens are expected is itself a red flag. |

## Sampling and confidence (clarification, 2026-06-12)

95% confidence is retained as a recorded standard, homed where it is the correct
instrument rather than applied to the wrong artifact:

- **Committed test fixture (this slice):** sized by code-path coverage, not a
  confidence interval — every observed vocabulary value and every quirk appears at
  least once. A random acceptance sample is rejected here because the
  highest-value cases are rare (the 7-character ZIP and the dedup pair are each
  about 1 in 570) and a random draw would systematically under-represent them.
- **Live conformance (this slice):** the opt-in integration test asserts over the
  full population (a census, every record), which is the limiting case of a
  confidence interval — 100% confidence, zero margin — and strictly stronger than a
  95% acceptance sample. Where a future population is too large or too costly to
  census (statewide eVP without the Public Utilities filter; NCLBGC per-license
  enrichment — cards 3 and 6), fall back to a zero-defect acceptance sample at 95%
  confidence with a 5% defect ceiling (n about 59, the rule of three).
- **Published representative sample (card P, D10):** when a published dataset must
  support inference, size it for proportion estimation at 95% confidence, 5% margin,
  p = 0.5, with the finite-population correction on N about 570 (n about 230).
