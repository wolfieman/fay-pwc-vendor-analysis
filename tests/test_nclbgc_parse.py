"""Unit tests for the pure NCLBGC HTML-fragment parsers (offline, fixture-driven).

The fixtures under ``tests/fixtures/nclbgc/`` are real portal responses with PII
(phone, qualifier name, street address) replaced by placeholders.

Copyright © 2026 Wolfgang Sanyer
Licensed under the Polyform Noncommercial License 1.0.0 (see LICENSE).
"""

from pathlib import Path

import pytest

from vendorscope.nclbgc_parse import (
    parse_detail,
    parse_qualifiers,
    parse_search_rows,
)

FIXTURES = Path(__file__).parent / "fixtures" / "nclbgc"


def _fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


@pytest.mark.unit
def test_parse_search_rows_extracts_license_company_and_key():
    rows = parse_search_rows(_fixture("search.html"))
    assert len(rows) == 1
    row = rows[0]
    assert row["license_number"] == "L.85168"
    assert row["company_name"] == "24North Investments LLC"
    assert row["account_type"] == "License"
    assert row["key"] == "JTeHh5hHBoEZqYLA9I%2b%2bZw%3d%3d"


@pytest.mark.unit
def test_parse_search_rows_empty_when_no_table():
    assert parse_search_rows("<div>no results</div>") == []


@pytest.mark.unit
def test_parse_detail_reads_all_fields():
    detail = parse_detail(_fixture("details.html"))
    assert detail["company_name"] == "24North Investments LLC"
    assert detail["license_number"] == "L.85168"
    assert detail["account_type"] == "License"
    assert detail["issue_date"] == "03/02/2021"
    assert detail["expiration_date"] == "12/31/2026"
    assert detail["status"] == "Active"
    assert detail["license_limitation"] == "Limited"
    assert detail["classifications"] == "Residential"
    assert detail["phone"] == "919-555-0100"
    assert "Example Dr." in detail["address"]
    assert "Raleigh, NC" in detail["address"]


@pytest.mark.unit
def test_parse_detail_missing_fields_default_to_empty():
    detail = parse_detail("<fieldset></fieldset>")
    assert detail["company_name"] == ""
    assert detail["classifications"] == ""


@pytest.mark.unit
def test_parse_qualifiers_extracts_rows_and_skips_header():
    quals = parse_qualifiers(_fixture("qualifiers.html"))
    assert quals == [
        {
            "name": "Jordan Q. Sample",
            "qualifier_number": "Q.11011",
            "status": "Active",
        }
    ]


@pytest.mark.unit
def test_parse_qualifiers_empty_when_no_table():
    assert parse_qualifiers("<div></div>") == []
