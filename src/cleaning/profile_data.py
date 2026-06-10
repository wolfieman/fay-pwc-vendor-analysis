#!/usr/bin/env python3
"""
Profile datasets (no mutation): counts, missingness, zeros, basic stats.
Writes per-file summaries + a combined summary CSV and simple metadata JSON.

Copyright © 2026 Wolfgang Sanyer
Licensed under the Polyform Noncommercial License 1.0.0 (see LICENSE).
"""

import argparse
import json
from pathlib import Path

import pandas as pd

from vendorscope.profiling import profile_dataframe


def profile_one(path: Path, id_col: str | None):
    if path.suffix.lower() in {".xlsx", ".xls"}:
        df = pd.read_excel(path)
    else:
        df = pd.read_csv(path)
    return profile_dataframe(df, id_col, name=path.name)


def main():
    ap = argparse.ArgumentParser(description="Profile datasets (no mutation).")
    ap.add_argument("--files", nargs="+", required=True,
                    help="Paths to files (csv/xlsx).")
    ap.add_argument("--id-col", default=None,
                    help="Optional ID column name (after header normalization).")
    ap.add_argument("--outdir", default="data/processed",
                    help="Output directory for summaries.")
    args = ap.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    combined_rows = []
    meta = []

    for f in args.files:
        p = Path(f)
        summary, info = profile_one(p, args.id_col)
        # per-file summary
        summary.reset_index().to_csv(
            outdir / f"{p.stem}-profile-summary.csv", index=False)
        # for combined view
        s2 = summary.reset_index()
        s2.insert(0, "file", p.name)
        combined_rows.append(s2)
        meta.append(info)

    if combined_rows:
        all_summary = pd.concat(combined_rows, ignore_index=True)
        all_summary.to_csv(outdir / "pwc-profile-summary.csv", index=False)

    with open(outdir / "pwc-profile-meta.json", "w", encoding="utf-8") as fh:
        json.dump(meta, fh, indent=2)

    print(f"Profile written to: {outdir}")


if __name__ == "__main__":
    main()
