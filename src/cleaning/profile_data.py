#!/usr/bin/env python3
"""
Profile datasets (no mutation): counts, missingness, zeros, basic stats.
Writes per-file summaries + a combined summary CSV and simple metadata JSON.

Copyright © 2026 Wolfgang Sanyer
Licensed under the Polyform Noncommercial License 1.0.0 (see LICENSE).
"""

import argparse
import json
import re
from pathlib import Path
import pandas as pd


def snake(name: str) -> str:
    s = re.sub(r"[^\w]+", "_", name.strip()).lower()
    return re.sub(r"__+", "_", s).strip("_")


def profile_one(path: Path, id_col: str | None):
    # load
    if path.suffix.lower() in {".xlsx", ".xls"}:
        df = pd.read_excel(path)
    else:
        df = pd.read_csv(path)

    # normalize headers
    df.columns = [snake(c) for c in df.columns]

    # --- build summaries safely ---
    num_df = df.select_dtypes(include="number")
    obj_df = df.select_dtypes(exclude="number")

    # numeric: full stats
    if not num_df.empty:
        num_stats = num_df.agg(
            ["count", "nunique", "min", "max", "mean", "std"]).T
    else:
        num_stats = pd.DataFrame()

    # non-numeric: only count & nunique
    if not obj_df.empty:
        obj_stats = obj_df.agg(["count", "nunique"]).T
    else:
        obj_stats = pd.DataFrame()

    # missingness for all cols
    miss = df.isna().sum().rename("n_missing")
    pct_miss = (miss / len(df) * 100).rename("pct_missing")

    # zeros only for numeric
    zero = (num_df == 0).sum().rename(
        "n_zero") if not num_df.empty else pd.Series(dtype="int64")

    # combine: start with counts for all columns
    base = pd.concat([miss, pct_miss], axis=1)

    # bring in numeric extras where available
    if not num_stats.empty:
        base = base.join(
            num_stats[["count", "nunique", "min", "max", "mean", "std"]], how="left")
    if not obj_stats.empty:
        # ensure we don't overwrite numeric stats; fill counts for object-only cols
        base = base.combine_first(obj_stats[["count", "nunique"]])

    # finally add zero counts for numeric columns
    if not zero.empty:
        base = base.join(zero, how="left")

    summary = base
    summary.index.name = "column"

    # high-level file meta
    info = {
        "file": path.name,
        "rows": int(len(df)),
        "columns": int(len(df.columns)),
    }
    if id_col and id_col in df.columns:
        info["unique_ids"] = int(df[id_col].nunique(dropna=True))

    return summary, info


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
