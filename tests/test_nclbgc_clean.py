"""NCLBGC cleaning: config manifest and end-to-end cleaning (slice 2).

The config mirrors slice 1's shape; the end-to-end test runs a decoded fixture
record through the reused engine to prove the sigil strip, the packed multi-value
handling, conservation, and idempotency.

Copyright © 2026 Wolfgang Sanyer
Licensed under the Polyform Noncommercial License 1.0.0 (see LICENSE).
"""

from pathlib import Path

import pytest

from vendorscope import nclbgc_parse
from vendorscope.cleaning import config, engine

FIXTURES = Path(__file__).parent / "fixtures" / "nclbgc"


def _read(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def _clean_one() -> tuple[list[dict[str, str]], engine.CleanResult]:
    record = nclbgc_parse.decode_record(_read("detail.html"), _read("qualifiers.html"))
    rows = engine.assign_row_keys([record])
    return rows, engine.clean_table(rows, config.LICENSE_CONFIG)


@pytest.mark.unit
def test_license_config_manifest_matches_the_parser_fields() -> None:
    assert config.LICENSE_EXPECTED_COLUMNS == nclbgc_parse.FIELDS
    assert tuple(config.LICENSE_CONFIG.columns) == config.LICENSE_EXPECTED_COLUMNS
    assert set(config.LICENSE_SNAKE_CASE) == set(config.LICENSE_EXPECTED_COLUMNS)
    # the rename targets are unique (no two source columns collapse)
    assert len(set(config.LICENSE_SNAKE_CASE.values())) == len(
        config.LICENSE_SNAKE_CASE
    )


@pytest.mark.unit
def test_license_keys_and_red_set() -> None:
    assert config.LICENSE_CONFIG.dedup_key == ("License_Number",)
    assert config.LICENSE_RED_COLUMNS == ("Phone", "Qualifier_Name")


@pytest.mark.contract
def test_sigils_stripped_on_license_and_qualifier_numbers() -> None:
    _, result = _clean_one()
    row = result.rows[0]
    assert row["License_Number"] == "68764"  # L. sigil stripped (N3)
    assert row["Qualifier_Number"] == "900001; 900002"  # Q. stripped per element
    assert row["Status"] == "Active"
    assert row["Classifications"] == "Building; PU(Water Lines & Sewer Lines)"
    # qualifier columns stay packed (split into rows is slice 4's job)
    assert row["Qualifier_Name"] == "Sample Qualifier One; Sample Qualifier Two"


@pytest.mark.contract
def test_conservation_and_idempotency() -> None:
    rows, result = _clean_one()
    assert len(rows) == len(result.rows) + len(result.drops)  # conservation
    second = engine.clean_table(result.rows, config.LICENSE_CONFIG)
    assert second.corrections == []  # idempotent on the cleaned output


@pytest.mark.unit
def test_packed_qualifier_columns_clean_per_element() -> None:
    # Part II: Qualifier_Name hybrid-capped, Qualifier_Status a controlled vocab;
    # the columns are '; '-packed, so cleaning is applied per element.
    record = dict.fromkeys(config.LICENSE_EXPECTED_COLUMNS, "")
    record["License_Number"] = "L.5"
    record["Qualifier_Name"] = "JOHN SMITH; jane doe"
    record["Qualifier_Status"] = "Active; Bogus"
    rows = engine.assign_row_keys([record])
    result = engine.clean_table(rows, config.LICENSE_CONFIG)
    row = result.rows[0]
    assert row["Qualifier_Name"] == "John Smith; Jane Doe"  # hybrid-cap each element
    assert row["Qualifier_Status"] == "Active; Bogus"  # report-don't-coerce: unchanged
    assert any(
        v.column == "Qualifier_Status" and v.rule == "out-of-vocabulary"
        for v in result.violations
    )


@pytest.mark.unit
def test_report_dont_coerce_on_out_of_vocabulary_status() -> None:
    record = dict.fromkeys(config.LICENSE_EXPECTED_COLUMNS, "")
    record["License_Number"] = "L.99999"
    record["Status"] = "Bogus"
    rows = engine.assign_row_keys([record])
    result = engine.clean_table(rows, config.LICENSE_CONFIG)
    assert result.rows[0]["Status"] == "Bogus"  # unchanged
    assert any(
        v.column == "Status" and v.rule == "out-of-vocabulary"
        for v in result.violations
    )
