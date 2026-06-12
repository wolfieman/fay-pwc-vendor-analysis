# Database Schema

> **Status (2026-06-12):** design reference for the future database slice. The
> implementation this document described was retired in the greenfield reset;
> the design below is carried-forward knowledge, to be re-authored fresh when
> the database slice opens (see [project-plan.md](project-plan.md)).

VendorScope's planned database is a **single SQLite file** holding the normalized
relational tables *and* the embedding vectors (via the
[`sqlite-vec`](https://github.com/asg017/sqlite-vec) `vec0` extension). Clone and
run; there is no service to host. The canonical DDL will be authored in the
database slice; this document is the design reference.

## Entity-relationship diagram

```mermaid
erDiagram
    source ||--o{ acquisition_run : "scraped in"
    acquisition_run ||--o{ license : stamps
    acquisition_run ||--o{ vendor : stamps
    acquisition_run ||--o{ qualifier : stamps
    acquisition_run ||--o{ vendor_trade : stamps
    acquisition_run ||--o{ vendor_certification : stamps
    acquisition_run ||--o{ license_classification : stamps

    license ||--|| license_pii : "PII split"
    license ||--o{ qualifier : "has"
    qualifier ||--|| qualifier_pii : "PII split"
    license ||--o{ license_classification : ""
    classification ||--o{ license_classification : ""
    license |o--o{ vendor : "GC license of"

    vendor ||--|| vendor_pii : "PII split"
    vendor ||--o{ vendor_trade : "holds"
    vendor ||--o{ vendor_certification : "carries"
    vendor ||--o| vendor_embedding : "vector (P2.3)"

    source {
        TEXT source_id PK
        TEXT name
        TEXT url
    }
    acquisition_run {
        INTEGER run_id PK
        TEXT source_id FK
        TEXT captured_at
        TEXT snapshot_tag
        TEXT source_checksum
        TEXT engine_version
        TEXT config_version
        INTEGER row_count
    }
    license {
        TEXT license_number PK
        INTEGER acquisition_run_id FK
        TEXT company_name
        TEXT status
        TEXT license_limitation
        TEXT issue_date
        TEXT expiration_date
    }
    license_pii {
        TEXT license_number PK_FK
        TEXT phone "PII"
    }
    qualifier {
        INTEGER qualifier_id PK
        TEXT license_number FK
        TEXT qualifier_number
        TEXT qualifier_status
    }
    qualifier_pii {
        INTEGER qualifier_id PK_FK
        TEXT qualifier_name "PII"
    }
    classification {
        INTEGER classification_id PK
        TEXT name
    }
    license_classification {
        TEXT license_number PK_FK
        INTEGER classification_id PK_FK
    }
    vendor {
        INTEGER vendor_id PK
        TEXT vendor_name
        TEXT license_number FK
        TEXT evp_status
        TEXT nc_eprocurement
        TEXT small_business
        TEXT dbe
        TEXT npwc
    }
    vendor_pii {
        INTEGER vendor_id PK_FK
        TEXT contact_name "PII"
        TEXT contact_email "PII"
        TEXT contact_phone "PII"
    }
    vendor_trade {
        INTEGER vendor_trade_id PK
        INTEGER vendor_id FK
        TEXT trade_kind
        TEXT held
        TEXT trade_license_number
        TEXT limitation
        TEXT level
    }
    vendor_certification {
        INTEGER vendor_certification_id PK
        INTEGER vendor_id FK
        TEXT program
        TEXT status
        TEXT category
    }
    vendor_embedding {
        INTEGER vendor_id PK
        INTEGER run_id
        FLOAT embedding "vec0 FLOAT[768]"
    }
```

## Tables

| Group | Table | Grain / purpose |
|---|---|---|
| Provenance | `source` | The two public sources (NC eVP, NCLBGC); seeded. |
| Provenance | `acquisition_run` | One row per scrape/refresh; append-only run envelope stamped on every fact row. |
| License | `license` | NCLBGC license details, one row per license (natural PK `license_number`). |
| License | `license_pii` | PII sibling of `license` (business phone only). |
| License | `qualifier` | Licensed individuals; **child of license** (one license -> many qualifiers). |
| License | `qualifier_pii` | PII sibling of `qualifier` (the individual's name). |
| License | `classification` / `license_classification` | Classification lookup + many-to-many bridge (resolves the semicolon-delimited field). |
| Vendor | `vendor` | eVP business master (surrogate `vendor_id`; `UNIQUE(vendor_name, license_number)` dedup identity). |
| Vendor | `vendor_pii` | PII sibling of `vendor` (contact name/email/phone). |
| Vendor | `vendor_trade` | One row per held trade; collapses the seven heterogeneous eVP per-trade blocks. |
| Vendor | `vendor_certification` | HUB + NCSBE programs, one row per program. |
| AI | `vendor_embedding` | `sqlite-vec` `vec0` virtual table; created now, populated at P2.3. |
| Parity | `v_license_flat` (view) | Re-collapses qualifier child rows to reproduce the flat source CSV 1:1. |

## Design decisions

- **STRICT tables + `PRAGMA foreign_keys = ON` + `CHECK` vocabularies.** Controlled
  vocabularies are enforced at write time, not merely documented. Blank/empty/NULL
  always means "missing / unevaluated" and is permitted everywhere (never imputed),
  so every vocab CHECK is blank-tolerant: `col IS NULL OR col = '' OR col IN (...)`.
- **Everything as TEXT.** Identifiers, ZIP codes, and dates are TEXT so leading zeros
  and `MM/DD/YYYY` format survive (dates are format-checked by a blank-tolerant GLOB).
- **PII airtight by construction.** All five PII fields live only in `*_pii` sibling
  tables, so the public / `sample/` export is "every table except the `*_pii` tables",
  a structural guarantee rather than a filter that can be forgotten.
- **Provenance spine.** `acquisition_run` records when/what/which-version produced each
  load, and every fact row carries `acquisition_run_id`, which makes the run-over-run
  diff (P2.4) computable without a schema change.
- **Surrogate `vendor_id`.** Under STRICT every primary-key column is implicitly
  `NOT NULL`, so a natural composite PK `(vendor_name, license_number)` would reject a
  license-less vendor. A surrogate PK fixes that; the documented dedup identity is kept
  as a `UNIQUE` constraint.
- **Discriminated `vendor_trade`.** The seven trade blocks have heterogeneous attributes
  (GC has a limitation, electrical has a level, etc.). One table with a `trade_kind`
  discriminator and two-sided CHECK guards rejects cross-trade attribute leakage, while
  a `held` column preserves the Yes/No participation value so the data round-trips.
- **SCD mechanism (b): append-only snapshots.** Core tables are current-state now;
  Phase 2.4 adds history as append-only `*_snapshot` tables alongside them (a pure
  `ADD TABLE`), never altering a key here.
- **`vendor_embedding` (vec0).** `vendor_id` is the primary key (1:1 back to a vendor);
  `run_id` is a partition key so embeddings are sliceable/droppable per run. The
  dimension (768) is a placeholder finalized at P2.3 against the chosen model.

## Standardization & loader contract (Phase 2.2b)

Raw source field names are irrelevant here; the database is the **standardized,
snake_case processed schema**. The loader maps cleaned frames onto it and:

- maps boolean flags `0/1 -> No/Yes` (canonical flag vocab is `Yes`/`No`);
- splits the `'; '`-packed qualifier cells into one `qualifier` row each, scrubbing the
  `'Status'` header-bleed artifact and normalizing the one legitimately duplicated
  license into one license row plus its qualifiers;
- reconciles the cleaning config vocabularies to the real data (license `status` gains
  `Invalid`/`Archived`; HUB category `Asian` -> `Asian American`).

Parity is verified against `v_license_flat` (the re-collapsed view), since the schema
normalizes the 295-row flattened CSV into `license` (294) + `qualifier` (295).
