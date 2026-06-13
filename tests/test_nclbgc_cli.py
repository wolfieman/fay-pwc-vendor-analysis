"""NCLBGC CLI subcommands: acquire-nclbgc, profile-nclbgc, clean-nclbgc (offline).

Copyright © 2026 Wolfgang Sanyer
Licensed under the Polyform Noncommercial License 1.0.0 (see LICENSE).
"""

import json
from pathlib import Path
from urllib.parse import parse_qs

import httpx
import pytest

from vendorscope import cli, nclbgc_parse, tabular

FIXTURES = Path(__file__).parent / "fixtures" / "nclbgc"


def _read(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def _transport() -> httpx.MockTransport:
    result = (FIXTURES / "search-result.html").read_bytes()
    empty = (FIXTURES / "search-empty.html").read_bytes()
    detail = (FIXTURES / "detail.html").read_bytes()
    quals = (FIXTURES / "qualifiers.html").read_bytes()
    matters = (FIXTURES / "matters-empty.html").read_bytes()

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if request.method == "GET" and path == "/":
            return httpx.Response(200, text="ok")
        if request.method == "POST" and path == "/Public/_Search/":
            body = parse_qs(request.content.decode())
            account = (body.get("AccountNumber") or [""])[0]
            company = (body.get("CompanyName") or [""])[0]
            if account == "68764" or company:
                return httpx.Response(200, content=result)
            return httpx.Response(200, content=empty)
        if "_ShowAccountDetails" in path:
            return httpx.Response(200, content=detail)
        if "_ShowAccountQualifiers" in path:
            return httpx.Response(200, content=quals)
        if "_ShowNCLBGCPublicMatters" in path:
            return httpx.Response(200, content=matters)
        return httpx.Response(404)

    return httpx.MockTransport(handler)


@pytest.mark.contract
def test_acquire_nclbgc_freezes_a_run(tmp_path: Path) -> None:
    # stage a minimal slice-1 deliverable to drive the lookup
    tabular.write_csv(
        tmp_path / "evp-vendor-master-vendor-20260612.csv",
        [
            {
                "name": "A & D Enterprises, Inc.",
                "general_contractor_license_number": "68764",
            }
        ],
        columns=["name", "general_contractor_license_number"],
    )
    code = cli.run(
        ["acquire-nclbgc"],
        transport=_transport(),
        data_raw=tmp_path,
        data_processed=tmp_path,
    )
    assert code == 0
    runs = list((tmp_path / "nclbgc").glob("*-nclbgc"))
    assert len(runs) == 1
    records = json.loads((runs[0] / "nclbgc-licenses.json").read_text(encoding="utf-8"))
    assert records[0]["License_Number"] == "L.68764"


@pytest.mark.contract
def test_clean_nclbgc_writes_license_pair_without_red_columns(tmp_path: Path) -> None:
    run_id = "20260612T010101-nclbgc"
    run_dir = tmp_path / "nclbgc" / run_id
    run_dir.mkdir(parents=True)
    record = nclbgc_parse.decode_record(_read("detail.html"), _read("qualifiers.html"))
    (run_dir / "nclbgc-licenses.json").write_text(
        json.dumps([record]), encoding="utf-8"
    )

    code = cli.run(
        ["clean-nclbgc", "--run-id", run_id], data_raw=tmp_path, data_processed=tmp_path
    )
    assert code == 0
    master = tabular.read_csv(tmp_path / "nclbgc-license-master-20260612.csv")
    assert "phone" not in master[0] and "qualifier_name" not in master[0]
    assert master[0]["license_number"] == "68764"  # L. sigil stripped at clean
    contacts = tabular.read_csv(tmp_path / "nclbgc-license-contacts-20260612.csv")
    assert set(contacts[0]) == {"row_key", "phone", "qualifier_name"}


@pytest.mark.contract
def test_profile_nclbgc_writes_values_free_profile(tmp_path: Path) -> None:
    run_id = "20260612T020202-nclbgc"
    run_dir = tmp_path / "nclbgc" / run_id
    run_dir.mkdir(parents=True)
    record = nclbgc_parse.decode_record(_read("detail.html"), _read("qualifiers.html"))
    (run_dir / "nclbgc-licenses.json").write_text(
        json.dumps([record]), encoding="utf-8"
    )

    code = cli.run(
        ["profile-nclbgc", "--run-id", run_id],
        data_raw=tmp_path,
        data_processed=tmp_path,
    )
    assert code == 0
    report = json.loads(
        (tmp_path / "profile" / "nclbgc-license-profile-20260612.json").read_text(
            encoding="utf-8"
        )
    )
    assert report["record_count"] == 1
    assert "Status" in report["vocabularies"]  # white vocab column profiled
    # red columns report counts only, never values
    assert set(report["red_columns"]) == {"Phone", "Qualifier_Name"}
    assert set(report["red_columns"]["Phone"]) == {"nonblank", "blank"}
