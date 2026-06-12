"""Acquire shell: raw frozen before any check, drift halts (REQ-04, REQ-05).

Offline via an injected httpx mock transport; no live request, no data/ access.

Copyright © 2026 Wolfgang Sanyer
Licensed under the Polyform Noncommercial License 1.0.0 (see LICENSE).
"""

import hashlib
import json
from pathlib import Path

import httpx
import pytest

from vendorscope import evp_client, http_client

FIXTURES = Path(__file__).parent / "fixtures" / "evp"


def _transport(name: str) -> httpx.MockTransport:
    body = (FIXTURES / name).read_bytes()

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=body)

    return httpx.MockTransport(handler)


def _acquire(name: str, tmp: Path, *, floor: int = 20):
    client = http_client.build_client(transport=_transport(name))
    try:
        return evp_client.acquire(
            client=client, data_raw=tmp, run_id="20260612T000000-evp", floor=floor
        )
    finally:
        client.close()


@pytest.mark.contract
def test_clean_pull_freezes_raw_with_matching_checksums(tmp_path: Path) -> None:
    result = _acquire("vendordetails-clean.html", tmp_path)
    raw = result.raw_dir
    html_bytes = (raw / "vendordetails-page-1.html").read_bytes()
    json_bytes = (raw / "evp-vendors.json").read_bytes()
    manifest = json.loads((raw / "acquire-manifest.json").read_text(encoding="utf-8"))

    assert result.record_count == 24
    assert manifest["sha256_html"] == hashlib.sha256(html_bytes).hexdigest()
    assert manifest["sha256_json"] == hashlib.sha256(json_bytes).hexdigest()
    # re-parsable offline from the frozen bytes
    assert json.loads(json_bytes)[0]["EvpStatus"] == "Active"
    assert result.alarms == []


@pytest.mark.contract
def test_drift_halts_but_raw_is_already_frozen(tmp_path: Path) -> None:
    with pytest.raises(evp_client.DriftHalt) as excinfo:
        _acquire("vendordetails-drift-nonactive.html", tmp_path)
    assert "runbook-evp-drift.md" in str(excinfo.value)
    raw = tmp_path / "evp" / "20260612T000000-evp"
    assert (raw / "vendordetails-page-1.html").is_file()
    assert (raw / "acquire-manifest.json").is_file()
    report = json.loads((raw / "drift-report.json").read_text(encoding="utf-8"))
    assert any(a["kind"] == "non-active-status" for a in report)


@pytest.mark.contract
def test_record_floor_breach_halts(tmp_path: Path) -> None:
    with pytest.raises(evp_client.DriftHalt):
        _acquire("vendordetails-clean.html", tmp_path, floor=500)


@pytest.mark.contract
def test_template_miss_raises_but_html_is_frozen(tmp_path: Path) -> None:
    from vendorscope import evp_parse

    with pytest.raises(evp_parse.EmbeddedDataError):
        _acquire("template-miss.html", tmp_path)
    raw = tmp_path / "evp" / "20260612T000000-evp"
    assert (raw / "vendordetails-page-1.html").is_file()
