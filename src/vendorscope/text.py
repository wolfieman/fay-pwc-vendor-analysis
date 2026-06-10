"""Text normalization helpers shared across the acquisition and cleaning
scripts: header, company-name, license-number, and vendor-key canonicalization.

Copyright © 2026 Wolfgang Sanyer
Licensed under the Polyform Noncommercial License 1.0.0 (see LICENSE).
"""

import re

import pandas as pd

# Legal-suffix tail stripped from a company name before matching (Inc, LLC, ...).
SUFFIXES = (
    r"(,?\s+(inc|inc\.|llc|l\.l\.c\.|ltd|ltd\.|co|co\.|corp|corp\.|company"
    r"|contracting|contractors?))+$"
)


def snake(name: str) -> str:
    """Normalize a header to lowercase snake_case ("HUB Status" -> "hub_status")."""
    s = re.sub(r"[^\w]+", "_", name.strip()).lower()
    return re.sub(r"__+", "_", s).strip("_")


def normalize_name(s: str) -> str:
    """Strip whitespace, legal suffixes, and punctuation from a company name."""
    s = (s or "").strip()
    s = re.sub(r"\s+", " ", s)
    s = re.sub(SUFFIXES, "", s, flags=re.I)
    s = re.sub(r"[^\w\s&-]", "", s)  # drop punctuation
    return s.strip()


def normalize_license(v) -> str | None:
    """Coerce an Excel/Pandas value to a clean license string (85168.0 -> "85168")."""
    if v is None:
        return None
    if isinstance(v, int):
        return str(v)
    if isinstance(v, float):
        if v.is_integer():
            return str(int(v))
        s = f"{v}".strip()
        m = re.match(r"^\s*(\d+)\.(\d+)\s*$", s)
        return (m.group(1) + m.group(2)) if m else re.sub(r"\D", "", s) or None
    s = str(v).strip()
    m = re.match(r"^\s*(\d+)(?:\.0+)?\s*$", s)
    if m:
        return m.group(1)
    digits = re.sub(r"\D", "", s)
    return digits or None


def canon_vendor(v: str) -> str:
    """Canonicalize a vendor name to an upper-case, punctuation-free key."""
    if pd.isna(v):
        return ""
    v = str(v).upper().strip()
    v = re.sub(r"[^\w\s]", "", v)  # remove punctuation
    v = re.sub(r"\s+", " ", v)  # collapse spaces
    return v
