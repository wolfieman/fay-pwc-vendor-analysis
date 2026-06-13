"""The generic cleaning engine: role dispatch, report-don't-coerce, dedup.

``clean_table`` is pure. It applies, in fixed protocol order, whitespace first
then the column's role transform, recording a ``Correction`` for any change and a
``Violation`` for any contract breach (the value is left unchanged on breach),
and finally dedups (REQ-11) recording a ``DedupDrop`` per removed row. It hard-
fails if a configured column is absent from any record (no vacuous pass, REQ-14).

Copyright © 2026 Wolfgang Sanyer
Licensed under the Polyform Noncommercial License 1.0.0 (see LICENSE).
"""

from dataclasses import dataclass

from . import transforms
from .config import ColumnRule, TableConfig
from .records import Correction, DedupDrop, Violation

ROW_KEY = "row_key"


class MissingColumnError(KeyError):
    """A configured column was absent from a record (the engine refuses to skip it)."""


@dataclass(frozen=True, slots=True)
class CleanResult:
    rows: list[dict[str, str]]
    corrections: list[Correction]
    violations: list[Violation]
    drops: list[DedupDrop]


def assign_row_keys(
    records: list[dict[str, str]], *, key: str = ROW_KEY
) -> list[dict[str, str]]:
    """Stamp each record with its zero-padded ordinal in the extract (REQ-12)."""
    width = max(len(str(len(records) - 1)), 1)
    return [{key: f"{i:0{width}d}", **record} for i, record in enumerate(records)]


def _apply_role(value: str, rule: ColumnRule) -> transforms.Result:
    role = rule.role
    if role == "whitespace":
        return value, None
    if role == "name":
        return transforms.business_name_case(value)
    if role == "email":
        return transforms.normalize_email(value)
    if role == "phone":
        return transforms.normalize_phone(value)
    if role == "date":
        return transforms.normalize_date(value)
    if role == "license":
        return transforms.normalize_license(value)
    if role == "list":
        return transforms.normalize_list(value)
    if role == "sigil":
        return transforms.strip_sigils(value)
    if role in ("vocab", "flag"):
        return transforms.map_vocabulary(
            value, allowed=rule.allowed, mapping=rule.mapping
        )
    raise ValueError(f"unknown role: {role!r}")


def _completeness(row: dict[str, str], *, key: str) -> int:
    return sum(1 for col, val in row.items() if col != key and val != "")


def clean_table(
    records: list[dict[str, str]], config: TableConfig, *, key: str = ROW_KEY
) -> CleanResult:
    """Clean every record against the config, then dedup; pure and order-preserving."""
    for record in records:
        missing = [col for col in config.columns if col not in record]
        if missing:
            raise MissingColumnError(
                f"{config.name}: configured columns absent: {missing}"
            )

    corrections: list[Correction] = []
    violations: list[Violation] = []
    cleaned: list[dict[str, str]] = []

    for record in records:
        row_key = record.get(key, "")
        out = dict(record)
        for col, rule in config.columns.items():
            raw = record[col]
            collapsed, _ = transforms.collapse_whitespace(raw)
            if collapsed != raw:
                corrections.append(
                    Correction(row_key, col, raw, collapsed, "whitespace")
                )
            value, err = _apply_role(collapsed, rule)
            if err is not None:
                violations.append(Violation(row_key, col, collapsed, err))
                value = collapsed
            elif value != collapsed:
                corrections.append(
                    Correction(row_key, col, collapsed, value, rule.role)
                )
            out[col] = value
        cleaned.append(out)

    survivors, drops = _dedup(cleaned, config, key=key)
    return CleanResult(survivors, corrections, violations, drops)


def _dedup(
    rows: list[dict[str, str]], config: TableConfig, *, key: str
) -> tuple[list[dict[str, str]], list[DedupDrop]]:
    """Keep the most complete row per non-blank key; blanks never match (REQ-11)."""
    groups: dict[tuple[str, ...], list[int]] = {}
    singletons: list[int] = []
    for i, row in enumerate(rows):
        key_parts = tuple(row.get(col, "") for col in config.dedup_key)
        if any(part == "" for part in key_parts):  # any blank key part -> never matches
            singletons.append(i)
        else:
            groups.setdefault(key_parts, []).append(i)

    keep: set[int] = set(singletons)
    drops: list[DedupDrop] = []
    for key_parts, idxs in groups.items():
        winner = max(idxs, key=lambda i: (_completeness(rows[i], key=key), -i))
        keep.add(winner)
        for i in idxs:
            if i != winner:
                drops.append(
                    DedupDrop(
                        rows[i].get(key, ""),
                        rows[winner].get(key, ""),
                        " | ".join(key_parts),
                    )
                )

    survivors = [row for i, row in enumerate(rows) if i in keep]
    return survivors, drops
