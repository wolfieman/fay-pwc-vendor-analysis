# Slice 3 Design: validation, re-resolution & retrofit

**Status:** design phase (solo; no section 2.4 panel trigger — a validation module plus a reuse of the slice-2 client clears none of the triggers). **Rewritten 2026-06-13** — the earlier offline-backfill design is superseded: profiling the live matches showed slice-2 resolution under-matched (the `isdigit()` gate never extracted numbers from decorated values) and mis-matched (~11% of by-license matches point at the wrong company), so slice 3 now does a **corrected, live two-factor re-resolution** before it validates. · **Last updated:** 2026-06-13

**Grounding.** Verified against the real artifacts and code: the slice-1 deliverable (`data/processed/evp-vendor-master-vendor-*.csv`, 570 rows), the slice-2 frozen run and client (`nclbgc_client.py` `resolve`/`_search`/`_fetch`/`decode_record`; `nclbgc_parse.py`), the cleaning engine + `Correction` record, `tabular.py`, and the `_clean_table` run-report writer. Requirements: [requirements-validation.md](requirements-validation.md) (V1–V11); register [project-plan.md](project-plan.md) §9 (REQ-09, REQ-15, REQ-18, REQ-20); [methodology.md](../reports/methodology.md) §1/§3; the join key in `data/DATA_DICTIONARY.md`.

## 1. What changed from the pre-pivot design

The earlier design read a frozen `resolution-report.json`, joined it to the vendor master, and retrofitted — treating slice-2's matches as final ("a match is a match"). The walkthrough overturned that premise:

- Slice-2 `resolve()` gates the board number search on `license_number.isdigit()`, so a decorated value (`GC1000187`, `42892 UL`) **never has its number tried** — it jumps to a name search, sometimes returning a *different* license.
- A by-number hit is accepted with **no company check**, so ~11% (41/374) of by-license matches resolve to the **wrong company** (the number exists but isn't this vendor's).

So slice 3 re-resolves **live**, **number-first with name confirmation**, then retrofits and validates. The offline backfill is gone.

## 2. What is reused unchanged

| Reused | From | Used for |
|---|---|---|
| `_search`, `_fetch`, `decode_record`, the raw-first freeze, the politeness delay | `nclbgc_client.py`, `nclbgc_parse.py` | the live board lookups during re-resolution (V1) |
| `clean_table`, `Correction`, the run-report shape, `LICENSE_CONFIG` | `cleaning/`, `cli.py::_clean_table` | regenerate the NCLBGC license master (new vintage); each retrofit is a logged `Correction` |
| `transforms.business_name_case`, `strip_sigils` | `cleaning/transforms.py` | the name matcher's normalization; sigil-strip the discovered license to bare digits |
| `transforms.normalize_license` (blank/digits valid; else `non-standard-license`) | `cleaning/transforms.py` | the validity test that decides fill vs overwrite |
| `tabular.read_csv`/`write_csv`, values-free report + gitignored audit discipline | `tabular.py`, `cli.py` | read the eVP deliverable; write the corrected master + audit + report |
| `paths`, the three pytest markers, the gate shape (§8.3 analog) | repo-wide | unchanged |

## 3. Module manifest

| Module | Responsibility | Stratum | vs prior slices |
|---|---|---|---|
| `matching.py` (new) | **pure:** `extract_numbers(value) -> list[str]` (strip extraneous decoration, every distinct digit-run + leading-zero variant); `corresponds(evp_name, board_name) -> bool` (the **name-only** matcher — normalize case/punctuation/spacing/suffixes, handle `T/A`/`DBA` person↔business overlap; threshold calibrated at the checkpoint) | pure | new — the heart of the correction |
| `resolution.py` (new) | the two-factor resolution **policy** over injected search primitives: number(s) → board hit **and** `corresponds` → matched-by-license; else name search → `corresponds` → matched-by-name; else unresolved. Returns a `Resolution` per vendor (status + confirmed board license). Pure policy; the live IO is injected (the slice-2 client) | pure policy | replaces `nclbgc_client.resolve`'s `isdigit` gate |
| `validation.py` (new) | **pure:** `retrofit`, `metric`, `tally_violations`, `gate`, and the `ValidationReport` assembly | pure | new |
| `cleaning/config.py` (extend) | `VALIDATION_THRESHOLDS` (per-rule UCLs + the match-rate floors + the name-correspondence threshold), a typed, documented constant; values pinned at the checkpoint | pure | a config constant |
| `cli.py` (extend) | `validate` subcommand: drive the live re-resolution (reusing the client) → regenerate the license master → retrofit → validate → write the corrected master + PII audit + values-free report | shell | one subcommand |

Slice-3 fixtures are small: synthetic HTML search/detail fragments exercising the resolution branches (number-corresponds, number-wrong-company→name, name-only, unresolved) plus a clean and a poisoned CSV frame, under `tests/fixtures/validation/`. They follow the no-PII sweep (synthetic names/addresses).

## 4. The two-factor resolution contract (V2–V4)

For each eVP vendor (`name`, `general_contractor_license_number`):

1. **Extract** candidate numbers: strip extraneous decoration, collect every distinct digit-run and the leading-zero variant (`WV063716` → {`63716`, `063716`}; `RLCO000867/RLQA000362` → {`867`,`000867`,`362`,`000362`}).
2. For each candidate, **search the board by number**. On a hit, accept **iff `corresponds(evp_name, board_company)`** → `matched-by-license` (confirmed). A hit whose company does not correspond is **not** accepted (the wrong-company case).
3. If no number is accepted, **search by name**; a hit whose company corresponds → `matched-by-name`.
4. Else → `unresolved` (recorded, never dropped).

The **stored eVP cell is never mutated here** (REQ-09): the extracted number is a *search key*, not a value edit. The confirmed board `License_Number` (sigil-stripped to bare digits) is the discovered license carried to the retrofit.

## 5. The name matcher (V4) — name only

`corresponds(evp_name, board_name)` is the only correspondence signal — **address and all other fields are excluded** (using them is imputation, REQ-09; recorded). Sketch:

- Normalize both: case-fold, strip punctuation, collapse whitespace, drop legal suffixes (`LLC`, `Inc`, `Co`, `Corp`, `Ltd`, …) and the `T/A`/`DBA` connectors.
- Compare by token overlap, so the **same name written differently** matches (`Phillipsconstructionllc` ↔ `Phillips Construction, LLC`) and a `T/A`/`DBA` line that still shares the person's name matches (`Christopher E Rhodes` ↔ `Christopher Egan Rhodes`). Names that share nothing (`B & B Crane Service` ↔ `Timothy B. Powell`) do **not** correspond → that vendor goes unresolved rather than be rescued by another field.
- The acceptance bar (overlap ratio / handling of one-token person names) is **calibrated at the owner checkpoint** against the live numbers, like the V7 thresholds. It is data, not a magic constant — pinned in `VALIDATION_THRESHOLDS`.

The same normalized comparator serves both the number-hit confirmation and the name-search fallback — one matcher, two call sites.

## 6. The retrofit (V5)

For each matched vendor, `cur` = the cleaned eVP `general_contractor_license_number`, `disc` = the confirmed board license:

| Vendor state | Action | Logged |
|---|---|---|
| unresolved | leave as-is (the difference) | — |
| matched, `cur` blank | **fill** with `disc` | `Correction("reconcile-fill")` |
| matched, `cur` malformed (`non-standard-license`) | **overwrite** with `disc` | `Correction("reconcile-overwrite")` |
| matched, `cur` valid digits but a different company resolved (wrong-company) | **overwrite** with `disc` | `Correction("reconcile-wrong-company")` |
| matched, `cur` digits == `disc` | no-op | — |

`general_contractor_license_number` is the **single** target (`license_number` is the NCLBGC table's field, not the eVP's). The regenerated license master is the read-only source of truth; the retrofit never mutates it. Output: the corrected eVP vendor master (slice-4 input).

## 7. Metric, tally, gate, report (V6–V11)

- **Metric (V6):** match rate %, the three buckets, the fix counts (fill / overwrite / **wrong-company**), trend vs the prior validation run.
- **Tally (V7):** read the eVP and (regenerated) NCLBGC run-reports' `violations_by_rule`; gate each per-rule count against its UCL in `VALIDATION_THRESHOLDS` (x + 1.645·√x, one-sided ~95%), total as backstop. **Re-derived from the live re-run profile at the checkpoint** — the pre-pivot figures (GC≤44 … total≤90) were computed on the flawed resolution and are provisional.
- **Cross-validation (V8):** every retrofitted license exists in the license master (else structural halt); the wrong-company count is reported.
- **Gate (V9):** A + zero-floor. PROMOTE on conservation (cleaning identity **and** `matched + unresolved = total`) + tally within threshold + referential check + green suite. Low match rate REPORTS; HALT on near-zero collapse (<5%), threshold breach, or structural failure. **V10** poisoned fixture proves the halt.
- **Report (V11):** values-free counts/percentages + verdict; per-record detail (PII) only to the gitignored audit zone.

## 8. Seams

- **Pure:** `matching` (extract/corresponds), `resolution` (policy over injected primitives), `validation` (retrofit/metric/tally/gate), `VALIDATION_THRESHOLDS` — all tested offline against fixtures with a mock transport for the injected search.
- **IO shell:** `cli.validate` (the only network path here, reusing the slice-2 client; writes the corrected master + audit + report).

## 9. Decisions

| # | Decision | Ruling | Grounding |
|---|---|---|---|
| V-D1 | Where re-resolution lives | In the validation slice (live), reusing the slice-2 client primitives; correction precedes the gate | owner walkthrough; methodology §3 cross-validation |
| V-D2 | Number handling | Extract a *search key* from any decorated value (strip extraneous, all digit-runs + leading-zero); the **stored value is never stripped** (REQ-09 governs the value, not the key) | owner; REQ-09 reworded |
| V-D3 | Match confirmation | Number hit accepted **only if the board company name corresponds**; name fallback otherwise | owner; the 41/374 wrong-company finding |
| V-D4 | Correspondence signal | **Name only.** Address and all other signals rejected as imputation; honest unresolved beats a guessed match | owner decision 2026-06-13; REQ-09 |
| V-D5 | Retrofit | Fill blank / overwrite invalid / overwrite wrong-company into `general_contractor_license_number`; logged corrections; license master read-only | V5; REQ-09 |
| V-D6 | Thresholds | Name-correspondence bar **and** vocab/format UCLs pinned at the checkpoint on the **live re-run** profile; earlier numbers provisional | checkpoint; V4/V7 |
| V-D7 | Report | Values-free counts/percentages + verdict; PII to the gitignored audit zone | V11; §2.2 |

## 10. Gate checklist (mirrors §8.3, adapted)

1. Dated terms/robots note on file (D3 tier 1 — already recorded at slice-2 entry); live re-run politeness honored.
2. Verbatim raw frozen (fragments + decoded JSON + checksum manifest), re-parsable offline; new vintage.
3. Number extraction exercised (decorated → digit-runs); the stored eVP value is byte-unchanged by the search.
4. Number hit accepted only with name correspondence; a wrong-company fixture routes to the name search; an unrelated name lands unresolved.
5. Retrofit: blank fills, malformed overwrites, wrong-company overwrites, matching-digit no-ops — each a logged `Correction`; the license-master file is byte-unchanged after the run.
6. Conservation: cleaning identity **and** `matched + unresolved == total` both asserted.
7. Metric reports match rate %, buckets, fix counts (incl. wrong-company), trend.
8. Tally gates each rule against `VALIDATION_THRESHOLDS` (re-derived on this run); over-threshold fails.
9. Gate: a clean run PROMOTES; a low (non-zero) rate still promotes (reported); near-zero halts. **V10** poisoned fixture HALTS red **before any corrected master is written**.
10. Report values-free; PII detail only in the gitignored audit zone.
11. CI green throughout (offline fixtures + mock transport); the live re-run is opt-in, never in CI.
12. Golden re-baseline captured outside the repository (machine-local), as in slices 1/2.

## 11. Test surface (set test-first)

`tests/test_validation.py` carries the V1–V11 acceptance tests named in `requirements-validation.md`. The pure matcher gets its own tests (`extract_numbers` on decorated values; `corresponds` accepts spacing/suffix/`T-A` variants and rejects unrelated names; **address is never consulted**). The resolution policy is tested offline against a mock transport routing by search body (number-corresponds / number-wrong-company→name / name-only / unresolved). The threshold constant gets a test asserting it matches the checkpoint values once pinned.
