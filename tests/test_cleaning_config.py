"""Config manifest + the dictionary-vs-config agreement (REQ-08, REQ-13).

The data dictionary is the one tracked, PII-free data artifact; the "no test
reads data/" rule guards the gitignored PII zones, not this hand-authored
contract. This test pins the executable config to the dictionary so neither can
drift unnoticed: the source-field manifest, the snake_case rename map, the red
set, and (one-way) that every configured vocabulary term is documented.

Copyright © 2026 Wolfgang Sanyer
Licensed under the Polyform Noncommercial License 1.0.0 (see LICENSE).
"""

import re
from pathlib import Path

import pytest

from vendorscope.cleaning import config

DICTIONARY = Path(__file__).parents[1] / "data" / "DATA_DICTIONARY.md"
_ROW = re.compile(r"^\|\s*\d+\s*\|(.+)$", re.M)


def _dictionary_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for line in _ROW.findall(DICTIONARY.read_text(encoding="utf-8")):
        cells = [c.strip() for c in line.split("|")]
        # cells: source, snake, type, sensitivity, notes  (trailing empty dropped)
        rows.append(
            {
                "source": cells[0],
                "snake": cells[1],
                "sensitivity": cells[3],
                "notes": cells[4],
            }
        )
    return rows


@pytest.mark.unit
def test_manifest_is_the_41_observed_fields() -> None:
    rows = _dictionary_rows()
    assert len(config.EXPECTED_COLUMNS) == 41
    assert tuple(r["source"] for r in rows) == config.EXPECTED_COLUMNS


@pytest.mark.unit
def test_snake_case_rename_matches_dictionary() -> None:
    rows = _dictionary_rows()
    assert {r["source"]: r["snake"] for r in rows} == config.SNAKE_CASE
    # the rename targets are unique (no two source columns collapse)
    assert len(set(config.SNAKE_CASE.values())) == len(config.SNAKE_CASE)


@pytest.mark.unit
def test_red_set_matches_dictionary() -> None:
    rows = _dictionary_rows()
    red = {r["source"] for r in rows if "red" in r["sensitivity"]}
    assert red == set(config.RED_COLUMNS)


@pytest.mark.unit
def test_every_configured_vocabulary_term_is_documented() -> None:
    notes = {r["source"]: r["notes"] for r in _dictionary_rows()}
    for source, rule in config.VENDOR_CONFIG.columns.items():
        if rule.role != "vocab":
            continue
        for term in rule.allowed:
            assert term in notes[source], f"{source}: {term!r} not in dictionary notes"


@pytest.mark.unit
def test_config_keyset_is_the_manifest() -> None:
    assert tuple(config.VENDOR_CONFIG.columns) == config.EXPECTED_COLUMNS
    assert set(config.SNAKE_CASE) == set(config.EXPECTED_COLUMNS)
