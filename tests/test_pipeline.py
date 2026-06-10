"""Tests for the vendorscope.pipeline orchestrator: the scripts it references
exist, and `reproduce` chains clean -> profile -> audit without scraping.

Copyright © 2026 Wolfgang Sanyer
Licensed under the Polyform Noncommercial License 1.0.0 (see LICENSE).
"""

import pytest

from vendorscope import pipeline


def _record_runs(monkeypatch) -> list[str]:
    """Patch pipeline._run to record the stem of each script it would run."""
    calls: list[str] = []

    def record(script, _args):
        calls.append(script.stem)

    monkeypatch.setattr(pipeline, "_run", record)
    return calls


@pytest.mark.unit
def test_all_scripts_exist():
    for name, path in pipeline.SCRIPTS.items():
        assert path.exists(), f"missing script for {name}: {path}"


@pytest.mark.unit
def test_reproduce_chains_clean_profile_audit_in_order(monkeypatch):
    calls = _record_runs(monkeypatch)
    pipeline.reproduce()
    assert calls == ["clean_data", "profile_data", "make_audit"]


@pytest.mark.unit
def test_reproduce_never_scrapes(monkeypatch):
    calls = _record_runs(monkeypatch)
    pipeline.reproduce()
    assert "nclbgc_licenses_acquisition" not in calls
    assert "nclbgc_license_details_acquisition" not in calls
