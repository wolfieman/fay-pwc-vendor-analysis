"""Schema constraint tests for the VendorScope SQLite + sqlite-vec database.

These prove the schema's guarantees actually bite on this machine's SQLite:
the controlled-vocabulary ``CHECK`` constraints, foreign-key enforcement,
``STRICT`` typing, the two-sided trade/certification guards, the ``vec0``
embedding table, and the parity re-flatten view. Accept-cases use the real
distinct values found in the cleaned snapshot (e.g. ``status = 'Archived'``,
``hub_category = 'Asian American'``) so a vocab that drifts from the data is
caught here, not at load time.

Copyright © 2026 Wolfgang Sanyer
Licensed under the Polyform Noncommercial License 1.0.0 (see LICENSE).
"""

import sqlite3
import struct
from collections.abc import Iterator

import pytest

from vendorscope.db import EMBED_DIM, build

pytestmark = pytest.mark.unit


@pytest.fixture
def conn() -> Iterator[sqlite3.Connection]:
    """An in-memory database with the full schema applied."""
    c = build(":memory:")
    yield c
    c.close()


@pytest.fixture
def seeded(conn: sqlite3.Connection) -> sqlite3.Connection:
    """Schema plus a license run, an eVP run, one license, and one vendor.

    Gives FK parents for the per-table constraint tests.
    """
    conn.execute(
        "INSERT INTO acquisition_run VALUES (1,'nclbgc','2026-06-11T00:00:00Z','v07','c','1.0','1.0',294)"
    )
    conn.execute(
        "INSERT INTO acquisition_run VALUES (2,'evp','2026-06-11T00:00:00Z','v07','d','1.0','1.0',295)"
    )
    conn.execute(
        "INSERT INTO license(license_number,acquisition_run_id,status) VALUES ('L1',1,'Active')"
    )
    conn.execute(
        "INSERT INTO vendor(vendor_id,acquisition_run_id,vendor_name,license_number) "
        "VALUES (1,2,'Acme','L1')"
    )
    return conn


# --------------------------------------------------------------------------- #
# Structure
# --------------------------------------------------------------------------- #


def test_schema_applies_and_seeds_sources(conn: sqlite3.Connection) -> None:
    names = {
        r[0]
        for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type IN ('table','view')"
        )
    }
    expected = {
        "source",
        "acquisition_run",
        "license",
        "license_pii",
        "qualifier",
        "qualifier_pii",
        "classification",
        "license_classification",
        "vendor",
        "vendor_pii",
        "vendor_trade",
        "vendor_certification",
        "vendor_embedding",
        "v_license_flat",
    }
    assert expected <= names
    assert conn.execute("SELECT count(*) FROM source").fetchone()[0] == 2


def test_pii_isolated_to_sibling_tables(conn: sqlite3.Connection) -> None:
    """Every PII column lives only in a ``*_pii`` table, so the public export is
    'all tables except ``*_pii``' by construction."""
    pii_cols = {
        "contact_name",
        "contact_email",
        "contact_phone",
        "phone",
        "qualifier_name",
    }
    for table in (
        "vendor",
        "license",
        "qualifier",
        "vendor_trade",
        "vendor_certification",
    ):
        cols = {r[1] for r in conn.execute(f"PRAGMA table_info({table})")}
        assert not (cols & pii_cols), f"{table} leaks PII columns {cols & pii_cols}"
    for table, col in (
        ("vendor_pii", "contact_name"),
        ("license_pii", "phone"),
        ("qualifier_pii", "qualifier_name"),
    ):
        cols = {r[1] for r in conn.execute(f"PRAGMA table_info({table})")}
        assert col in cols


# --------------------------------------------------------------------------- #
# Vocabularies accept the real data (blank-tolerant)
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("status", ["Active", "Invalid", "Archived", ""])
def test_license_status_accepts_real_values(
    seeded: sqlite3.Connection, status: str
) -> None:
    seeded.execute(
        "INSERT INTO license(license_number,acquisition_run_id,status) VALUES (?,1,?)",
        (f"S-{status or 'blank'}", status),
    )


def test_certification_accepts_real_hub_category(seeded: sqlite3.Connection) -> None:
    # 'Asian American' is the real snapshot value (NOT 'Asian').
    seeded.execute(
        "INSERT INTO vendor_certification(vendor_certification_id,vendor_id,acquisition_run_id,"
        "program,status,category) VALUES (1,1,2,'HUB','Certified','Asian American')"
    )
    # NCSBE carries no category.
    seeded.execute(
        "INSERT INTO vendor_certification(vendor_certification_id,vendor_id,acquisition_run_id,"
        "program,status,category) VALUES (2,1,2,'NCSBE','Certified','')"
    )


def test_vendor_accepts_yes_no_and_blank_flags(seeded: sqlite3.Connection) -> None:
    seeded.execute(
        "INSERT INTO vendor(vendor_id,acquisition_run_id,vendor_name,license_number,"
        "small_business,dbe,pwc_active) VALUES (2,2,'Beta','L1','Yes','No','')"
    )


def test_vendor_allows_license_less_with_null_fk(seeded: sqlite3.Connection) -> None:
    """Surrogate PK lets a vendor with no primary license still insert."""
    seeded.execute(
        "INSERT INTO vendor(vendor_id,acquisition_run_id,vendor_name,license_number) "
        "VALUES (3,2,'NoLicense Co',NULL)"
    )


# --------------------------------------------------------------------------- #
# Guards reject bad data
# --------------------------------------------------------------------------- #


def test_check_rejects_out_of_vocab_status(seeded: sqlite3.Connection) -> None:
    with pytest.raises(sqlite3.IntegrityError):
        seeded.execute(
            "INSERT INTO license(license_number,acquisition_run_id,status) VALUES ('X',1,'Bogus')"
        )


def test_check_rejects_non_iso_us_date(seeded: sqlite3.Connection) -> None:
    with pytest.raises(sqlite3.IntegrityError):
        seeded.execute(
            "INSERT INTO license(license_number,acquisition_run_id,issue_date) "
            "VALUES ('X',1,'2020-01-02')"
        )


def test_check_rejects_zero_one_flag(seeded: sqlite3.Connection) -> None:
    """Raw 0/1 must be mapped to Yes/No by the loader; the schema rejects 0/1."""
    with pytest.raises(sqlite3.IntegrityError):
        seeded.execute(
            "INSERT INTO vendor(vendor_id,acquisition_run_id,vendor_name,small_business) "
            "VALUES (9,2,'Bad','0')"
        )


def test_check_rejects_bad_snapshot_tag(conn: sqlite3.Connection) -> None:
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO acquisition_run VALUES (5,'evp','t','x99','c','1','1',5)"
        )


def test_strict_rejects_text_in_integer_column(conn: sqlite3.Connection) -> None:
    """STRICT bites on INTEGER columns (row_count); text ids are TEXT by design."""
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO acquisition_run VALUES (6,'evp','t','v9','c','1','1','notanint')"
        )


def test_fk_rejects_orphan_vendor_license(seeded: sqlite3.Connection) -> None:
    with pytest.raises(sqlite3.IntegrityError):
        seeded.execute(
            "INSERT INTO vendor(vendor_id,acquisition_run_id,vendor_name,license_number) "
            "VALUES (9,2,'Ghost','NOPE')"
        )


def test_fk_rejects_orphan_qualifier(seeded: sqlite3.Connection) -> None:
    with pytest.raises(sqlite3.IntegrityError):
        seeded.execute(
            "INSERT INTO qualifier(qualifier_id,license_number,acquisition_run_id) "
            "VALUES (1,'NOPE',1)"
        )


def test_certification_category_two_sided_guard(seeded: sqlite3.Connection) -> None:
    # NCSBE may not carry a category...
    with pytest.raises(sqlite3.IntegrityError):
        seeded.execute(
            "INSERT INTO vendor_certification(vendor_certification_id,vendor_id,"
            "acquisition_run_id,program,category) VALUES (3,1,2,'NCSBE','Female')"
        )
    # ...and the stale 'Asian' value is rejected even on HUB.
    with pytest.raises(sqlite3.IntegrityError):
        seeded.execute(
            "INSERT INTO vendor_certification(vendor_certification_id,vendor_id,"
            "acquisition_run_id,program,category) VALUES (4,1,2,'HUB','Asian')"
        )


def test_vendor_trade_rejects_cross_trade_attribute(seeded: sqlite3.Connection) -> None:
    # 'limitation' is GC-only; an electrical row may not carry it.
    with pytest.raises(sqlite3.IntegrityError):
        seeded.execute(
            "INSERT INTO vendor_trade(vendor_trade_id,vendor_id,acquisition_run_id,"
            "trade_kind,limitation) VALUES (1,1,2,'electrical','Unlimited')"
        )


def test_vendor_trade_bars_license_on_flag_only_trade(
    seeded: sqlite3.Connection,
) -> None:
    with pytest.raises(sqlite3.IntegrityError):
        seeded.execute(
            "INSERT INTO vendor_trade(vendor_trade_id,vendor_id,acquisition_run_id,"
            "trade_kind,trade_license_number) VALUES (2,1,2,'engineering_services','999')"
        )


def test_vendor_trade_accepts_owning_attributes(seeded: sqlite3.Connection) -> None:
    seeded.execute(
        "INSERT INTO vendor_trade(vendor_trade_id,vendor_id,acquisition_run_id,trade_kind,"
        "held,limitation,trade_license_number) VALUES (3,1,2,'general_contractor','Yes','Unlimited','123')"
    )
    seeded.execute(
        "INSERT INTO vendor_trade(vendor_trade_id,vendor_id,acquisition_run_id,trade_kind,"
        "held,level) VALUES (4,1,2,'electrical','Yes','Limited')"
    )


# --------------------------------------------------------------------------- #
# vec0 embedding table + parity view
# --------------------------------------------------------------------------- #


def test_vec0_partition_key_roundtrip(seeded: sqlite3.Connection) -> None:
    emb = struct.pack(f"{EMBED_DIM}f", *([0.1] * EMBED_DIM))
    seeded.execute(
        "INSERT INTO vendor_embedding(vendor_id, run_id, embedding) VALUES (1, 2, ?)",
        (emb,),
    )
    assert seeded.execute("SELECT count(*) FROM vendor_embedding").fetchone()[0] == 1


def test_parity_view_recollapses_qualifiers(seeded: sqlite3.Connection) -> None:
    seeded.execute(
        "INSERT INTO qualifier(qualifier_id,license_number,acquisition_run_id,"
        "qualifier_number,qualifier_status) VALUES (10,'L1',1,'111','Active')"
    )
    seeded.execute(
        "INSERT INTO qualifier(qualifier_id,license_number,acquisition_run_id,"
        "qualifier_number,qualifier_status) VALUES (11,'L1',1,'222','Active')"
    )
    row = seeded.execute(
        "SELECT qualifier_number, qualifier_status FROM v_license_flat WHERE license_number='L1'"
    ).fetchone()
    assert row == ("111; 222", "Active; Active")
