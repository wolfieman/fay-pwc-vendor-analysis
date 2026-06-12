"""Canonical VendorScope database schema (SQLite + sqlite-vec).

ONE SQLite file holds the normalized relational core *and* the embedding
vectors. The DDL is kept here as a module-level constant (rather than a
``.sql`` package-data file) so the wheel keeps shipping only
``src/vendorscope`` with no data-file plumbing.

Design summary (full rationale in ``docs/database-schema.md``):

* STRICT tables everywhere; ``PRAGMA foreign_keys = ON``; controlled
  vocabularies enforced as inline ``CHECK`` constraints (write-time
  rejection, not lookup-only).
* Blank / empty / NULL means "missing / unevaluated" and is ALWAYS
  permitted -- every vocab/format CHECK has the form
  ``(col IS NULL OR col = '' OR col IN (...) | col GLOB ...)`` because the
  cleaned data stores missing cells as ``''`` (empty string), and the bare
  ``col IN (...)`` form rejects ``''`` under STRICT.
* All identifiers, ZIP codes, and dates are TEXT (leading zeros + format
  preserved; dates MM/DD/YYYY, enforced by a blank-tolerant GLOB).
* PII is physically quarantined into ``*_pii`` sibling tables, so the
  public / sample export is "every table except the ``*_pii`` tables" by
  construction -- omission is structural, not a filter you can forget.
* Provenance spine: ``acquisition_run`` is an append-only run envelope and
  every fact row carries ``acquisition_run_id``, which makes the P2.4
  run-over-run diff computable without a schema change (SCD mechanism (b):
  current-state core now, append-only ``*_snapshot`` history added later).
* ``vendor_embedding`` is a ``sqlite-vec`` ``vec0`` virtual table created
  now and populated at P2.3; its dimension is a documented placeholder.

Copyright © 2026 Wolfgang Sanyer
Licensed under the Polyform Noncommercial License 1.0.0 (see LICENSE).
"""

import sqlite3

# The embedding width is finalized at P2.3 against the chosen model; vec0
# fixes a column's dimension at CREATE, so the table is DROP/CREATEd then
# (acceptable and additive because it is unpopulated until P2.3).
EMBED_DIM = 768

SCHEMA_SQL = f"""
PRAGMA foreign_keys = ON;

-- ===========================================================================
-- PROVENANCE SPINE
-- ===========================================================================

-- The two public data sources. Exactly two rows (seeded below).
CREATE TABLE source (
    source_id   TEXT NOT NULL PRIMARY KEY,    -- stable slug: 'evp', 'nclbgc'
    name        TEXT NOT NULL,
    url         TEXT NOT NULL,
    CHECK (source_id IN ('evp', 'nclbgc'))
) STRICT;

-- Full run envelope, append-only: one row per scrape/refresh of one source.
-- Every fact row carries acquisition_run_id, so the whole database is
-- sliceable by run and the P2.4 run-over-run diff needs NO schema change.
-- Metadata columns are NOT NULL so provenance can never be partially recorded.
CREATE TABLE acquisition_run (
    run_id           INTEGER NOT NULL PRIMARY KEY,  -- surrogate; monotonic run ordinal
    source_id        TEXT    NOT NULL,
    captured_at      TEXT    NOT NULL,              -- ISO-8601 capture timestamp (TEXT)
    snapshot_tag     TEXT    NOT NULL,              -- the v## tag, e.g. 'v07'
    source_checksum  TEXT    NOT NULL,              -- digest of the raw snapshot
    engine_version   TEXT    NOT NULL,              -- cleaning-engine version
    config_version   TEXT    NOT NULL,              -- TableConfig / vocab version
    row_count        INTEGER NOT NULL,              -- rows ingested this run
    FOREIGN KEY (source_id) REFERENCES source (source_id),
    UNIQUE (source_id, snapshot_tag),
    CHECK (snapshot_tag GLOB 'v[0-9]*'),
    CHECK (row_count >= 0)
) STRICT;

-- ===========================================================================
-- NCLBGC LICENSE REGISTER  (loaded first; vendor.license_number references it)
-- ===========================================================================

-- License core (current state). PK = natural license_number (TEXT). ~294 rows.
CREATE TABLE license (
    license_number       TEXT    NOT NULL PRIMARY KEY,
    acquisition_run_id   INTEGER NOT NULL,
    company_name         TEXT,
    address              TEXT,
    issue_date           TEXT,   -- MM/DD/YYYY (TEXT)
    expiration_date      TEXT,   -- MM/DD/YYYY (TEXT)
    status               TEXT,
    license_limitation   TEXT,
    FOREIGN KEY (acquisition_run_id) REFERENCES acquisition_run (run_id),
    -- Vocab reconciled to the REAL cleaned snapshot: 'Archived' and 'Invalid'
    -- are present in the data and MUST be permitted. Reconcile config.py
    -- LICENSE_CONFIG to match (P2.2b).
    CHECK (status IS NULL OR status = '' OR status IN
        ('Active', 'Expired', 'Suspended', 'Revoked', 'Inactive', 'Pending',
         'Archived', 'Invalid')),
    CHECK (license_limitation IS NULL OR license_limitation = '' OR license_limitation IN
        ('Limited', 'Intermediate', 'Unlimited')),
    CHECK (issue_date IS NULL OR issue_date = '' OR issue_date GLOB
        '[0-9][0-9]/[0-9][0-9]/[0-9][0-9][0-9][0-9]'),
    CHECK (expiration_date IS NULL OR expiration_date = '' OR expiration_date GLOB
        '[0-9][0-9]/[0-9][0-9]/[0-9][0-9][0-9][0-9]')
) STRICT;

-- PII sibling for license. 1:1 with license; holds ONLY the licensed-business
-- phone. Dropping this table yields a PII-free license register.
CREATE TABLE license_pii (
    license_number   TEXT NOT NULL PRIMARY KEY,
    phone            TEXT,   -- ###-###-#### ; PII
    FOREIGN KEY (license_number) REFERENCES license (license_number) ON DELETE CASCADE
) STRICT;

-- Qualifier: CHILD of license (one license -> MANY qualifiers; NOT 1:1).
-- Surrogate PK because a qualifier number is not globally unique on its own.
-- A defensive UNIQUE(license_number, qualifier_number) catches accidental
-- double-loads of the same qualifier within a license; it does NOT block P2.4
-- history (history lives in a side-car qualifier_snapshot table, not here).
-- Verified against real data: every qualifier number maps to exactly one
-- license, so a qualifier dimension/bridge would add a join with no dedup
-- benefit -- the child table is the correct model.
CREATE TABLE qualifier (
    qualifier_id         INTEGER NOT NULL PRIMARY KEY,  -- surrogate
    license_number       TEXT    NOT NULL,
    acquisition_run_id   INTEGER NOT NULL,
    qualifier_number     TEXT,                          -- business id; TEXT
    qualifier_status     TEXT,
    FOREIGN KEY (license_number) REFERENCES license (license_number) ON DELETE CASCADE,
    FOREIGN KEY (acquisition_run_id) REFERENCES acquisition_run (run_id),
    UNIQUE (license_number, qualifier_number),
    -- 'Expired' kept per the engine SSOT (LICENSE_CONFIG.vocabularies); the
    -- loader splits '; '-joined cells and scrubs the 'Status' header-leak
    -- artifact BEFORE insert, so each row carries one clean value.
    CHECK (qualifier_status IS NULL OR qualifier_status = '' OR qualifier_status IN
        ('Active', 'Inactive', 'Expired'))
) STRICT;

-- PII sibling for qualifier. 1:1 with qualifier; holds ONLY the individual's name.
CREATE TABLE qualifier_pii (
    qualifier_id     INTEGER NOT NULL PRIMARY KEY,
    qualifier_name   TEXT,   -- PII (an individual)
    FOREIGN KEY (qualifier_id) REFERENCES qualifier (qualifier_id) ON DELETE CASCADE
) STRICT;

-- Classification lookup (resolves the semicolon-delimited license.classifications).
CREATE TABLE classification (
    classification_id   INTEGER NOT NULL PRIMARY KEY,
    name                TEXT    NOT NULL,   -- e.g. 'Building', 'Highway', 'PU(Water Lines & Sewer Lines)'
    UNIQUE (name)
) STRICT;

-- M:N bridge: which classifications a license holds. Run-stamped for per-run diff.
CREATE TABLE license_classification (
    license_number       TEXT    NOT NULL,
    classification_id    INTEGER NOT NULL,
    acquisition_run_id   INTEGER NOT NULL,
    PRIMARY KEY (license_number, classification_id),
    FOREIGN KEY (license_number) REFERENCES license (license_number) ON DELETE CASCADE,
    FOREIGN KEY (classification_id) REFERENCES classification (classification_id),
    FOREIGN KEY (acquisition_run_id) REFERENCES acquisition_run (run_id)
) STRICT;

-- ===========================================================================
-- eVP VENDOR MASTER
-- ===========================================================================

-- Vendor core (current state). SURROGATE vendor_id PK so license_number can be
-- a NULLABLE FK rather than a NOT-NULL composite-PK column: under STRICT every
-- PK column is implicitly NOT NULL, so a natural composite PK (vendor_name,
-- license_number) would HARD-REJECT a license-less vendor. The surrogate fixes
-- that and shrinks every child FK to a single integer. The documented dedup
-- identity is preserved as UNIQUE(vendor_name, license_number). ~295 rows.
CREATE TABLE vendor (
    vendor_id            INTEGER NOT NULL PRIMARY KEY,  -- surrogate
    acquisition_run_id   INTEGER NOT NULL,
    vendor_name          TEXT    NOT NULL,
    license_number       TEXT,   -- primary GC license; FK -> license; NULL/'' = missing
    address              TEXT,
    city                 TEXT,
    state                TEXT,
    zip_code             TEXT,   -- TEXT; leading zeros preserved
    county               TEXT,
    country              TEXT,
    url                  TEXT,
    evp_status           TEXT,
    nc_eprocurement      TEXT,
    pwc_active           TEXT,   -- PWC-derived/client flag (NOT eVP source); Yes/No
    small_business       TEXT,   -- Yes/No
    dbe                  TEXT,   -- Yes/No
    npwc                 TEXT,   -- internal PWC vendor classification (open TEXT, no closed vocab)
    UNIQUE (vendor_name, license_number),
    FOREIGN KEY (acquisition_run_id) REFERENCES acquisition_run (run_id),
    FOREIGN KEY (license_number) REFERENCES license (license_number),
    CHECK (evp_status IS NULL OR evp_status = '' OR evp_status IN
        ('Active', 'Pending', 'Debarred')),
    CHECK (nc_eprocurement IS NULL OR nc_eprocurement = '' OR nc_eprocurement IN
        ('Active', 'Inactive', 'Not Applicable')),
    CHECK (pwc_active     IS NULL OR pwc_active     = '' OR pwc_active     IN ('Yes', 'No')),
    CHECK (small_business IS NULL OR small_business = '' OR small_business IN ('Yes', 'No')),
    CHECK (dbe            IS NULL OR dbe            = '' OR dbe            IN ('Yes', 'No'))
    -- npwc intentionally has NO CHECK: the source defines it only as an
    -- 'internal PWC vendor classification' with no enumerated vocabulary.
) STRICT;

-- PII sibling for vendor. 1:1 with vendor; holds the three eVP contact PII columns.
CREATE TABLE vendor_pii (
    vendor_id        INTEGER NOT NULL PRIMARY KEY,
    contact_name     TEXT,   -- PII
    contact_email    TEXT,   -- PII (lowercased)
    contact_phone    TEXT,   -- PII (###-###-####)
    FOREIGN KEY (vendor_id) REFERENCES vendor (vendor_id) ON DELETE CASCADE
) STRICT;

-- Vendor trades: collapses eVP's SEVEN heterogeneous per-trade blocks into one
-- row per trade. trade_kind is the discriminator over a closed 7-value vocab.
-- Each per-trade attribute lives in a NULLable column gated by a TWO-SIDED
-- guard (only the owning trade_kind may populate it AND any off-type trade must
-- leave it NULL/''), so cross-trade attribute leakage is rejected at write
-- time. trade_license_number is physically barred on the two flag-only trades.
--
-- `held` (the Yes/No participation value mapped from the source 0/1 flag) is
-- stored explicitly so the rare rows where a trade flag = '0' yet attributes
-- are present (verified: 4 such rows) round-trip exactly: row PRESENCE alone
-- cannot distinguish '0' from 'missing'. The loader creates a row when `held`
-- is non-blank OR any attribute is non-blank.
CREATE TABLE vendor_trade (
    vendor_trade_id        INTEGER NOT NULL PRIMARY KEY,  -- surrogate
    vendor_id              INTEGER NOT NULL,
    acquisition_run_id     INTEGER NOT NULL,
    trade_kind             TEXT    NOT NULL,
    held                   TEXT,                          -- Yes/No participation flag value
    trade_license_number   TEXT,                          -- business id; absent for arch/eng
    limitation             TEXT,                          -- GC only
    work_classification    TEXT,                          -- GC only (free text)
    level                  TEXT,                          -- electrical only
    specialties            TEXT,                          -- electrical only (free text)
    classifications        TEXT,                          -- plumbing/mechanical (free text)
    UNIQUE (vendor_id, trade_kind),
    FOREIGN KEY (vendor_id) REFERENCES vendor (vendor_id) ON DELETE CASCADE,
    FOREIGN KEY (acquisition_run_id) REFERENCES acquisition_run (run_id),
    CHECK (trade_kind IN (
        'general_contractor',
        'electrical',
        'plumbing_fire_sprinkler',
        'mechanical_heating',
        'trades_sub_contractor',
        'architectural_services',
        'engineering_services')),
    CHECK (held IS NULL OR held = '' OR held IN ('Yes', 'No')),
    -- vocab guards on the typed per-trade attributes (blank-tolerant):
    CHECK (limitation IS NULL OR limitation = '' OR limitation IN
        ('Unlimited', 'Limited', 'Intermediate', 'None')),
    CHECK (level IS NULL OR level = '' OR level IN
        ('Unlimited', 'Limited', 'Intermediate')),
    -- heterogeneity guards (TWO-SIDED): an attribute may be non-blank only for
    -- its owning trade_kind; otherwise it must be NULL or ''.
    CHECK (limitation IS NULL OR limitation = '' OR trade_kind = 'general_contractor'),
    CHECK (work_classification IS NULL OR work_classification = '' OR trade_kind = 'general_contractor'),
    CHECK (level IS NULL OR level = '' OR trade_kind = 'electrical'),
    CHECK (specialties IS NULL OR specialties = '' OR trade_kind = 'electrical'),
    CHECK (classifications IS NULL OR classifications = '' OR trade_kind IN
        ('plumbing_fire_sprinkler', 'mechanical_heating')),
    -- architectural/engineering services are flag-only: no license number.
    CHECK (trade_license_number IS NULL OR trade_license_number = '' OR trade_kind NOT IN
        ('architectural_services', 'engineering_services'))
) STRICT;

-- Vendor certifications: HUB + NCSBE programs, one row per program a vendor
-- carries. Collapses the parallel HUB_*/NCSBE_* column blocks into one table
-- keyed by program (the discriminator). category is HUB-only, guarded TWO-SIDED.
CREATE TABLE vendor_certification (
    vendor_certification_id   INTEGER NOT NULL PRIMARY KEY,  -- surrogate
    vendor_id                 INTEGER NOT NULL,
    acquisition_run_id        INTEGER NOT NULL,
    program                   TEXT    NOT NULL,   -- 'HUB' | 'NCSBE'
    status                    TEXT,               -- Certified / Not Certified
    category                  TEXT,               -- HUB demographic category (NCSBE: NULL/'')
    start_date                TEXT,               -- MM/DD/YYYY
    end_date                  TEXT,               -- MM/DD/YYYY
    active                    TEXT,               -- Yes/No
    UNIQUE (vendor_id, program),
    FOREIGN KEY (vendor_id) REFERENCES vendor (vendor_id) ON DELETE CASCADE,
    FOREIGN KEY (acquisition_run_id) REFERENCES acquisition_run (run_id),
    CHECK (program IN ('HUB', 'NCSBE')),
    CHECK (status IS NULL OR status = '' OR status IN ('Certified', 'Not Certified')),
    CHECK (active IS NULL OR active = '' OR active IN ('Yes', 'No')),
    -- HUB category vocab reconciled to the REAL data: the snapshot carries
    -- 'Asian American' (NOT 'Asian'); omitting it rejects a real row.
    CHECK (category IS NULL OR category = '' OR category IN (
        'American Indian', 'Asian American', 'Black', 'Disabled', 'Female',
        'Hispanic', 'Socially and Economically Disadvantaged')),
    -- TWO-SIDED category guard: only HUB may carry a category; NCSBE must leave
    -- it blank. (Empty-string-safe both ways.)
    CHECK ((program = 'HUB' AND (category IS NULL OR category = '' OR category IN (
                'American Indian', 'Asian American', 'Black', 'Disabled', 'Female',
                'Hispanic', 'Socially and Economically Disadvantaged')))
           OR (program <> 'HUB' AND (category IS NULL OR category = ''))),
    CHECK (start_date IS NULL OR start_date = '' OR start_date GLOB
        '[0-9][0-9]/[0-9][0-9]/[0-9][0-9][0-9][0-9]'),
    CHECK (end_date IS NULL OR end_date = '' OR end_date GLOB
        '[0-9][0-9]/[0-9][0-9]/[0-9][0-9][0-9][0-9]')
) STRICT;

-- ===========================================================================
-- HELPER INDEXES (FK / current-state lookup hot paths; PK & UNIQUE auto-index)
-- ===========================================================================
CREATE INDEX idx_license_run                  ON license (acquisition_run_id);
CREATE INDEX idx_vendor_run                   ON vendor (acquisition_run_id);
CREATE INDEX idx_vendor_license_number        ON vendor (license_number);
CREATE INDEX idx_qualifier_license            ON qualifier (license_number);
CREATE INDEX idx_license_classification_class ON license_classification (classification_id);
CREATE INDEX idx_vendor_trade_vendor          ON vendor_trade (vendor_id);
CREATE INDEX idx_vendor_cert_vendor           ON vendor_certification (vendor_id);

-- ===========================================================================
-- EMBEDDINGS  (sqlite-vec vec0 virtual table)
-- ===========================================================================
-- Created NOW, populated at P2.3. vendor_id is the vec0 PRIMARY KEY (maps each
-- vector 1:1 back to a vendor with no join table); run_id is a PARTITION KEY so
-- embeddings are sliceable/droppable per acquisition run (cheap additive
-- refresh). The dimension ({EMBED_DIM}) is a documented placeholder; vec0 fixes
-- it at CREATE, so P2.3 DROP/CREATEs this (unpopulated) table with the chosen
-- width -- the one expected non-additive step, by design, on an empty table.
CREATE VIRTUAL TABLE vendor_embedding USING vec0 (
    vendor_id INTEGER PRIMARY KEY,
    run_id INTEGER PARTITION KEY,
    embedding FLOAT[{EMBED_DIM}]
);

-- ===========================================================================
-- SEED: the two fixed sources (self-bootstrapping; FK-satisfiable at create)
-- ===========================================================================
INSERT INTO source (source_id, name, url) VALUES
    ('evp',    'NC electronic Vendor Portal',                'https://evp.nc.gov'),
    ('nclbgc', 'NC Licensing Board for General Contractors', 'https://nclbgc.org');

-- ===========================================================================
-- PARITY RE-FLATTEN VIEW
-- ===========================================================================
-- The cleaned NCLBGC CSV is FLATTENED to one-row-per-license with a '; '-joined
-- qualifier list, so it has 295 rows over 294 distinct licenses (license 83622
-- carries 2 qualifiers). This schema normalizes that into license (294) +
-- qualifier (295). The parity gate compares the cleaned CSV against THIS view,
-- which re-collapses qualifier child rows back onto each license to reproduce
-- the source cell exactly. PII columns (phone, qualifier_name) are omitted: the
-- public/sample parity target is PII-free.
CREATE VIEW v_license_flat AS
SELECT
    l.license_number,
    l.company_name,
    l.address,
    l.issue_date,
    l.expiration_date,
    l.status,
    l.license_limitation,
    (SELECT group_concat(c.name, '; ')
       FROM license_classification lc
       JOIN classification c ON c.classification_id = lc.classification_id
      WHERE lc.license_number = l.license_number)            AS classifications,
    (SELECT group_concat(q.qualifier_number, '; ')
       FROM qualifier q WHERE q.license_number = l.license_number) AS qualifier_number,
    (SELECT group_concat(q.qualifier_status, '; ')
       FROM qualifier q WHERE q.license_number = l.license_number) AS qualifier_status
FROM license l;
"""


def create_schema(conn: sqlite3.Connection) -> None:
    """Apply the full schema (tables, indexes, vec0 table, seed, view) to ``conn``.

    The connection must already have the ``sqlite-vec`` extension loaded (see
    :func:`vendorscope.db.connect`) so the ``vendor_embedding`` ``vec0`` virtual
    table can be created.
    """
    conn.executescript(SCHEMA_SQL)
    conn.execute("PRAGMA foreign_keys = ON")
