"""Opt-in live acquisition test (auto-skipped in CI and by default).

Runs only when ``TEST_MODE=false`` is set deliberately in the shell; ``conftest``
defaults it on so this never runs in CI (3.2). One polite GET of the public
results page.

Copyright © 2026 Wolfgang Sanyer
Licensed under the Polyform Noncommercial License 1.0.0 (see LICENSE).
"""

import json
import os
from pathlib import Path

import pytest

from vendorscope import evp_client, http_client
from vendorscope.cleaning import config

pytestmark = pytest.mark.integration

_OPT_IN = os.environ.get("TEST_MODE", "true") == "false"


@pytest.mark.skipif(not _OPT_IN, reason="live test is opt-in via TEST_MODE=false")
def test_live_acquire_matches_expectations(tmp_path: Path) -> None:
    client = http_client.build_client()
    try:
        result = evp_client.acquire(
            client=client, data_raw=tmp_path, run_id="20260612T000000-evp"
        )
    finally:
        client.close()
    assert result.record_count >= config.RECORD_FLOOR
    assert result.alarms == []
    records = json.loads(
        (result.raw_dir / "evp-vendors.json").read_text(encoding="utf-8")
    )
    assert all(r["EvpStatus"] == "Active" for r in records)
    assert len(records[0]) == 41
