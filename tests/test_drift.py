"""Drift predicates over the parsed page (REQ-02, REQ-03).

Red on all three drift fixtures (a non-Active record, an added filter clause, a
collapsed single-state HUB) and green on the clean fixture. The record-count
floor is a pure predicate tested with explicit production counts; the clean
fixture is coverage-sized (24), so its end-to-end check uses a fixture-scoped
floor while the floor logic itself is checked at the real 500.

Copyright © 2026 Wolfgang Sanyer
Licensed under the Polyform Noncommercial License 1.0.0 (see LICENSE).
"""

from pathlib import Path

import pytest

from vendorscope import drift, evp_parse

FIXTURES = Path(__file__).parent / "fixtures" / "evp"


def _read(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def _evaluate(name: str, *, floor: int = 20) -> list[drift.DriftAlarm]:
    page = _read(name)
    return drift.evaluate(page, evp_parse.parse_records(page), floor=floor)


@pytest.mark.contract
def test_clean_fixture_has_no_drift() -> None:
    assert _evaluate("vendordetails-clean.html") == []


@pytest.mark.contract
def test_clean_fixture_summary_parses_to_expected_clauses() -> None:
    count, clauses = drift.parse_filter_summary(_read("vendordetails-clean.html"))
    assert count == 24
    assert clauses == drift.EXPECTED_CLAUSES


@pytest.mark.contract
def test_non_active_record_is_drift() -> None:
    kinds = {a.kind for a in _evaluate("vendordetails-drift-nonactive.html")}
    assert "non-active-status" in kinds


@pytest.mark.contract
def test_added_filter_clause_is_drift() -> None:
    kinds = {a.kind for a in _evaluate("vendordetails-drift-addedclause.html")}
    assert "filter-clause" in kinds


@pytest.mark.contract
def test_single_state_hub_is_drift() -> None:
    kinds = {a.kind for a in _evaluate("vendordetails-drift-singlecategoryhub.html")}
    assert "hub-tristate" in kinds


@pytest.mark.unit
def test_record_count_floor_predicate() -> None:
    assert drift.count_floor_drift(570, 500) is False
    assert drift.count_floor_drift(499, 500) is True


@pytest.mark.unit
def test_clause_set_exact_comparison() -> None:
    assert drift.clause_drift(drift.EXPECTED_CLAUSES) is False
    added = (*drift.EXPECTED_CLAUSES, "HUB Certification Status: Certified")
    assert drift.clause_drift(added) is True
