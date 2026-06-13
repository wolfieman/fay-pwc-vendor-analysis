"""Acquire shell: license-first + name-fallback, raw frozen first (slice 2).

Offline via an injected httpx mock transport that routes by request (the search
POST body decides license-hit / license-miss / name-hit / name-miss); no live
request, no ``data/`` access.

Copyright © 2026 Wolfgang Sanyer
Licensed under the Polyform Noncommercial License 1.0.0 (see LICENSE).
"""

import hashlib
import json
from pathlib import Path
from urllib.parse import parse_qs

import httpx
import pytest

from vendorscope import http_client, nclbgc_client

FIXTURES = Path(__file__).parent / "fixtures" / "nclbgc"


def _bytes(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


def _transport() -> httpx.MockTransport:
    pages = {
        n: _bytes(n)
        for n in (
            "search-result.html",
            "search-empty.html",
            "detail.html",
            "qualifiers.html",
            "matters-empty.html",
        )
    }

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if request.method == "GET" and path == "/":
            return httpx.Response(200, text="<html>primed</html>")
        if request.method == "POST" and path == "/Public/_Search/":
            body = parse_qs(request.content.decode())
            account = (body.get("AccountNumber") or [""])[0]
            company = (body.get("CompanyName") or [""])[0]
            if account == "68764":  # the one known license number resolves
                return httpx.Response(200, content=pages["search-result.html"])
            if account:  # any other number misses
                return httpx.Response(200, content=pages["search-empty.html"])
            if company and "Unfindable" not in company:  # name resolves unless ghost
                return httpx.Response(200, content=pages["search-result.html"])
            return httpx.Response(200, content=pages["search-empty.html"])
        if "_ShowAccountDetails" in path:
            return httpx.Response(200, content=pages["detail.html"])
        if "_ShowAccountQualifiers" in path:
            return httpx.Response(200, content=pages["qualifiers.html"])
        if "_ShowNCLBGCPublicMatters" in path:
            return httpx.Response(200, content=pages["matters-empty.html"])
        return httpx.Response(404)

    return httpx.MockTransport(handler)


VENDORS = [
    {"name": "A & D Enterprises, Inc.", "license_number": "68764"},  # by license
    {"name": "Findable By Name LLC", "license_number": "99999"},  # license miss -> name
    {"name": "Out Of State Co", "license_number": "WV063716"},  # flagged -> name
    {"name": "Unfindable Ghost LLC", "license_number": ""},  # neither -> unresolved
]


def _acquire(tmp: Path) -> nclbgc_client.AcquireResult:
    client = http_client.build_client(transport=_transport())
    try:
        return nclbgc_client.acquire(
            client=client,
            data_raw=tmp,
            run_id="20260612T000000-nclbgc",
            vendors=VENDORS,
            delay=0.0,
        )
    finally:
        client.close()


@pytest.mark.contract
def test_resolution_statuses(tmp_path: Path) -> None:
    result = _acquire(tmp_path)
    assert [r.status for r in result.resolutions] == [
        "matched-by-license",
        "matched-by-name",
        "matched-by-name",
        "unresolved",
    ]
    assert result.record_count == 3


@pytest.mark.contract
def test_flagged_license_goes_straight_to_name(tmp_path: Path) -> None:
    # the WV (non-digit) license is never searched by number; it resolves by name
    wv = _acquire(tmp_path).resolutions[2]
    assert wv.license_number == "WV063716"
    assert wv.status == "matched-by-name"


@pytest.mark.contract
def test_resolution_carries_discovered_license(tmp_path: Path) -> None:
    # issue #27: the vendor -> discovered-license linkage must be persisted, so
    # slice 3 can reconcile a name-matched vendor (whose eVP license was blank or
    # wrong) to the board-confirmed license. Every matched vendor carries the
    # decoded License_Number; an unresolved vendor carries "".
    result = _acquire(tmp_path)
    assert [r.discovered_license for r in result.resolutions] == [
        "L.68764",
        "L.68764",
        "L.68764",
        "",
    ]
    report = json.loads(
        (result.raw_dir / "resolution-report.json").read_text(encoding="utf-8")
    )
    name_match = next(e for e in report if e["status"] == "matched-by-name")
    assert name_match["discovered_license"] == "L.68764"


@pytest.mark.contract
def test_raw_frozen_and_reparsable(tmp_path: Path) -> None:
    result = _acquire(tmp_path)
    raw = result.raw_dir
    json_bytes = (raw / "nclbgc-licenses.json").read_bytes()
    records = json.loads(json_bytes)
    assert len(records) == 3
    assert records[0]["License_Number"] == "L.68764"  # re-parsable offline
    manifest = json.loads((raw / "acquire-manifest.json").read_text(encoding="utf-8"))
    assert manifest["sha256_json"] == hashlib.sha256(json_bytes).hexdigest()
    assert manifest["record_count"] == 3
    report = json.loads((raw / "resolution-report.json").read_text(encoding="utf-8"))
    assert sum(1 for entry in report if entry["status"] == "unresolved") == 1
