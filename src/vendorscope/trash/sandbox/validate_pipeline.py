"""Experimental end-to-end eVP -> NCLBGC GC-license validation pipeline.

Acquires the live eVP vendor list, then validates each vendor's general-
contractor license against the NCLBGC board (number -> exact name -> phonetic
name, with owner matching) via :mod:`vendorscope.sandbox.license_validation`,
and writes a per-vendor verdict report. The board is a validation oracle only --
no license detail is ingested here.

Sandbox code: a reproducible capture of the live-data validation work, still
being vetted. Run it deliberately -- it makes hundreds of live requests.

Copyright © 2026 Wolfgang Sanyer
Licensed under the Polyform Noncommercial License 1.0.0 (see LICENSE).
"""

import time
from pathlib import Path

import pandas as pd

from vendorscope.evp_client import EVPClient
from vendorscope.nclbgc_client import NCLBGCClient
from vendorscope.sandbox.license_validation import clean_gc_number, validate_vendor

_ROOT = Path(__file__).resolve().parents[3]
RAW_DIR = _ROOT / "data" / "raw" / "sandbox"
PROCESSED_DIR = _ROOT / "data" / "processed" / "sandbox"
NAME_COL = "Name"
GC_COL = "GeneralContractorLicenseNumber"


def acquire_evp(out_path: Path | None = None) -> pd.DataFrame:
    """Fetch the live eVP vendor list and, when given a path, save it as raw."""
    with EVPClient() as client:
        records = client.fetch_records()
    df = pd.DataFrame(records)
    if out_path is not None:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(out_path, index=False)
    return df


def route_vendors(df: pd.DataFrame) -> pd.DataFrame:
    """Stage A: classify each GC number into a search route (no network)."""
    rows = [
        {"name": name, "gc_raw": raw} | _routed(raw)
        for name, raw in zip(df[NAME_COL], df[GC_COL], strict=True)
    ]
    return pd.DataFrame(rows)


def _routed(raw: str) -> dict[str, str]:
    clean, category, route = clean_gc_number(raw)
    return {"gc_clean": clean, "category": category, "route": route}


def validate_vendors(
    client: NCLBGCClient, df: pd.DataFrame, *, delay: float = 0.3
) -> pd.DataFrame:
    """Stage B: validate every vendor's GC license against the board (live)."""
    out = []
    for name, raw in zip(df[NAME_COL], df[GC_COL], strict=True):
        v = validate_vendor(client, name, raw)
        out.append(
            {
                "name": name,
                "gc_raw": raw,
                "gc_clean": v.gc_clean,
                "category": v.category,
                "verdict": v.verdict,
                "via": v.via,
                "board_account": v.board_account,
                "board_owner": v.board_owner,
            }
        )
        time.sleep(delay)
    return pd.DataFrame(out)


def main() -> None:
    """Acquire -> validate -> write the verdict report under data/processed/sandbox."""
    df = acquire_evp(RAW_DIR / "vendor-details-evp-nc-latest.csv")
    with NCLBGCClient() as client:
        report = validate_vendors(client, df)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    out = PROCESSED_DIR / "license-validation-report.csv"
    report.to_csv(out, index=False)
    counts = report["verdict"].value_counts().to_dict()
    print(f"validated {len(report)} vendors -> {counts}")
    print(f"report: {out}")


if __name__ == "__main__":
    main()
