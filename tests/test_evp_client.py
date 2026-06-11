"""Offline unit tests for the eVP client's fast path (httpx.MockTransport).

The repair path drives a real browser and is exercised only by the opt-in live
integration test, never here.

Copyright © 2026 Wolfgang Sanyer
Licensed under the Polyform Noncommercial License 1.0.0 (see LICENSE).
"""

import html
import json
from pathlib import Path

import httpx
import pytest

from vendorscope.evp_client import EVPClient

FIXTURE = Path(__file__).parent / "fixtures" / "evp" / "results.html"


def _client(body: str) -> EVPClient:
    def handler(_req: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=body)

    http = httpx.Client(
        base_url="https://evp.nc.gov", transport=httpx.MockTransport(handler)
    )
    return EVPClient(client=http)


@pytest.mark.unit
def test_fetch_records_fast_path_returns_filtered_records():
    with _client(FIXTURE.read_text(encoding="utf-8")) as client:
        records = client.fetch_records(repair=False)
    assert len(records) == 2
    assert all(r["EvpStatus"] == "Active" for r in records)


@pytest.mark.unit
def test_fetch_records_raises_on_drift_without_repair():
    payload = html.escape(json.dumps([{"Name": "X", "EvpStatus": "Pending"}]))
    drifted = f'<html><script>var data = "{payload}";</script></html>'
    with _client(drifted) as client, pytest.raises(RuntimeError, match="drifted"):
        client.fetch_records(repair=False)
