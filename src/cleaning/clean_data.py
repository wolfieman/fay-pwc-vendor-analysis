#!/usr/bin/env python3
"""
clean_data.py — Standardize a single dataset: snake_case headers, trim strings,
normalize common Y/N booleans, and add is_missing / is_zero flags for numeric columns.
No imputation. Writes a cleaned CSV plus a QA missingness summary to --outdir.

Copyright © 2026 Wolfgang Sanyer
Licensed under the Polyform Noncommercial License 1.0.0 (see LICENSE).
"""
import argparse
import re
from pathlib import Path
import pandas as pd


def snake(name: str) -> str:
    s = re.sub(r"[^\w]+", "_", name.strip()).lower()
    return re.sub(r"__+", "_", s).strip("_")


YN_MAP = {"y": True, "yes": True, "n": False,
          "no": False, "true": True, "false": False}


def normalize(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [snake(c) for c in df.columns]
    # trim strings
    for c in df.select_dtypes(include=["object", "str"]).columns:
        df[c] = df[c].astype(str).str.strip()
    # normalize common booleans if present
    for c in ("active_status", "utilities_yn", "hub_status"):
        if c in df.columns:
            df[c] = df[c].map(lambda x: YN_MAP.get(str(x).strip().lower(), x))
    # add flags for missing/zero on numeric
    num = df.select_dtypes("number").columns
    for c in num:
        df[f"{c}_is_missing"] = df[c].isna()
        df[f"{c}_is_zero"] = df[c].eq(0)
    return df


def read_any(p: Path) -> pd.DataFrame:
    return pd.read_excel(p) if p.suffix.lower() in {".xlsx", ".xls"} else pd.read_csv(p)


def main():
    ap = argparse.ArgumentParser(
        description="Standardize columns & flags (no imputation).")
    ap.add_argument("--input", required=True,
                    help="Path to a single source file (csv/xlsx).")
    ap.add_argument(
        "--outdir", default="data/processed", help="Output directory.")
    args = ap.parse_args()

    src = Path(args.input)
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    df = read_any(src)
    df = normalize(df)

    # quick QA summary
    qa = pd.DataFrame({
        "column": df.columns,
        "n_missing": df.isna().sum().values
    })
    qa.to_csv(outdir / f"{src.stem}-qa-summary.csv", index=False)

    # write sanitized copy
    out_path_csv = outdir / f"{src.stem}-clean.csv"
    df.to_csv(out_path_csv, index=False)
    print(f"Wrote {out_path_csv}")


if __name__ == "__main__":
    main()
