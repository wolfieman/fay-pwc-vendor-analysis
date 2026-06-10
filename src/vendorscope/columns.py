"""Column resolution helpers: find the license-number column, or map column
letters / header names to integer indices.

Copyright © 2026 Wolfgang Sanyer
Licensed under the Polyform Noncommercial License 1.0.0 (see LICENSE).
"""

import re

import pandas as pd


def autodetect_license_column(df: pd.DataFrame) -> str | None:
    """Return the most likely license-number column, or None if none matches."""
    candidates = [
        "License_Number",
        "LICENSE_NUMBER",
        "LICENSE",
        "LICENSE #",
        "License #",
        "LicenseNumber",
        "License No",
        "LicenseNo",
        "AccountNumber",
        "Account Number",
    ]
    for c in candidates:
        if c in df.columns:
            return c
    for c in df.columns:
        if re.search(r"license|account", c, re.I):
            return c
    return None


def get_col_indices(df: pd.DataFrame, name_col: str, license_col: str):
    """Resolve column letters (A, B, ...) or header names to integer indices."""

    def to_idx(key):
        if isinstance(key, str) and key.strip().isalpha() and len(key.strip()) == 1:
            return ord(key.strip().upper()) - ord("A")
        if isinstance(key, str) and key in df.columns:
            return df.columns.get_loc(key)
        if isinstance(key, int):
            return key
        raise ValueError(f"Can't resolve column: {key}")

    return to_idx(name_col), to_idx(license_col)
