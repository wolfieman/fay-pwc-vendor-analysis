# Slice 2 Design: the NCLBGC pipeline

**Status:** design phase (solo; no section 2.4 panel trigger; doubles as the mid-slice owner checkpoint) · **Last updated:** 2026-06-13 · Supersedes the first draft, which was corrected after a full re-read of the documentation. (2026-06-13 provenance pass: citations re-pointed from the retired source archive to the project's own docs; no design content changed.)

**Grounding.** This design mirrors slice 1's pipeline exactly — verified against slice 1's processed artifact on disk (`data/processed/evp-vendor-master-vendor-*.csv`: 570 × 39, snake_case, multi-value cells `'; '`-packed, **not** normalized) and against `project-plan.md` sections 4 and 8 — pointed at NCLBGC's documented twelve-column license-details schema. Citations used below: `reports/methodology.md` sections 1 and 3; `data/DATA_DICTIONARY.md` (the NCLBGC section — the authoritative license dictionary) and `docs/master-data-documentation.md` (controlled vocabularies); `docs/data-cleaning-protocol.md` (the cross-validation rules); `docs/database-schema.md`; `reports/findings-summary.md`; `project-plan.md` sections 4 and 8, decisions D6 and D9, requirements REQ-08/09/16/17/18.

## 1. What is identical to slice 1 (the reused template)

Slice 2 is the same four-stage flow (acquire → analyze → clean → standardize) and the same data discipline as slice 1. **Reused unchanged:** `paths`, `http_client`, `tabular` (text-mode IO with `dtype=str` / NA-guessing off / `utf-8-sig`, the read-time column-manifest hard check, the snake_case rename + uniqueness assertion at processed-write, the two-file PII split), `cleaning/engine` (role dispatch in fixed order, report-don't-coerce, dedup, conservation), `cleaning/transforms`, `cleaning/records`, `profiling`.

Same as slice 1, unchanged: the zones layout (4.1), the header ruling (raw keeps the source's field names; snake_case is the final step at processed-write; the dictionary's per-column **dual-name mapping is the rename contract**, pinned by the dictionary-vs-config agreement test), `row_key` as the zero-padded ordinal, the idempotency / conservation / manifest discipline, the fixture + sanitizer + no-PII-sweep discipline, the three test markers, and the gate shape (8.3).

**The processed output is one flat table** — proven by the slice-1 CSV above — plus a PII sibling. Normalization into child / bridge tables is slice 4 (`database-schema.md`).

## 2. What slice 2 must customize (forced by the source, not chosen)

Three things genuinely differ because NCLBGC differs from eVP:

1. **Acquisition is multi-request and matched, not one GET.** Slice 1 fetched the entire dataset from one GET of an embedded `var data`. NCLBGC has no such page: we look each vendor up individually and **match** it. Per `methodology.md` section 1, resolution is **by license number first, with normalized-name retries** as the fallback (the eVP license number is what we search with; reports 3/4/6: extracted "for cross-validation").
2. **Parsing is stdlib `html.parser` over HTML fragments, not a regex over embedded JSON** (D6). Three fragment shapes: search → key, detail → record, qualifiers → packed rows.
3. **No drift detector.** Slice 1's `drift.py` guards a *shared, publicly mutable saved-search filter*. NCLBGC has no shared filter — each lookup is independent — so there is nothing to drift. Integrity is guarded instead by: the parser raising on a fragment template change (the `evp_parse` template-miss analog), the **resolve-or-flag** outcome (did we find it at all?), and the fact that finding a record **by the eVP number** is itself the confirmation that the number matched.

Everything else is slice 1's pipeline, unchanged.

## 3. Module manifest (mirrors 8.1)

| Module | Responsibility | Stratum | vs slice 1 |
|---|---|---|---|
| `paths`, `http_client`, `tabular`, `profiling`, `cleaning/{records,engine}` | reused as-is | — | unchanged |
| `nclbgc_client.py` | acquire shell: prime a session; for each slice-1 vendor, search (license-number first, normalized-name retry) and on a hit GET the detail / qualifiers / public-matters fragments per opaque key; write the verbatim fragments + decoded records JSON + manifest **before** any check can abort; record a per-vendor resolution status (matched-by-license / matched-by-name / unresolved); politeness delay; injectable transport | boundary IO | **replaces `evp_client`** — per-vendor loop + match, not one GET; no drift |
| `nclbgc_parse.py` | pure stdlib `html.parser`: search fragment → opaque key (the `onclick` token); detail fragment → one license record (mapping the fragment's label/field pairs onto the NCLBGC dictionary's field names); qualifiers fragment → the qualifier rows, scrubbing the `Status` header-bleed row; raises a specific error on a template miss | pure | **replaces `evp_parse`** — HTML fragments, not a `var data` regex |
| `cleaning/config.py` (extend) | add `LICENSE_CONFIG` + its `EXPECTED_COLUMNS` (the twelve-column schema in section 4.2): roles, the status vocabulary including `Invalid`/`Archived`, limitation Unlimited/Limited/Intermediate, dedup on `License_Number` | pure | a second `TableConfig`, same shape as `VENDOR_CONFIG` |
| `cleaning/transforms.py` (extend) | add one normalizer: strip the uniform `L.`/`Q.` type-sigil to bare digits, logged as a correction (N3) | pure | one new pure function |
| `cli.py` (extend) | add `acquire-nclbgc` (driven by the slice-1 license numbers), `profile-nclbgc` (values-free, mirrors eVP `profile`), and `clean-nclbgc` subcommands | shell | three subcommands |

The fixture sanitizer (`tools/make_nclbgc_fixture.py`) and the six fixtures already exist. There is **no** drift runbook (no drift).

## 4. The data: zones, the twelve-column schema, the flat output

### 4.1 Zones (mirrors 4.1)

- `data/raw/nclbgc/<run-id>/` (gitignored): the verbatim fragments (search / detail / qualifiers / public-matters HTML), `nclbgc-licenses.json` (the mechanically decoded license records, field names as the parser assigns them, values untouched), `acquire-manifest.json` (checksums, timestamp, count, client version), and `resolution-report.json` (the per-vendor match status **and the discovered board license** — the `vendor → license` link slice 3 reconciles, issue #27; the analog of slice 1's drift report).
- `data/processed/` (gitignored): the deliverable pair — `nclbgc-license-master-<YYYYMMDD>.csv` (no red columns) and `nclbgc-license-contacts-<YYYYMMDD>.csv` (`row_key` + the red columns) — plus `audit/<run-id>/` and `profile/`.

### 4.2 The license-details schema (twelve columns, per the NCLBGC data dictionary)

One flat table, one row per license; multi-value fields are `'; '`-packed (REQ-17 — splitting into rows is slice 4's job).

| # | Source field | snake_case target | Type | Sensitivity | Role / observed vocabulary |
|---|---|---|---|---|---|
| 1 | License_Number | license_number | text id | yellow | dedup key; `L.` sigil stripped to digits (N3); the join key back to eVP |
| 2 | Company_Name | company_name | text | yellow | hybrid business-name casing + legal suffixes |
| 3 | Address | address | text | yellow | whitespace / proper case |
| 4 | Phone | phone | text | **red** | `###-###-####` |
| 5 | Issue_Date | issue_date | date | white | `MM/DD/YYYY` text |
| 6 | Expiration_Date | expiration_date | date | white | `MM/DD/YYYY` text |
| 7 | Status | status | category | white | Active / Expired / Suspended / Revoked / Inactive / Pending / **Invalid** / **Archived** (the last two added from the data — `findings-summary.md`: 263 active, 23 invalid, 9 archived) |
| 8 | License_Limitation | license_limitation | category | white | Unlimited / Limited / Intermediate |
| 9 | Classifications | classifications | text multi | white | `'; '`-packed |
| 10 | Qualifier_Number | qualifier_number | text multi | yellow | `'; '`-packed; `Q.` sigil stripped (N3) |
| 11 | Qualifier_Name | qualifier_name | text multi | **red** | `'; '`-packed; hybrid casing |
| 12 | Qualifier_Status | qualifier_status | category multi | white | Active / Inactive / Expired; `'; '`-packed |

Red set = `Phone`, `Qualifier_Name` (REQ-16; `database-schema.md` `license_pii` / `qualifier_pii`). The packed `qualifier_name` cell lives only in the contacts sibling. Dedup key = `License_Number` (the dedup/join key in the NCLBGC section of `DATA_DICTIONARY.md`; `data-cleaning-protocol.md`). The fragment's non-schema fields (for example the detail's constant `Account Type` = "License") are dropped at parse.

### 4.3 row_key, the PII split, the ingest contract (mirrors 4.3 and 4.5)

Identical to slice 1: `row_key` is the zero-padded ordinal in the decoded records; the two processed files join losslessly on it and it keys every audit record; the column manifest is hard-checked at read; the conservation identity `rows_in == rows_out + dedup_drops` is asserted at end of run with a seeded-duplicate red test. A new NCLBGC section of the data dictionary (4.4) carries the dual-name mapping, the vocabularies with provenance tags, the red set, the dedup key, and the join key (`License_Number`), with a dictionary-vs-config agreement test.

## 5. The match / resolution contract (the slice-2-specific logic)

For each slice-1 vendor (its cleaned `name` + `general_contractor_license_number`, already classified by slice 1):

1. **Valid NC digit license number** (slice 1's 379 digit class) → search NCLBGC by number. A hit *is* the confirmation that the number matched; fetch and parse; status = **matched-by-license**. No hit → step 2.
2. **Name fallback** (the documented "normalized-name retries") → search by company name; a hit gives status = **matched-by-name**. Name matching is fuzzier than a number hit, but slice 3 treats a match as a match (it does not re-scrutinize slice 2's matches — see `requirements-validation.md`).
3. **Slice-1-flagged number** — out-of-state / prefixed / multi-value (the 34 "other", for example `WV063716`, `NY Lic: 2045482`) or blank (the 157) → skip the number (an NC-only board cannot match it) and go straight to name (step 2).
4. **Resolved by neither** → status = **unresolved** (recorded with the searched value and a reason); never silently dropped; counted in the run report; slice 3 excludes the unusable row.

The per-vendor resolution status is the slice-2 output that feeds slice 3's reconciliation metric (orphan count, match rate, trend). The aggregate referential validation — every number exists, subcontractor formats match classification types, HUB vendors hold proper licenses (`docs/data-cleaning-protocol.md` "Cross-validation"; `methodology.md` section 3) — is **slice 3**, not here.

## 6. Seams (pure core vs IO shell)

- **Pure:** `nclbgc_parse`, `LICENSE_CONFIG`, the sigil-strip transform, the cleaning engine — all tested offline against the committed fixtures.
- **IO shell:** `nclbgc_client` (the only network code; injectable transport for offline contract tests), `tabular` (disk), `cli`.

## 7. Decisions (revised, grounded)

| # | Decision | Ruling | Grounding |
|---|---|---|---|
| N1 | Output shape | **One flat license-details table** (twelve columns), qualifiers + classifications `'; '`-packed, plus a PII sibling; not normalized | methodology "295 × 12"; the NCLBGC dictionary (`DATA_DICTIONARY.md`); the verified slice-1 CSV; REQ-17; database-schema normalizes at slice 4 |
| N2 | Matching | License-number first, normalized-name fallback, **in slice-2 acquisition**; resolve-or-flag; a by-number hit is the cross-check | methodology section 1 "with normalized-name retries"; reports 3/4/6 |
| N3 | Sigil strip | Strip the uniform `L.`/`Q.` type-sigil at processed-write (logged correction); raw keeps it verbatim. A **deliberate deviation** from the original, which stored `L.xxxxx`; scopes REQ-09's no-prefix-strip to *meaningful* prefixes, which still surface as violations | methodology section 1 stored `L.xxxxx`; REQ-09 |
| N4 | Parser | Stdlib `html.parser` only; revisit only if the markup defeats it | D6 |
| N5 | No drift detector | NCLBGC has no shared filter; integrity = the parser's template-miss guard + resolve-or-flag + by-number confirmation | contrast slice 1's `drift.py` (8.1) |
| N6 | Politeness | One vendor at a time with a fixed delay; the live run is opt-in and never in CI | REQ-18 |

## 8. Gate checklist (mirrors 8.3, adapted)

1. Dated terms/robots note on the card (recorded at entry).
2. Verbatim raw frozen (fragments + decoded JSON + checksum manifest), re-parsable offline.
3. Column-manifest check green on the live shape, demonstrably red on a doctored fixture.
4. NCLBGC dictionary committed; dictionary-vs-config agreement test green.
5. Cleaning idempotent in the raw header space (in memory and through a serialized round-trip).
6. Conservation identity holds and reconciles on a seeded-duplicate fixture.
7. The parser raises on a template-miss fixture; resolve-or-flag exercised on fixtures (matched-by-license / matched-by-name / unresolved).
8. Multi-value fields land `'; '`-packed end-to-end (qualifiers, classifications); the `Status` header-bleed is scrubbed; the `L.`/`Q.` sigil is stripped (fixture-driven).
9. PII: structural test proves no red column in the deliverable and no red-column values or PII patterns in any tracked artifact; pattern sweep clean over `tests/fixtures/`; the two-file split joins losslessly on `row_key`, unique in both; the packed `qualifier_name` lives only in contacts.
10. Processed deliverable written snake_case with the uniqueness assertion exercised.
11. Profile and run report (values-free; match-rate counts) attached to the card; divergence from canaries explained.
12. Golden baseline captured outside the repository (machine-local, recorded locally).
13. CI green throughout; opt-in live run resolves every slice-1 license number or flags it.

## 9. Test surface (set in the test-first phase)

Pure parser tests against the committed fixtures: search → key; the empty search yields no key (the flag path); detail → a license record with the `L.` prefix present; qualifiers → packed rows; the quirk fixture scrubs the `Status` header-bleed and packs the multi-qualifier rows; the `Q.` sigil is stripped. Config-vs-dictionary agreement, conservation, idempotency, and the manifest red test reuse the slice-1 patterns. A **name-search result fixture is still owed** (the spike froze only license-number searches). `docs/requirements-nclbgc.md` binds the requirements register to these tests at the start of the build, mirroring slice 1.
