"""Unit tests for the pure eVP results-page parsers (offline, fixture-driven).

The fixture under ``tests/fixtures/evp/`` is a real results page trimmed to two
records with contact PII and the street address replaced by placeholders.

Copyright © 2026 Wolfgang Sanyer
Licensed under the Polyform Noncommercial License 1.0.0 (see LICENSE).
"""

from pathlib import Path

import pytest

from vendorscope.evp_parse import filters_applied, parse_embedded_records

FIXTURE = Path(__file__).parent / "fixtures" / "evp" / "results.html"


def _html() -> str:
    return FIXTURE.read_text(encoding="utf-8")


@pytest.mark.unit
def test_parse_embedded_records_extracts_records_and_full_columns():
    records = parse_embedded_records(_html())
    assert len(records) == 2
    by_name = {r["Name"]: r for r in records}
    vendor = by_name["24North Investments LLC"]
    assert vendor["EvpStatus"] == "Active"
    assert len(vendor) == 41  # the full vendor-master column set
    assert vendor["MainContactEmail"] == "contact@example.com"  # PII placeholdered


@pytest.mark.unit
def test_parse_embedded_records_raises_when_var_data_missing():
    with pytest.raises(ValueError):
        parse_embedded_records("<html><body>no data here</body></html>")


@pytest.mark.unit
def test_filters_applied_true_on_matching_summary_and_status():
    page = _html()
    records = parse_embedded_records(page)
    assert (
        filters_applied(page, records, ("Status: Active", "Public Utilities")) is True
    )


@pytest.mark.unit
def test_filters_applied_false_when_summary_missing():
    records = parse_embedded_records(_html())
    assert filters_applied("<html></html>", records, ("Status: Active",)) is False


@pytest.mark.unit
def test_filters_applied_false_when_status_drifts():
    page = _html()
    drifted = [dict(r, EvpStatus="Pending") for r in parse_embedded_records(page)]
    assert filters_applied(page, drifted, ("Status: Active",)) is False
