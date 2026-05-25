#!/usr/bin/env python3
"""
list_columns.py — Print and optionally save column names from an Excel or CSV file.

Reads from data/raw by default; saves column lists to data/processed with --save.

Usage:
  python src/cleaning/list_columns.py                          # default vendor-details-evp-nc.xlsx
  python src/cleaning/list_columns.py nclbgc-license-details.xlsx
  python src/cleaning/list_columns.py some.xlsx --sheet 0 --save
  python src/cleaning/list_columns.py some.xlsx --list-sheets
  python src/cleaning/list_columns.py --datadir other/dir file.csv
"""

import argparse
from pathlib import Path
import sys
import pandas as pd

# Default locations (relative to repo root)
DEFAULT_DATA_DIR = "data/raw"
DEFAULT_OUT_DIR = "data/processed"
DEFAULT_FILE = "vendor-details-evp-nc.xlsx"


def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)


def parse_args():
    p = argparse.ArgumentParser(
        description="List dataset columns (Excel/CSV).")
    p.add_argument("filename", nargs="?", default=DEFAULT_FILE,
                   help=f"Filename inside --datadir (default: {DEFAULT_FILE})")
    p.add_argument("--datadir", default=DEFAULT_DATA_DIR,
                   help=f"Directory containing the file (default: {DEFAULT_DATA_DIR})")
    p.add_argument("--outdir", default=DEFAULT_OUT_DIR,
                   help=f"Where --save writes the column list (default: {DEFAULT_OUT_DIR})")
    p.add_argument("--sheet", help="Excel sheet name or index (0-based)")
    p.add_argument("--list-sheets", action="store_true",
                   help="List Excel sheets and exit")
    p.add_argument("--save", action="store_true",
                   help="Save the column list to --outdir")
    return p.parse_args()


def list_sheets(xlsx_path: Path):
    xl = pd.ExcelFile(xlsx_path)
    return xl.sheet_names


def load_columns(path: Path, sheet=None):
    suffix = path.suffix.lower()
    if suffix in [".xlsx", ".xls"]:
        if sheet is None:
            df = pd.read_excel(path, nrows=0)
        else:
            try:
                sheet_arg = int(sheet)
            except (TypeError, ValueError):
                sheet_arg = sheet
            df = pd.read_excel(path, sheet_name=sheet_arg, nrows=0)
    elif suffix == ".csv":
        try:
            df = pd.read_csv(path, nrows=0)
        except UnicodeDecodeError:
            df = pd.read_csv(path, nrows=0, encoding="latin-1")
    else:
        raise ValueError(f"Unsupported file type: {suffix}")
    return [str(c) for c in df.columns.tolist()]


def main():
    args = parse_args()
    path = Path(args.datadir) / args.filename

    if not path.exists():
        eprint(f"❌ File not found:\n{path}")
        sys.exit(1)

    if args.list_sheets:
        if path.suffix.lower() not in [".xlsx", ".xls"]:
            eprint("⚠️ --list-sheets applies only to Excel files.")
            sys.exit(2)
        sheets = list_sheets(path)
        print(f"📄 Sheets in {path.name}:")
        for i, s in enumerate(sheets):
            print(f"  {i}: {s}")
        sys.exit(0)

    try:
        cols = load_columns(path, sheet=args.sheet)
    except Exception as ex:
        eprint(f"❌ Error reading columns: {ex}")
        sys.exit(3)

    print(f"✅ Columns in {path.name}" +
          (f" (sheet={args.sheet})" if args.sheet else "") + ":")
    for i, c in enumerate(cols, 1):
        print(f"{i:02d}. {c}")

    if args.save:
        outdir = Path(args.outdir)
        outdir.mkdir(parents=True, exist_ok=True)
        out = outdir / f"{path.stem}-columns.txt"
        with open(out, "w", encoding="utf-8") as f:
            for c in cols:
                f.write(f"{c}\n")
        print(f"\n💾 Saved column list to: {out}")


if __name__ == "__main__":
    main()
