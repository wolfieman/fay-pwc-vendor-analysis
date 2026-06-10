"""Dataset standardization and profiling. Pure transforms over a DataFrame:
snake-case headers, Y/N + missing/zero flags, and per-column missingness,
zeros, and basic statistics. File IO lives in the calling scripts.

Copyright © 2026 Wolfgang Sanyer
Licensed under the Polyform Noncommercial License 1.0.0 (see LICENSE).
"""

import pandas as pd

from vendorscope.text import snake

YN_MAP = {"y": True, "yes": True, "n": False, "no": False, "true": True, "false": False}


def normalize(df: pd.DataFrame) -> pd.DataFrame:
    """Snake-case headers, trim strings, map Y/N booleans, add missing/zero flags."""
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


def profile_dataframe(
    df: pd.DataFrame, id_col: str | None = None, *, name: str = ""
) -> tuple[pd.DataFrame, dict]:
    """Profile a DataFrame: missingness, zeros, and basic stats per column.

    Args:
        df: Data to profile; headers are snake-cased on a copy (input is not mutated).
        id_col: Optional ID column (post-normalization) whose unique count is recorded.
        name: File/source label stored in the returned metadata.

    Returns:
        A (summary, info) pair: the per-column summary frame and a metadata dict.
    """
    df = df.copy()
    df.columns = [snake(c) for c in df.columns]

    num_df = df.select_dtypes(include="number")
    obj_df = df.select_dtypes(exclude="number")

    if not num_df.empty:
        num_stats = num_df.agg(["count", "nunique", "min", "max", "mean", "std"]).T
    else:
        num_stats = pd.DataFrame()

    if not obj_df.empty:
        obj_stats = obj_df.agg(["count", "nunique"]).T
    else:
        obj_stats = pd.DataFrame()

    miss = df.isna().sum().rename("n_missing")
    pct_miss = (miss / len(df) * 100).rename("pct_missing")

    zero = (
        (num_df == 0).sum().rename("n_zero")
        if not num_df.empty
        else pd.Series(dtype="int64")
    )

    base = pd.concat([miss, pct_miss], axis=1)

    if not num_stats.empty:
        base = base.join(
            num_stats[["count", "nunique", "min", "max", "mean", "std"]], how="left"
        )
    if not obj_stats.empty:
        # don't overwrite numeric stats; fill counts for object-only columns
        base = base.combine_first(obj_stats[["count", "nunique"]])

    if not zero.empty:
        base = base.join(zero, how="left")

    summary = base
    summary.index.name = "column"

    info = {
        "file": name,
        "rows": int(len(df)),
        "columns": int(len(df.columns)),
    }
    if id_col and id_col in df.columns:
        info["unique_ids"] = int(df[id_col].nunique(dropna=True))

    return summary, info
