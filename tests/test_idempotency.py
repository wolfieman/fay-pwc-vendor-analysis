"""Idempotency as a permanent regression test (REQ-14).

Re-cleaning cleaned output yields zero corrections, asserted in memory and
through a serialized round-trip in the raw header space (before the snake_case
rename, per 4.2). A county literally named "NA" and a leading-zero ZIP survive
the round-trip as strings.

Copyright © 2026 Wolfgang Sanyer
Licensed under the Polyform Noncommercial License 1.0.0 (see LICENSE).
"""

from pathlib import Path

import pytest

from vendorscope import evp_parse, tabular
from vendorscope.cleaning import config, engine

FIXTURES = Path(__file__).parent / "fixtures" / "evp"


def _clean_once(name: str) -> engine.CleanResult:
    page = (FIXTURES / name).read_text(encoding="utf-8")
    rows = engine.assign_row_keys(evp_parse.parse_records(page))
    return engine.clean_table(rows, config.VENDOR_CONFIG)


@pytest.mark.contract
def test_idempotent_in_memory() -> None:
    first = _clean_once("vendordetails-clean.html")
    second = engine.clean_table(first.rows, config.VENDOR_CONFIG)
    assert second.corrections == []
    assert len(second.rows) == len(first.rows) and second.drops == []


@pytest.mark.contract
def test_idempotent_through_serialized_round_trip(tmp_path: Path) -> None:
    first = _clean_once("vendordetails-synthetic.html")
    columns = ["row_key", *config.EXPECTED_COLUMNS]
    path = tmp_path / "evp-cleaned-rawheaders.csv"
    tabular.write_csv(path, first.rows, columns=columns)
    back = tabular.read_csv(path)

    # survives the round trip as text
    assert any(r["County"] == "NA" for r in back)
    assert any(r["ZipCode"] == "02134" for r in back)

    second = engine.clean_table(back, config.VENDOR_CONFIG)
    assert second.corrections == []  # zero new corrections on the cleaned output
