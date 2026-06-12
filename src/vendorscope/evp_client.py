"""Acquire shell: one GET of the saved-search results page, raw frozen first.

The order is load-bearing (REQ-05): the verbatim response bytes are written
before anything can fail; then the page is parsed and the decoded JSON plus a
checksum manifest are written; only then are the gating checks consulted (the
read-time column manifest, then drift detection). The drift report is written
separately, after detection, and a drift alarm halts the run loudly, naming the
manual runbook (REQ-04). A template change raises ``EmbeddedDataError`` from the
parser with the raw bytes already frozen for forensics.

Copyright © 2026 Wolfgang Sanyer
Licensed under the Polyform Noncommercial License 1.0.0 (see LICENSE).
"""

import hashlib
import json
import time
from dataclasses import dataclass
from pathlib import Path

import httpx

from . import drift, evp_parse, tabular
from .cleaning import config

RUNBOOK = "docs/runbook-evp-drift.md"


class DriftHalt(RuntimeError):
    """Acquire detected drift and refuses to proceed; consult the runbook."""


@dataclass(frozen=True, slots=True)
class AcquireResult:
    run_id: str
    raw_dir: Path
    record_count: int
    alarms: list[drift.DriftAlarm]


def acquire(
    *,
    client: httpx.Client,
    data_raw: Path,
    run_id: str,
    url: str = config.RESULTS_URL,
    floor: int = config.RECORD_FLOOR,
) -> AcquireResult:
    """Fetch, freeze raw, then gate on manifest and drift; halt loudly on drift."""
    raw_dir = data_raw / "evp" / run_id
    raw_dir.mkdir(parents=True, exist_ok=True)

    response = client.get(url)
    response.raise_for_status()
    page_bytes = response.content
    # (1) verbatim bytes first — before any parse or check can abort
    (raw_dir / "vendordetails-page-1.html").write_bytes(page_bytes)

    page = page_bytes.decode("utf-8", errors="replace")
    records = evp_parse.parse_records(page)  # raises EmbeddedDataError on template miss

    # (2) decoded JSON + checksum manifest, still before any gating check.
    # Write exact bytes (not write_text) so the on-disk checksum is reproducible
    # and unaffected by platform newline translation.
    json_bytes = json.dumps(records, indent=1, ensure_ascii=False).encode("utf-8")
    (raw_dir / "evp-vendors.json").write_bytes(json_bytes)
    manifest = {
        "run_id": run_id,
        "url": url,
        "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "sha256_html": hashlib.sha256(page_bytes).hexdigest(),
        "sha256_json": hashlib.sha256(json_bytes).hexdigest(),
        "record_count": len(records),
        "client": "vendorscope/0.2",
    }
    (raw_dir / "acquire-manifest.json").write_bytes(
        json.dumps(manifest, indent=1).encode("utf-8")
    )

    # (3) gating checks — raw is now safely frozen
    tabular.assert_manifest(records[0].keys())
    alarms = drift.evaluate(page, records, floor=floor)
    (raw_dir / "drift-report.json").write_text(
        json.dumps([{"kind": a.kind, "detail": a.detail} for a in alarms], indent=1),
        encoding="utf-8",
    )
    if alarms:
        summary = "; ".join(a.kind for a in alarms)
        raise DriftHalt(
            f"eVP filter drift detected ({summary}). Run halted; do not trust this "
            f"pull. Follow {RUNBOOK} to inspect and repair, then re-acquire."
        )

    return AcquireResult(run_id, raw_dir, len(records), alarms)
