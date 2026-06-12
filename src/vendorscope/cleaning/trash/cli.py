"""Command-line orchestrator — the imperative shell around the pure engine.

All file IO lives here and only here. Inputs are read entirely as text
(``dtype=str``) with pandas' NA-token guessing disabled, because identifier
columns must keep leading zeros and a county named "NA" is data, not a
missing value. The engine itself never touches a file.

Example:
    python -m vendorscope.cleaning.cli --vendor raw/vendors.csv \\
        --license raw/licenses.csv --out-dir cleaned --public

Copyright © 2026 Wolfgang Sanyer
Licensed under the Polyform Noncommercial License 1.0.0 (see LICENSE).
"""

import argparse
import sys
from pathlib import Path

import pandas as pd

from .config import CROSS_VALIDATION_CONFIG, LICENSE_CONFIG, VENDOR_CONFIG
from .pipeline import (
    CleanResult,
    clean_table,
    corrections_frame,
    cross_validate,
    violations_frame,
)
from .transforms import split_pii

# Dataset name -> its cleaning configuration. Registering a new source here
# (with its own TableConfig) is the entire onboarding step.
TABLE_REGISTRY = {
    "vendor": VENDOR_CONFIG,
    "license": LICENSE_CONFIG,
}


def read_table(path: Path) -> pd.DataFrame:
    """Read a CSV with every cell as text and NA-guessing disabled."""
    return pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8-sig")


def write_outputs(
    name: str,
    result: CleanResult,
    out_dir: Path,
    *,
    public: bool,
) -> None:
    """Write a cleaned table, splitting PII into a separate file if asked."""
    config = TABLE_REGISTRY[name]
    if public and config.pii_columns:
        public_frame, pii_frame = split_pii(result.frame, config.pii_columns)
        public_frame.to_csv(out_dir / f"{name}_public.csv", index_label="record_id")
        pii_frame.to_csv(out_dir / f"{name}_pii.csv", index_label="record_id")
    else:
        result.frame.to_csv(out_dir / f"{name}_clean.csv", index_label="record_id")


def main(argv: list[str] | None = None) -> int:
    """Clean the configured tables and write data plus audit trails."""
    parser = argparse.ArgumentParser(
        description="Clean vendor/licensing tables per the documented "
        "protocol and report all corrections and violations."
    )
    parser.add_argument(
        "--vendor", type=Path, help="Path to the raw vendor-master CSV."
    )
    parser.add_argument(
        "--license",
        dest="license_path",
        type=Path,
        help="Path to the raw license-details CSV.",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("cleaned"),
        help="Directory for cleaned files and audit logs.",
    )
    parser.add_argument(
        "--public",
        action="store_true",
        help="Split PII columns into separate *_pii.csv "
        "files so the main output is publishable.",
    )
    args = parser.parse_args(argv)

    sources = {
        name: path
        for name, path in (("vendor", args.vendor), ("license", args.license_path))
        if path is not None
    }
    if not sources:
        parser.error("provide at least one of --vendor / --license")

    args.out_dir.mkdir(parents=True, exist_ok=True)

    results: dict[str, CleanResult] = {}
    for name, path in sources.items():
        results[name] = clean_table(read_table(path), TABLE_REGISTRY[name])
        write_outputs(name, results[name], args.out_dir, public=args.public)

    all_corrections = [c for r in results.values() for c in r.corrections]
    all_violations = [v for r in results.values() for v in r.violations]
    all_violations.extend(
        cross_validate(
            {name: r.frame for name, r in results.items()},
            CROSS_VALIDATION_CONFIG,
        )
    )

    corrections_frame(all_corrections).to_csv(
        args.out_dir / "corrections.csv", index=False
    )
    violations_frame(all_violations).to_csv(
        args.out_dir / "violations.csv", index=False
    )

    for name, result in results.items():
        print(
            f"{name}: {len(result.frame)} rows, "
            f"{len(result.corrections)} corrections, "
            f"{len(result.violations)} table violations"
        )
    print(f"total violations incl. cross-table: {len(all_violations)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
