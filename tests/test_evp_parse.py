"""Parser contract against the captured fixture (REQ-01, REQ-07).

Copyright © 2026 Wolfgang Sanyer
Licensed under the Polyform Noncommercial License 1.0.0 (see LICENSE).
"""

from pathlib import Path

import pytest

from vendorscope import evp_parse

FIXTURES = Path(__file__).parent / "fixtures" / "evp"


def _read(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


@pytest.mark.contract
def test_parses_records_from_captured_fixture() -> None:
    records = evp_parse.parse_records(_read("vendordetails-clean.html"))
    assert len(records) == 24
    assert all(len(r) == 41 for r in records)
    assert all(r["EvpStatus"] == "Active" for r in records)


@pytest.mark.contract
def test_json_booleans_become_true_false_strings() -> None:
    records = evp_parse.parse_records(_read("vendordetails-clean.html"))
    # every value is a string (text-mode entry); the ten flags stringify via str()
    assert all(isinstance(v, str) for r in records for v in r.values())
    assert all(r["SmallBusiness"] == "False" for r in records)
    assert any(r["GeneralContractor"] == "True" for r in records)


@pytest.mark.contract
def test_template_miss_raises_specific_error() -> None:
    with pytest.raises(evp_parse.EmbeddedDataError):
        evp_parse.parse_records(_read("template-miss.html"))
