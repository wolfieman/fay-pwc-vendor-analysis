#!/usr/bin/env python3
"""
make_audit.py — Summarize data quality from a profile-summary CSV (produced by
profile_data.py): average % missing per file and the top-N most-missing columns.
Writes a Markdown audit report. Run profile_data.py first.

Copyright © 2026 Wolfgang Sanyer
Licensed under the Polyform Noncommercial License 1.0.0 (see LICENSE).
"""
import argparse
from pathlib import Path
import pandas as pd


def build_report(df: pd.DataFrame, top_n: int = 10) -> str:
    by_file = (
        df.groupby("file")["pct_missing"]
          .mean().round(1).reset_index()
          .rename(columns={"pct_missing": "avg_pct_missing"})
    )
    top_missing = (
        df.groupby(["file", "column"])["pct_missing"]
          .mean().reset_index()
          .sort_values("pct_missing", ascending=False)
          .head(top_n)
    )

    def md_block(title: str, frame: pd.DataFrame) -> str:
        return f"## {title}\n\n```\n{frame.to_string(index=False)}\n```\n"

    return "".join([
        "# Data Audit Summary\n\n",
        md_block("Completeness by File (avg % missing)", by_file),
        md_block(f"Top {top_n} Columns by Missingness", top_missing),
        "## Observations & Next Actions\n\n",
        "- The highest-missingness columns above are the priority data-quality gaps.\n",
        "- Treat high-missing categorical fields as 'Unknown' rather than dropping rows.\n",
        "- No imputation is applied here; missing values are left as NA for downstream decisions.\n",
    ])


def main():
    ap = argparse.ArgumentParser(
        description="Build a Markdown data-audit summary from a profile-summary CSV.")
    ap.add_argument("--summary", default="data/processed/pwc-profile-summary.csv",
                    help="Profile-summary CSV produced by profile_data.py.")
    ap.add_argument("--out", default="data/processed/data_audit.md",
                    help="Output Markdown path.")
    ap.add_argument("--top-n", type=int, default=10,
                    help="How many most-missing columns to list.")
    args = ap.parse_args()

    summary_path = Path(args.summary)
    if not summary_path.exists():
        raise FileNotFoundError(
            f"Missing: {summary_path}. Run profile_data.py first.")

    df = pd.read_csv(summary_path)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(build_report(df, args.top_n), encoding="utf-8")
    print(f"Wrote audit summary to {out}")


if __name__ == "__main__":
    main()
