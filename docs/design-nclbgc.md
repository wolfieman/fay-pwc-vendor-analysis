# Slice 2 Design: the NCLBGC pipeline

**Status:** design phase (solo; no section 2.4 panel trigger) · **Last updated:** 2026-06-12

This is the design-of-record for slice 2 and doubles as the mid-slice owner
checkpoint: module seams, stage hand-offs, the two-table data model, and the
decisions a reviewer should confirm before the test-first build. It builds on the
analysis spike (the fragment shapes are frozen and fixtured) and the entry-check
requirements R1–R9 on the slice card. Vocabularies and shapes are observed, not
assumed.

## 1. Module manifest

New modules (NCLBGC-specific) and the slice-1 core they reuse unchanged.

| Module | Responsibility | Stratum |
|---|---|---|
| `nclbgc_client.py` | acquire shell: prime a session, POST the search per license number, GET the three fragments per opaque key; politeness delay; raw written before any check; resolve-or-flag per license | boundary IO |
| `nclbgc_parse.py` | pure: stdlib `html.parser`. Search fragment to opaque key(s); detail fragment to one license record (label/field pairs); qualifiers fragment to zero-or-more child rows, scrubbing the `Status` header-bleed row | pure |
| `cleaning/config.py` (extend) | add `LICENSE_CONFIG` and `QUALIFIER_CONFIG` (snake_case targets; license status vocabulary including `Invalid`/`Archived`; limitation Unlimited/Limited/Intermediate); their own `EXPECTED_COLUMNS` manifests | pure |
| `cli.py` (extend) | add `acquire-nclbgc` (drive from slice-1 license numbers) and `enrich`/`clean-nclbgc` subcommands | shell |

Reused unchanged: `http_client`, `tabular` (text-mode IO, manifest check, snake_case rename, PII split), `cleaning/engine` (role dispatch, report-don't-coerce, conservation), `cleaning/transforms`, `cleaning/records`, `profiling`, `paths`.

## 2. Data model and stage hand-offs

The board lookup is one-to-one for the license and one-to-many for qualifiers, so
the slice produces **two tables**, not one:

- **`license`** — one row per resolved license number (the detail fragment).
- **`qualifier`** — zero-or-more rows per license (the qualifiers fragment); a
  child table carrying the license number as its parent reference.

Stage hand-offs (each immutable, like slice 1):

1. **Acquire** (`nclbgc_client`): for each slice-1 general-contractor license
   number, prime to search to per-key fragments; freeze the raw fragments under
   `data/raw/nclbgc/<run-id>/`. A license that returns no row is recorded as a
   **flagged unresolved record**, never silently dropped (gate: resolve every
   slice-1 number or flag it).
2. **Parse** (`nclbgc_parse`, pure): search to key; detail to one license record;
   qualifiers to a list of child rows. All values stringified, text mode.
3. **Clean** (`cleaning/engine`, reused): the license table through
   `LICENSE_CONFIG`, the qualifier table through `QUALIFIER_CONFIG`; report-don't-
   coerce; per-table `row_key`; conservation per table.
4. **Standardize/split** (`tabular`, reused): snake_case at processed-write; PII
   split per table — `Phone` from the license, `Qualifier_Name` from the qualifier.

## 3. Seams (pure core vs IO shell)

- **Pure:** `nclbgc_parse` (key extraction, detail label/field parse, qualifier
  table parse with the header-bleed scrub), the two configs, the cleaning engine.
  All tested offline against the committed fixtures.
- **IO shell:** `nclbgc_client` (HTTP, the only network code; injectable transport
  for offline contract tests), `tabular` (disk), `cli`.

## 4. Decisions to confirm (slice-2 design)

| # | Decision | Proposed ruling |
|---|---|---|
| N1 | Output cardinality | Two tables: `license` (1:1) and `qualifier` (1:N child). Each gets its own manifest, `row_key`, conservation identity, and PII split. |
| N2 | Unresolved license numbers | Two-pronged match: search by license number first; on no row, fall back to a company-name search (a name-matched but license-mismatched hit is flagged for review, not trusted blindly, because name matching is fuzzier). If neither resolves, record a flagged `unresolved` record (searched number, reason), counted in the run report; never silently dropped. Slice 2 only flags — the downstream validation/database slice excludes the unusable rows. |
| N3 | The `L.` prefix on the NCLBGC license number | NCLBGC displays the number with a uniform `L.` type-sigil (for example `L.68764`) carrying no discriminating information in our GC-only context, while eVP and our search use the digits (`68764`). **Strip the `L.` prefix at processed-write** to recover the bare account number, logged as an audited correction; the raw capture keeps it verbatim. This scopes REQ-09's "never prefix-strip" to *meaningful* prefixes (out-of-state, multi-license) which still surface as violations; the uniform sigil is normalization, not silent coercion. The digit form is the join key back to eVP. |
| N4 | Parser dependency | Stdlib `html.parser` only (D6). Revisit only if the markup demonstrably defeats it, recorded as a fresh decision. |
| N5 | Qualifier identity | `row_key` is the qualifier's ordinal within its parent license's fragment; the parent reference is the license number. A qualifier never spans more than one license (confirmed prior; revisit only on a counter-example). |
| N6 | Politeness | One license at a time with a fixed delay; the live run is opt-in and never in CI. |

## 5. Test surface (set in the test-first phase)

Pure parser tests against the six committed fixtures: search to key; the empty
search yields no key (the flag path); detail to a license record with the `L.`
prefix preserved; qualifiers to two child rows; the quirk fixture drops the
`Status` header-bleed row and yields the multi-qualifier rows. Config-vs-fixture
agreement, conservation per table, idempotency, and the manifest hard check reuse
the slice-1 patterns. A `docs/requirements-nclbgc.md` register binds R1–R9 to
these tests at the start of the build, mirroring slice 1.
