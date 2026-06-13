"""Config manifest + the dictionary-vs-config agreement (REQ-08, REQ-13, R8).

The data dictionary is the one tracked, PII-free data artifact; the "no test
reads data/" rule guards the gitignored PII zones, not this hand-authored
contract. This test pins each executable config to its dictionary section so
neither can drift unnoticed: the source-field manifest, the snake_case rename
map, the red set, and (one-way) that every configured vocabulary term is
documented.

The dictionary now carries two source tables (eVP, NCLBGC), each a level-2
section. The row parser is scoped to one section so the two manifests are pinned
independently — without scoping, the NCLBGC rows would break the eVP counts.

Copyright © 2026 Wolfgang Sanyer
Licensed under the Polyform Noncommercial License 1.0.0 (see LICENSE).
"""

import re
from pathlib import Path

import pytest

from vendorscope.cleaning import config

DICTIONARY = Path(__file__).parents[1] / "data" / "DATA_DICTIONARY.md"
_ROW = re.compile(r"^\|\s*\d+\s*\|(.+)$", re.M)


def _section_body(heading_contains: str) -> str:
    """The text under the level-2 (`## `) heading containing the marker, up to
    the next level-2 heading (or end of file). Level-3 subsections stay inside."""
    text = DICTIONARY.read_text(encoding="utf-8")
    pat = re.compile(
        rf"^##[^\n]*{re.escape(heading_contains)}[^\n]*\n(.*?)(?=^## |\Z)",
        re.M | re.S,
    )
    match = pat.search(text)
    assert match, f"no level-2 section heading contains {heading_contains!r}"
    return match.group(1)


def _dictionary_rows(section: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for line in _ROW.findall(_section_body(section)):
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


# ---- eVP vendor table ----


@pytest.mark.unit
def test_manifest_is_the_41_observed_fields() -> None:
    rows = _dictionary_rows("eVP")
    assert len(config.EXPECTED_COLUMNS) == 41
    assert tuple(r["source"] for r in rows) == config.EXPECTED_COLUMNS


@pytest.mark.unit
def test_snake_case_rename_matches_dictionary() -> None:
    rows = _dictionary_rows("eVP")
    assert {r["source"]: r["snake"] for r in rows} == config.SNAKE_CASE
    # the rename targets are unique (no two source columns collapse)
    assert len(set(config.SNAKE_CASE.values())) == len(config.SNAKE_CASE)


@pytest.mark.unit
def test_red_set_matches_dictionary() -> None:
    rows = _dictionary_rows("eVP")
    red = {r["source"] for r in rows if "red" in r["sensitivity"]}
    assert red == set(config.RED_COLUMNS)


@pytest.mark.unit
def test_every_configured_vocabulary_term_is_documented() -> None:
    notes = {r["source"]: r["notes"] for r in _dictionary_rows("eVP")}
    for source, rule in config.VENDOR_CONFIG.columns.items():
        if rule.role != "vocab":
            continue
        for term in rule.allowed:
            assert term in notes[source], f"{source}: {term!r} not in dictionary notes"


@pytest.mark.unit
def test_config_keyset_is_the_manifest() -> None:
    assert tuple(config.VENDOR_CONFIG.columns) == config.EXPECTED_COLUMNS
    assert set(config.SNAKE_CASE) == set(config.EXPECTED_COLUMNS)


# ---- NCLBGC license-details table ----


@pytest.mark.unit
def test_license_manifest_is_the_12_documented_fields() -> None:
    rows = _dictionary_rows("NCLBGC")
    assert len(config.LICENSE_EXPECTED_COLUMNS) == 12
    assert tuple(r["source"] for r in rows) == config.LICENSE_EXPECTED_COLUMNS


@pytest.mark.unit
def test_license_snake_case_rename_matches_dictionary() -> None:
    rows = _dictionary_rows("NCLBGC")
    snake = config.LICENSE_SNAKE_CASE
    assert {r["source"]: r["snake"] for r in rows} == snake
    # the rename targets are unique (no two source columns collapse)
    assert len(set(snake.values())) == len(snake)


@pytest.mark.unit
def test_license_red_set_matches_dictionary() -> None:
    rows = _dictionary_rows("NCLBGC")
    red = {r["source"] for r in rows if "red" in r["sensitivity"]}
    assert red == set(config.LICENSE_RED_COLUMNS)


@pytest.mark.unit
def test_license_every_configured_vocabulary_term_is_documented() -> None:
    notes = {r["source"]: r["notes"] for r in _dictionary_rows("NCLBGC")}
    for source, rule in config.LICENSE_CONFIG.columns.items():
        if rule.role != "vocab":
            continue
        for term in rule.allowed:
            assert term in notes[source], f"{source}: {term!r} not in dictionary notes"


@pytest.mark.unit
def test_license_config_keyset_is_the_manifest() -> None:
    assert tuple(config.LICENSE_CONFIG.columns) == config.LICENSE_EXPECTED_COLUMNS
    assert set(config.LICENSE_SNAKE_CASE) == set(config.LICENSE_EXPECTED_COLUMNS)
