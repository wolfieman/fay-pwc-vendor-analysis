"""Offline unit tests for the NCLBGC httpx client.

Uses httpx.MockTransport to serve the saved fixtures, so the request-building and
key-handling are exercised without touching the network.

Copyright © 2026 Wolfgang Sanyer
Licensed under the Polyform Noncommercial License 1.0.0 (see LICENSE).
"""

from pathlib import Path

import httpx
import pytest

from vendorscope.nclbgc_client import NCLBGCClient

FIXTURES = Path(__file__).parent / "fixtures" / "nclbgc"


def _fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def _mock_client(seen: dict | None = None) -> NCLBGCClient:
    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if seen is not None:
            seen[path] = request
        if path == "/Public/Search":
            return httpx.Response(200, text="<html></html>")
        if path == "/Public/_Search/":
            return httpx.Response(200, text=_fixture("search.html"))
        if path == "/Public/_ShowAccountDetails/":
            return httpx.Response(200, text=_fixture("details.html"))
        if path == "/Public/_ShowAccountQualifiers/":
            return httpx.Response(200, text=_fixture("qualifiers.html"))
        return httpx.Response(404)

    http = httpx.Client(
        base_url="https://portal.nclbgc.org", transport=httpx.MockTransport(handler)
    )
    return NCLBGCClient(client=http)


@pytest.mark.unit
def test_search_posts_company_and_parses_rows():
    seen: dict = {}
    with _mock_client(seen) as client:
        rows = client.search(company="24North Investments LLC")
    assert rows[0]["license_number"] == "L.85168"
    body = seen["/Public/_Search/"].content.decode()
    assert "CompanyName=24North+Investments+LLC" in body


@pytest.mark.unit
def test_detail_decodes_key_before_requesting():
    seen: dict = {}
    with _mock_client(seen) as client:
        detail = client.detail("JTeHh5hHBoEZqYLA9I%2b%2bZw%3d%3d")
    assert detail["status"] == "Active"
    params = dict(seen["/Public/_ShowAccountDetails/"].url.params)
    assert params["key"] == "JTeHh5hHBoEZqYLA9I++Zw=="  # url-decoded once
    assert params["Source"] == "Search"


@pytest.mark.unit
def test_license_record_merges_detail_and_qualifiers():
    with _mock_client() as client:
        record = client.license_record("24North Investments LLC")
    assert record is not None
    assert record["license_number"] == "L.85168"
    assert record["detail"]["company_name"] == "24North Investments LLC"
    assert record["qualifiers"][0]["qualifier_number"] == "Q.11011"


@pytest.mark.unit
def test_license_record_none_when_no_results():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/Public/_Search/":
            return httpx.Response(200, text="<div>no table</div>")
        return httpx.Response(200, text="<html></html>")

    http = httpx.Client(
        base_url="https://portal.nclbgc.org", transport=httpx.MockTransport(handler)
    )
    with NCLBGCClient(client=http) as client:
        assert client.license_record("nobody at all") is None
