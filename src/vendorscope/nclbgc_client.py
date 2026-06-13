"""Acquire shell: NCLBGC license enrichment, raw frozen before any decode.

For each slice-1 vendor the client resolves a board record **license-number
first, then a normalized-name fallback** (methodology section 1): a by-number hit
is itself the confirmation that the number matched. A slice-1-flagged number
(out-of-state, prefixed, blank — anything not a bare NC digit string) skips the
number search and goes straight to name. A vendor that resolves by neither is
recorded as ``unresolved`` and never dropped; the downstream validation slice
excludes it. On a hit the detail, qualifiers, and public-matters fragments are
fetched per opaque key, frozen verbatim, then decoded into one flat record.

Mirrors slice 1's discipline: verbatim bytes land before any decode, and the
decoded JSON plus a checksum manifest are written with reproducible bytes. The
client is the only network code; the transport is injectable for offline tests.
There is no drift detector — NCLBGC has no shared filter to drift.

Copyright © 2026 Wolfgang Sanyer
Licensed under the Polyform Noncommercial License 1.0.0 (see LICENSE).
"""

import hashlib
import json
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

import httpx

from . import nclbgc_parse
from .cleaning import config

_SEARCH_HEADERS = {"x-requested-with": "XMLHttpRequest"}


@dataclass(frozen=True, slots=True)
class Resolution:
    """How one slice-1 vendor resolved against the board."""

    index: int
    license_number: str
    name: str
    status: str  # matched-by-license | matched-by-name | unresolved
    key: str | None


@dataclass(frozen=True, slots=True)
class AcquireResult:
    run_id: str
    raw_dir: Path
    record_count: int
    resolutions: list[Resolution]


def _search(
    client: httpx.Client, *, account_number: str = "", company_name: str = ""
) -> tuple[list[str], str]:
    body: dict[str, str] = dict.fromkeys(config.NCLBGC_SEARCH_FIELDS, "")
    body["AccountNumber"] = account_number
    body["CompanyName"] = company_name
    response = client.post(config.NCLBGC_SEARCH_URL, data=body, headers=_SEARCH_HEADERS)
    response.raise_for_status()
    return nclbgc_parse.parse_search_keys(response.text), response.text


def resolve(
    client: httpx.Client, *, name: str, license_number: str
) -> tuple[str, str | None, str]:
    """License-number first, then a name fallback; returns the search HTML."""
    last_html = ""
    if license_number.isdigit():  # a bare NC digit string; flagged numbers fall through
        keys, last_html = _search(client, account_number=license_number)
        if keys:
            return "matched-by-license", keys[0], last_html
    if name.strip():
        keys, last_html = _search(client, company_name=name)
        if keys:
            return "matched-by-name", keys[0], last_html
    return "unresolved", None, last_html


def _fetch(client: httpx.Client, path: str, key: str) -> httpx.Response:
    response = client.get(config.NCLBGC_BASE + path.format(key=key))
    response.raise_for_status()
    return response


def acquire(
    *,
    client: httpx.Client,
    data_raw: Path,
    run_id: str,
    vendors: Sequence[Mapping[str, str]],
    delay: float = config.NCLBGC_DELAY,
) -> AcquireResult:
    """Resolve and enrich each vendor; freeze raw first; report resolutions."""
    raw_dir = data_raw / "nclbgc" / run_id
    raw_dir.mkdir(parents=True, exist_ok=True)
    client.get(config.NCLBGC_BASE + "/")  # prime a session cookie

    width = max(len(str(len(vendors) - 1)), 1)
    records: list[dict[str, str]] = []
    resolutions: list[Resolution] = []

    for index, vendor in enumerate(vendors):
        if index:
            time.sleep(delay)  # politeness between vendors (REQ-18)
        name = vendor.get("name", "")
        license_number = vendor.get("license_number", "")
        status, key, search_html = resolve(
            client, name=name, license_number=license_number
        )
        tag = f"{index:0{width}d}"
        (raw_dir / f"search-{tag}.html").write_text(search_html, encoding="utf-8")
        resolutions.append(Resolution(index, license_number, name, status, key))
        if key is None:
            continue
        # raw-first: freeze each fragment verbatim before decoding
        detail = _fetch(client, config.NCLBGC_DETAIL_PATH, key)
        qualifiers = _fetch(client, config.NCLBGC_QUALIFIERS_PATH, key)
        matters = _fetch(client, config.NCLBGC_MATTERS_PATH, key)
        (raw_dir / f"detail-{tag}.html").write_bytes(detail.content)
        (raw_dir / f"qualifiers-{tag}.html").write_bytes(qualifiers.content)
        (raw_dir / f"matters-{tag}.html").write_bytes(matters.content)
        records.append(nclbgc_parse.decode_record(detail.text, qualifiers.text))

    json_bytes = json.dumps(records, indent=1, ensure_ascii=False).encode("utf-8")
    (raw_dir / "nclbgc-licenses.json").write_bytes(json_bytes)
    manifest = {
        "run_id": run_id,
        "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "sha256_json": hashlib.sha256(json_bytes).hexdigest(),
        "record_count": len(records),
        "vendor_count": len(vendors),
        "client": "vendorscope/0.3",
    }
    (raw_dir / "acquire-manifest.json").write_bytes(
        json.dumps(manifest, indent=1).encode("utf-8")
    )
    report = [
        {"index": r.index, "license_number": r.license_number, "status": r.status}
        for r in resolutions
    ]
    (raw_dir / "resolution-report.json").write_bytes(
        json.dumps(report, indent=1).encode("utf-8")
    )

    return AcquireResult(run_id, raw_dir, len(records), resolutions)
