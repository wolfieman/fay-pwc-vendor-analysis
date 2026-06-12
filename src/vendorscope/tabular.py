"""Text-mode tabular IO and the processed-write transforms.

The single chokepoint for reading and writing CSVs and for the read-time column
manifest check, the snake_case rename, and the PII split. Every read is
text-mode: every cell a string, NA-token guessing off, ``utf-8-sig`` (REQ-06), so
a county literally named "NA" is data and leading zeros survive. The rename to
snake_case is applied once, at processed-write, with a uniqueness assertion so
two source columns can never silently merge (REQ-13/4.2).

Copyright © 2026 Wolfgang Sanyer
Licensed under the Polyform Noncommercial License 1.0.0 (see LICENSE).
"""

from collections.abc import Iterable, Sequence
from pathlib import Path

import pandas as pd

from .cleaning import config

ROW_KEY = "row_key"


class ManifestError(ValueError):
    """The observed columns do not match the expected manifest (REQ-13)."""


class UniquenessError(ValueError):
    """A rename would collapse two source columns into one target (REQ-13/4.2)."""


def read_csv(path: Path) -> list[dict[str, str]]:
    """Read a CSV in strict text mode: all strings, no NA coercion, BOM-tolerant."""
    frame = pd.read_csv(
        path, dtype=str, keep_default_na=False, na_filter=False, encoding="utf-8-sig"
    )
    return frame.to_dict(orient="records")


def write_csv(
    path: Path, rows: list[dict[str, str]], *, columns: Sequence[str]
) -> None:
    """Write rows as a text CSV with a stable column order and a UTF-8 BOM."""
    frame = pd.DataFrame(rows, columns=list(columns)).fillna("")
    frame.to_csv(path, index=False, encoding="utf-8-sig")


def assert_manifest(
    columns: Iterable[str], expected: tuple[str, ...] = config.EXPECTED_COLUMNS
) -> None:
    """Hard-fail at read time on any column set mismatch (rename, add, or drop)."""
    observed = set(columns)
    want = set(expected)
    if observed != want:
        missing = sorted(want - observed)
        extra = sorted(observed - want)
        raise ManifestError(
            f"column manifest mismatch: missing={missing} unexpected={extra}"
        )


def rename_snake(
    rows: list[dict[str, str]], mapping: dict[str, str] = config.SNAKE_CASE
) -> list[dict[str, str]]:
    """Rename source columns to their snake_case targets; reject any collision."""
    out: list[dict[str, str]] = []
    for row in rows:
        renamed: dict[str, str] = {}
        for key, value in row.items():
            target = mapping.get(key, key)
            if target in renamed:
                raise UniquenessError(f"rename collision on target {target!r}")
            renamed[target] = value
        out.append(renamed)
    return out


def split_pii(
    rows: list[dict[str, str]], red_columns: Sequence[str], *, key: str = ROW_KEY
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    """Split into the deliverable (no red columns) and the contacts sibling."""
    red = set(red_columns)
    deliverable = [{k: v for k, v in row.items() if k not in red} for row in rows]
    contacts = [
        {key: row[key], **{c: row.get(c, "") for c in red_columns}} for row in rows
    ]
    return deliverable, contacts
