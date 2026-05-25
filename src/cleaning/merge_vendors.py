#!/usr/bin/env python3
"""
merge_vendors.py — Merge multiple vendor lists (HUB, master, PWC) into a single
source-of-truth keyed on a canonicalized vendor name, with per-source presence flags.
Writes a GitHub-safe sample + QA counts to --outdir (full SSOT optional via --full-xlsx).
"""
import argparse
import re
from pathlib import Path
import pandas as pd


def snake(s: str) -> str:
    s = re.sub(r"[^\w]+", "_", s.strip()).lower()
    return re.sub(r"__+", "_", s).strip("_")


def canon_vendor(v: str) -> str:
    if pd.isna(v):
        return ""
    v = str(v).upper().strip()
    v = re.sub(r"[^\w\s]", "", v)           # remove punctuation
    v = re.sub(r"\s+", " ", v)              # collapse spaces
    return v


def load_norm(path: Path, vendor_cols=("vendor_name", "vendor")):
    # read csv/xlsx
    if path.suffix.lower() in {".xlsx", ".xls"}:
        df = pd.read_excel(path)
    else:
        df = pd.read_csv(path)

    # normalize headers
    df.columns = [snake(c) for c in df.columns]

    # pick best vendor column
    vcol = next((c for c in vendor_cols if c in df.columns), None)
    if vcol is None:
        # fallback: first object column
        vcol = df.select_dtypes(include=["object", "str"]).columns[0]

    df["vendor_key"] = df[vcol].map(canon_vendor)

    # keep a minimal, consistent set of columns
    keep = [
        c for c in df.columns
        if c in {"vendor_key", "active_status", "industry", "utilities_yn", "hub_status", "license_number"}
    ]
    return df[keep].copy()


def main():
    ap = argparse.ArgumentParser(
        description="Merge HUB, Master, PWC lists into a vendor SSOT (with source flags)."
    )
    ap.add_argument("--hub", required=True)
    ap.add_argument("--master", required=True)
    ap.add_argument("--pwc", required=True)
    ap.add_argument("--outdir", default="data/processed")
    ap.add_argument("--full-xlsx", default=None,
                    help="Optional path (e.g., Teams) to write full SSOT Excel.")
    args = ap.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    # load & tag sources
    df_hub = load_norm(Path(args.hub))
    df_hub["in_hub"] = True
    df_mas = load_norm(Path(args.master))
    df_mas["in_master"] = True
    df_pwc = load_norm(Path(args.pwc))
    df_pwc["in_pwc"] = True

    # stack, then aggregate to one row per vendor_key
    merged = pd.concat([df_hub, df_mas, df_pwc], ignore_index=True)

    # --- Merge and aggregate vendor records ---
    merged = (
        merged.groupby("vendor_key", as_index=False)
              .agg(lambda s: s.ffill().bfill().iloc[0] if s.notna().any() else None)
    )

    # infer correct dtypes (prevents FutureWarning about silent downcasting)
    merged = merged.infer_objects(copy=False)

    # ensure source flags exist and are boolean
    for f in ("in_hub", "in_master", "in_pwc"):
        if f not in merged.columns:
            merged[f] = False
        merged[f] = merged[f].fillna(False).astype(bool)

    # Small, GitHub-safe sample (first 200)
    sample = merged.head(200)
    sample.to_csv(outdir / "pwc-vendors-ssot-sample.csv", index=False)

    # QA counts
    qa = pd.DataFrame({
        "total_unique_vendors": [len(merged)],
        "in_hub": [merged["in_hub"].sum()],
        "in_master": [merged["in_master"].sum()],
        "in_pwc": [merged["in_pwc"].sum()],
    })
    qa.to_csv(outdir / "pwc-vendors-qa-summary.csv", index=False)

    # Optional full Excel (Teams / shared location)
    if args.full_xlsx:
        merged.to_excel(args.full_xlsx, index=False)
        print(f"Full SSOT written to {args.full_xlsx}")

    print(f"Sample + QA written to {outdir}")


if __name__ == "__main__":
    main()
