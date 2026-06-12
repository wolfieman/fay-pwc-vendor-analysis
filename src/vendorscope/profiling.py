"""Pure per-column profiling, values-free for red columns.

Produces a counts-only report: distinct value counts for the named vocabulary
columns, blank/missingness counts for every column, and for red columns only a
nonblank/blank split (never a value list), so the profile is safe to attach to
the card (4.3). The acquire-time wall clock and file IO live in the shell; this
module is a pure function of the records.

Copyright © 2026 Wolfgang Sanyer
Licensed under the Polyform Noncommercial License 1.0.0 (see LICENSE).
"""

from collections import Counter
from collections.abc import Sequence


def profile(
    records: Sequence[dict[str, str]],
    *,
    vocab_columns: Sequence[str] = (),
    red_columns: Sequence[str] = (),
) -> dict:
    """Summarize records as counts only; red columns never contribute values."""
    columns: list[str] = list(records[0].keys()) if records else []
    red = set(red_columns)

    blank_counts = {
        col: sum(1 for r in records if r.get(col, "") == "") for col in columns
    }
    vocabularies = {
        col: dict(Counter(r.get(col, "") for r in records).most_common())
        for col in vocab_columns
        if col not in red
    }
    red_report = {
        col: {
            "nonblank": sum(1 for r in records if r.get(col, "") != ""),
            "blank": sum(1 for r in records if r.get(col, "") == ""),
        }
        for col in red_columns
    }

    return {
        "record_count": len(records),
        "columns": columns,
        "blank_counts": blank_counts,
        "vocabularies": vocabularies,
        "red_columns": red_report,
    }
