"""Opt-in live NCLBGC resolution test (auto-skipped in CI and by default).

Runs only when ``TEST_MODE=false`` is set deliberately in the shell *and* a public
general-contractor license number is supplied via ``NCLBGC_TEST_LICENSE`` (and,
optionally, ``NCLBGC_TEST_NAME``). The license is read from the environment rather
than hard-coded so no real value is ever committed to this tracked file. One
polite lookup against the public portal; proves the live wire flow, the
resolve-or-flag outcome (R4), and that a matched record decodes to the documented
twelve-field schema.

Copyright © 2026 Wolfgang Sanyer
Licensed under the Polyform Noncommercial License 1.0.0 (see LICENSE).
"""

import json
import os
from pathlib import Path

import pytest

from vendorscope import http_client, nclbgc_client
from vendorscope.cleaning import config

pytestmark = pytest.mark.integration

_OPT_IN = os.environ.get("TEST_MODE", "true") == "false"
_LICENSE = os.environ.get("NCLBGC_TEST_LICENSE", "")
_NAME = os.environ.get("NCLBGC_TEST_NAME", "")
_STATUSES = {"matched-by-license", "matched-by-name", "unresolved"}


@pytest.mark.skipif(not _OPT_IN, reason="live test is opt-in via TEST_MODE=false")
@pytest.mark.skipif(
    not (_LICENSE or _NAME),
    reason="supply NCLBGC_TEST_LICENSE (and/or NCLBGC_TEST_NAME) to run live",
)
def test_live_resolve_matches_expectations(tmp_path: Path) -> None:
    vendors = [{"name": _NAME, "license_number": _LICENSE}]
    client = http_client.build_client()
    try:
        result = nclbgc_client.acquire(
            client=client,
            data_raw=tmp_path,
            run_id="20260612T000000-nclbgc",
            vendors=vendors,
            delay=0.0,
        )
    finally:
        client.close()

    assert len(result.resolutions) == 1
    resolution = result.resolutions[0]
    assert resolution.status in _STATUSES

    # raw is frozen before any decode, hit or miss (R2).
    assert (result.raw_dir / "search-0.html").exists()
    assert (result.raw_dir / "acquire-manifest.json").exists()
    assert (result.raw_dir / "resolution-report.json").exists()

    # a match decodes to the documented twelve-field license schema (R8).
    if resolution.status != "unresolved":
        records = json.loads(
            (result.raw_dir / "nclbgc-licenses.json").read_text(encoding="utf-8")
        )
        assert records, "a matched key should decode at least one record"
        assert tuple(records[0]) == config.LICENSE_EXPECTED_COLUMNS
