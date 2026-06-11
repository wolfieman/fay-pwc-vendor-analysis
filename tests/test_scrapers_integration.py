"""Integration: live NCLBGC-portal scraper smoke (the "canary").

Drives a real browser against the live portal, so it is slow, network-dependent,
and non-deterministic if the site changes. SKIPPED by default; opt in with:

    TEST_MODE=false uv run pytest -m integration

It asserts a known-good fixture on the live site, so a failure means either a
real regression or site drift (selectors/data changed) -> a re-validation signal.

Copyright © 2026 Wolfgang Sanyer
Licensed under the Polyform Noncommercial License 1.0.0 (see LICENSE).
"""

import os
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

from vendorscope.evp_client import EVPClient
from vendorscope.nclbgc_client import NCLBGCClient

_OFFLINE = os.environ.get("TEST_MODE", "true").lower() != "false"
pytestmark = pytest.mark.skipif(
    _OFFLINE, reason="live site; set TEST_MODE=false to run"
)

_ROOT = Path(__file__).resolve().parents[1]
LICENSES = _ROOT / "src" / "acquisition" / "nclbgc_licenses_acquisition.py"
DETAILS = _ROOT / "src" / "acquisition" / "nclbgc_license_details_acquisition.py"

# Known-good fixture on the live NCLBGC portal (re-verify if the site changes).
KNOWN_LICENSE = "85168"
KNOWN_COMPANY = "24North Investments LLC"


@pytest.mark.integration
def test_licenses_scraper_finds_known_license(tmp_path):
    inp, out = tmp_path / "in.xlsx", tmp_path / "out.xlsx"
    pd.DataFrame({"Vendor_Name": [KNOWN_COMPANY], "License_Number": [""]}).to_excel(
        inp, index=False
    )
    subprocess.run(
        [
            sys.executable,
            str(LICENSES),
            "--input",
            str(inp),
            "--limit",
            "1",
            "--out",
            str(out),
        ],
        check=True,
        timeout=240,
    )
    assert pd.read_excel(out).iloc[0, 1] == f"L.{KNOWN_LICENSE}"


@pytest.mark.integration
def test_details_scraper_extracts_known_company(tmp_path):
    inp, out = tmp_path / "in.xlsx", tmp_path / "out.xlsx"
    pd.DataFrame({"License_Number": [KNOWN_LICENSE]}).to_excel(inp, index=False)
    subprocess.run(
        [
            sys.executable,
            str(DETAILS),
            "--input",
            str(inp),
            "--limit",
            "1",
            "--headless",
            "--out",
            str(out),
        ],
        check=True,
        timeout=240,
    )
    result = pd.read_excel(out)
    assert result.iloc[0]["Company_Name"] == KNOWN_COMPANY
    assert "Error" not in result.columns


@pytest.mark.integration
def test_nclbgc_client_finds_known_license_via_http():
    """The browserless httpx client reaches parity with the scraper canary."""
    with NCLBGCClient() as client:
        record = client.license_record(KNOWN_COMPANY)
    assert record is not None
    assert record["license_number"] == f"L.{KNOWN_LICENSE}"
    detail = record["detail"]
    assert detail["company_name"] == KNOWN_COMPANY
    assert detail["status"]
    assert record["qualifiers"]


@pytest.mark.integration
def test_evp_client_fetches_active_public_utilities_via_fast_path():
    """The browserless eVP fast path returns the filtered Active vendor set."""
    with EVPClient() as client:
        records = client.fetch_records()
    assert len(records) > 400  # ~570 Active + Public Utilities (grows over time)
    assert all(r["EvpStatus"] == "Active" for r in records)
    assert any(r["Name"] == "24North Investments LLC" for r in records)
