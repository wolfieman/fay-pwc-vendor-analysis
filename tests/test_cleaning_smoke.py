"""Smoke test: the cleaning engine runs on real acquired eVP data.

Drives the committed eVP fixture (the embedded ``var data`` block) through the
parser and the cleaning engine. This guards the contract between acquisition
and cleaning: the vendor configuration must still name columns the live
acquisition actually emits, cleaning must be idempotent on real records, and
the PII split must hold. Counts are not asserted — the fixture is a sanitized
two-record sample — only structural invariants are.

Copyright © 2026 Wolfgang Sanyer
Licensed under the Polyform Noncommercial License 1.0.0 (see LICENSE).
"""

from pathlib import Path

import pandas as pd
import pytest

from vendorscope.cleaning import VENDOR_CONFIG, clean_table, split_pii
from vendorscope.evp_parse import parse_embedded_records

pytestmark = pytest.mark.unit

FIXTURE = Path(__file__).parent / "fixtures" / "evp" / "results.html"


def _vendor_frame() -> pd.DataFrame:
    records = parse_embedded_records(FIXTURE.read_text(encoding="utf-8"))
    return pd.DataFrame(records).fillna("").astype(str)


def _declared_columns() -> set[str]:
    """Every column the vendor config names across all its roles."""
    declared = set(
        VENDOR_CONFIG.email_columns
        + VENDOR_CONFIG.phone_columns
        + VENDOR_CONFIG.business_name_columns
        + VENDOR_CONFIG.address_columns
        + VENDOR_CONFIG.date_columns
        + VENDOR_CONFIG.text_id_columns
        + VENDOR_CONFIG.flag_columns
        + VENDOR_CONFIG.list_columns
        + VENDOR_CONFIG.dedup_keys
        + VENDOR_CONFIG.pii_columns
    )
    declared |= set(VENDOR_CONFIG.vocabularies)
    declared |= set(VENDOR_CONFIG.mapped_vocab_columns)
    return declared


def test_vendor_config_matches_the_acquisition_schema():
    # Columns the config names but the records lack would be silently skipped
    # by the engine, so an absent column is acquisition/config drift, not noise.
    frame = _vendor_frame()
    missing = sorted(c for c in _declared_columns() if c not in frame.columns)
    assert not missing, f"config columns absent from eVP records: {missing}"


def test_engine_cleans_real_records_and_is_idempotent():
    frame = _vendor_frame()
    first = clean_table(frame, VENDOR_CONFIG)
    assert list(first.frame.columns) == list(frame.columns)
    second = clean_table(first.frame, VENDOR_CONFIG)
    assert second.frame.equals(first.frame)
    assert not second.corrections


def test_pii_split_excludes_contact_columns():
    cleaned = clean_table(_vendor_frame(), VENDOR_CONFIG).frame
    public, pii = split_pii(cleaned, VENDOR_CONFIG.pii_columns)
    assert all(column not in public.columns for column in VENDOR_CONFIG.pii_columns)
    assert list(pii.columns) == [
        column for column in VENDOR_CONFIG.pii_columns if column in cleaned.columns
    ]
