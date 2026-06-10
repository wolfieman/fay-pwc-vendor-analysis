"""Audit-report rendering: turn a profile-summary frame into a Markdown summary.

Copyright © 2026 Wolfgang Sanyer
Licensed under the Polyform Noncommercial License 1.0.0 (see LICENSE).
"""

import pandas as pd


def build_report(df: pd.DataFrame, top_n: int = 10) -> str:
    """Render a Markdown data-audit summary from a profile-summary DataFrame."""
    by_file = (
        df.groupby("file")["pct_missing"]
        .mean()
        .round(1)
        .reset_index()
        .rename(columns={"pct_missing": "avg_pct_missing"})
    )
    top_missing = (
        df.groupby(["file", "column"])["pct_missing"]
        .mean()
        .reset_index()
        .sort_values("pct_missing", ascending=False)
        .head(top_n)
    )

    def md_block(title: str, frame: pd.DataFrame) -> str:
        return f"## {title}\n\n```\n{frame.to_string(index=False)}\n```\n"

    return "".join(
        [
            "# Data Audit Summary\n\n",
            md_block("Completeness by File (avg % missing)", by_file),
            md_block(f"Top {top_n} Columns by Missingness", top_missing),
            "## Observations & Next Actions\n\n",
            "- The highest-missingness columns above are the priority data-quality gaps.\n",
            "- Treat high-missing categorical fields as 'Unknown' rather than dropping rows.\n",
            "- No imputation is applied here; missing values are left as NA for downstream decisions.\n",
        ]
    )
