"""Frozen audit records produced by the cleaning engine.

These carry real cell values (before/after, offending value, the dedup key) and
are therefore PII-bearing by construction: they are written only to the
gitignored audit zone and never tracked. Any counts-only summary derived from
them is what may be posted (values-free board rule).

Copyright © 2026 Wolfgang Sanyer
Licensed under the Polyform Noncommercial License 1.0.0 (see LICENSE).
"""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Correction:
    """A cell the engine normalized: the value changed without breaching contract."""

    row_key: str
    column: str
    before: str
    after: str
    rule: str


@dataclass(frozen=True, slots=True)
class Violation:
    """A cell that breached its contract: flagged, left unchanged (report-don't-coerce)."""  # noqa: E501

    row_key: str
    column: str
    value: str
    rule: str


@dataclass(frozen=True, slots=True)
class DedupDrop:
    """A row removed by dedup, carrying the dropped and surviving row keys (REQ-11)."""

    dropped_row_key: str
    surviving_row_key: str
    dedup_value: str
