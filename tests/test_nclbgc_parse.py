"""NCLBGC fragment parser contracts (stdlib ``html.parser``, decision D6).

Tested against the committed fixtures. The parser emits the Master Data
Documentation Part II field names (the raw header space); the snake_case rename,
sigil strip, and cleaning happen later, exactly as in slice 1.

Copyright © 2026 Wolfgang Sanyer
Licensed under the Polyform Noncommercial License 1.0.0 (see LICENSE).
"""

from pathlib import Path

import pytest

from vendorscope import nclbgc_parse

FIXTURES = Path(__file__).parent / "fixtures" / "nclbgc"


def _read(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


@pytest.mark.contract
def test_search_keys_extracted_from_onclick() -> None:
    keys = nclbgc_parse.parse_search_keys(_read("search-result.html"))
    assert keys == ["SYNTHETICKEY0001%3d%3d"]


@pytest.mark.contract
def test_empty_search_yields_no_keys() -> None:
    assert nclbgc_parse.parse_search_keys(_read("search-empty.html")) == []


@pytest.mark.contract
def test_detail_parses_to_part_ii_fields() -> None:
    rec = nclbgc_parse.parse_detail(_read("detail.html"))
    assert rec["License_Number"] == "L.68764"  # sigil kept at parse; stripped at clean
    assert rec["Company_Name"] == "A & D Enterprises, Inc."
    assert rec["Status"] == "Active"
    assert rec["License_Limitation"] == "Unlimited"
    assert rec["Issue_Date"] == "01/04/2010"
    assert rec["Expiration_Date"] == "12/31/2026"
    # the <br />-separated classifications become a '; '-packed cell
    assert rec["Classifications"] == "Building; PU(Water Lines & Sewer Lines)"
    assert rec["Phone"] == "redacted-phone"  # the sanitized fixture value
    assert "Account Type" not in rec  # a non-schema constant, dropped


@pytest.mark.contract
def test_qualifiers_parse_to_rows() -> None:
    rows = nclbgc_parse.parse_qualifiers(_read("qualifiers.html"))
    assert [r["Qualifier_Number"] for r in rows] == ["Q.900001", "Q.900002"]
    assert [r["Qualifier_Status"] for r in rows] == ["Active", "Active"]
    assert all("Sample Qualifier" in r["Qualifier_Name"] for r in rows)


@pytest.mark.contract
def test_qualifiers_scrub_status_header_bleed() -> None:
    rows = nclbgc_parse.parse_qualifiers(_read("qualifiers-quirk.html"))
    # the bled header row (Name / Qualifier # / Status) is dropped; two real rows remain
    assert [r["Qualifier_Number"] for r in rows] == ["Q.900003", "Q.900004"]
    assert [r["Qualifier_Status"] for r in rows] == ["Active", "Inactive"]


@pytest.mark.contract
def test_decode_record_combines_detail_with_packed_qualifiers() -> None:
    rec = nclbgc_parse.decode_record(_read("detail.html"), _read("qualifiers.html"))
    assert len(rec) == len(nclbgc_parse.FIELDS) == 12
    assert rec["License_Number"] == "L.68764"
    assert rec["Qualifier_Number"] == "Q.900001; Q.900002"  # packed
    assert rec["Qualifier_Name"] == "Sample Qualifier One; Sample Qualifier Two"
    assert rec["Qualifier_Status"] == "Active; Active"


@pytest.mark.contract
def test_template_miss_raises() -> None:
    with pytest.raises(nclbgc_parse.NclbgcTemplateError):
        nclbgc_parse.parse_detail(_read("matters-empty.html"))  # no display fields
