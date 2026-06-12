"""Text-mode IO, manifest check, snake_case rename, PII split (REQ-06/12/13/16).

All file IO here uses ``tmp_path``; no test reads ``data/``.

Copyright © 2026 Wolfgang Sanyer
Licensed under the Polyform Noncommercial License 1.0.0 (see LICENSE).
"""

from pathlib import Path

import pytest

from vendorscope import tabular
from vendorscope.cleaning import config


@pytest.mark.unit
def test_text_mode_round_trip_preserves_na_zeros_and_blanks(tmp_path: Path) -> None:
    rows = [
        {"row_key": "00", "County": "NA", "ZipCode": "02134", "URL": ""},
        {"row_key": "01", "County": "Wake", "ZipCode": "27601", "URL": ""},
    ]
    path = tmp_path / "rt.csv"
    tabular.write_csv(path, rows, columns=["row_key", "County", "ZipCode", "URL"])
    back = tabular.read_csv(path)
    assert back[0]["County"] == "NA"  # a county literally named NA is data
    assert back[0]["ZipCode"] == "02134"  # leading zero preserved
    assert back[0]["URL"] == ""  # blank stays blank, not the float NaN


@pytest.mark.unit
def test_manifest_check_passes_on_expected_and_fails_on_rename() -> None:
    tabular.assert_manifest(config.EXPECTED_COLUMNS)  # no raise
    doctored = ("Renamed", *config.EXPECTED_COLUMNS[1:])
    with pytest.raises(tabular.ManifestError):
        tabular.assert_manifest(doctored)


@pytest.mark.unit
def test_rename_to_snake_and_uniqueness() -> None:
    rows = [{"Name": "Acme", "ZipCode": "27601", "row_key": "00"}]
    renamed = tabular.rename_snake(rows, {"Name": "name", "ZipCode": "zip_code"})
    assert renamed[0] == {"name": "Acme", "zip_code": "27601", "row_key": "00"}
    with pytest.raises(tabular.UniquenessError):
        tabular.rename_snake(rows, {"Name": "x", "ZipCode": "x"})  # collide


@pytest.mark.unit
def test_pii_split_is_lossless_and_drops_red_from_deliverable() -> None:
    rows = [
        {
            "row_key": "00",
            "Name": "Acme",
            "MainContactName": "A",
            "MainContactEmail": "e",
            "MainContactPhone": "p",
        },
        {
            "row_key": "01",
            "Name": "Beta",
            "MainContactName": "B",
            "MainContactEmail": "e2",
            "MainContactPhone": "p2",
        },
    ]
    deliverable, contacts = tabular.split_pii(rows, config.RED_COLUMNS)
    assert all(c not in deliverable[0] for c in config.RED_COLUMNS)
    assert set(contacts[0]) == {"row_key", *config.RED_COLUMNS}
    # lossless join on row_key, unique in both
    d_keys = [r["row_key"] for r in deliverable]
    c_keys = [r["row_key"] for r in contacts]
    assert d_keys == c_keys == ["00", "01"]
    assert len(set(d_keys)) == len(d_keys)
