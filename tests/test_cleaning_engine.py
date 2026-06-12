"""Engine contracts: roles, report-don't-coerce, dedup, conservation (REQ-07..15).

Mechanics use a small ad-hoc config; the flags-end-to-end and report-don't-coerce
cases run against the real ``VENDOR_CONFIG`` on the parsed fixture.

Copyright © 2026 Wolfgang Sanyer
Licensed under the Polyform Noncommercial License 1.0.0 (see LICENSE).
"""

from pathlib import Path

import pytest

from vendorscope import evp_parse
from vendorscope.cleaning import config, engine
from vendorscope.cleaning.config import ColumnRule, TableConfig

FIXTURES = Path(__file__).parent / "fixtures" / "evp"

MINI = TableConfig(
    name="mini",
    columns={
        "Name": ColumnRule("name"),
        "Lic": ColumnRule("license"),
        "Flag": ColumnRule(
            "flag", allowed=("Yes", "No"), mapping={"true": "Yes", "false": "No"}
        ),
    },
    dedup_key=("Name", "Lic"),
    red_columns=(),
)


def _rows(*records: dict[str, str]) -> list[dict[str, str]]:
    return engine.assign_row_keys([dict(r) for r in records])


@pytest.mark.unit
def test_whitespace_and_role_corrections() -> None:
    result = engine.clean_table(
        _rows({"Name": "ACME  LLC", "Lic": "123", "Flag": "true"}), MINI
    )
    row = result.rows[0]
    assert row["Name"] == "Acme LLC"
    assert row["Lic"] == "123"
    assert row["Flag"] == "Yes"  # flags land canonical Yes/No (REQ-07)
    assert {c.rule for c in result.corrections} >= {"name", "flag"}


@pytest.mark.unit
def test_report_dont_coerce_leaves_value_and_flags_violation() -> None:
    result = engine.clean_table(
        _rows({"Name": "Acme", "Lic": "WV063716", "Flag": "false"}), MINI
    )
    assert result.rows[0]["Lic"] == "WV063716"  # unchanged (REQ-09)
    assert [(v.column, v.rule) for v in result.violations] == [
        ("Lic", "non-standard-license")
    ]


@pytest.mark.unit
def test_missing_configured_column_hard_fails() -> None:
    with pytest.raises(engine.MissingColumnError):
        engine.clean_table(_rows({"Name": "Acme", "Lic": "123"}), MINI)  # no Flag


@pytest.mark.unit
def test_dedup_blank_key_rows_never_match() -> None:
    result = engine.clean_table(
        _rows(
            {"Name": "Acme", "Lic": "", "Flag": "false"},
            {"Name": "Acme", "Lic": "", "Flag": "false"},
        ),
        MINI,
    )
    assert (
        len(result.rows) == 2 and result.drops == []
    )  # blank key part -> no match (REQ-11)


@pytest.mark.unit
def test_dedup_most_complete_survives_and_drop_is_recorded() -> None:
    result = engine.clean_table(
        _rows(
            {"Name": "Acme", "Lic": "123", "Flag": ""},  # row_key 0, completeness 2
            {
                "Name": "Acme",
                "Lic": "123",
                "Flag": "false",
            },  # row_key 1, completeness 3
        ),
        MINI,
    )
    assert len(result.rows) == 1
    assert result.rows[0]["row_key"] == "1"
    drop = result.drops[0]
    assert drop.dropped_row_key == "0" and drop.surviving_row_key == "1"


@pytest.mark.unit
def test_dedup_tie_breaks_by_original_order() -> None:
    result = engine.clean_table(
        _rows(
            {"Name": "Beta", "Lic": "55", "Flag": "false"},
            {"Name": "Beta", "Lic": "55", "Flag": "false"},
        ),
        MINI,
    )
    assert result.rows[0]["row_key"] == "0"
    assert result.drops[0].dropped_row_key == "1"


@pytest.mark.unit
def test_conservation_identity_reconciles_on_seeded_duplicate() -> None:
    rows = _rows(
        {"Name": "Acme", "Lic": "123", "Flag": "false"},
        {"Name": "Acme", "Lic": "123", "Flag": "false"},
        {"Name": "Beta", "Lic": "9", "Flag": "true"},
    )
    result = engine.clean_table(rows, MINI)
    assert len(rows) == len(result.rows) + len(result.drops)  # REQ-15
    assert len(result.drops) == 1


@pytest.mark.contract
def test_flags_land_yes_no_end_to_end_on_fixture() -> None:
    page = (FIXTURES / "vendordetails-clean.html").read_text(encoding="utf-8")
    rows = engine.assign_row_keys(evp_parse.parse_records(page))
    result = engine.clean_table(rows, config.VENDOR_CONFIG)
    flags = [
        "SmallBusiness",
        "DBE",
        "NPWC",
        "GeneralContractor",
        "ElectricalContractor",
        "PlumbingFireSprinklerContractor",
        "MechanicalHeating",
        "TradesSubContractor",
        "ArchitecturalServices",
        "EngineeringServices",
    ]
    for row in result.rows:
        for flag in flags:
            assert row[flag] in ("Yes", "No")
    assert all(r["SmallBusiness"] == "No" for r in result.rows)
    assert any(r["GeneralContractor"] == "Yes" for r in result.rows)


@pytest.mark.contract
def test_real_license_oddities_surface_as_violations() -> None:
    page = (FIXTURES / "vendordetails-clean.html").read_text(encoding="utf-8")
    rows = engine.assign_row_keys(evp_parse.parse_records(page))
    result = engine.clean_table(rows, config.VENDOR_CONFIG)
    gc = [v for v in result.violations if v.column == "GeneralContractorLicenseNumber"]
    assert len(gc) >= 4  # the fixture carries several out-of-format GC licenses
