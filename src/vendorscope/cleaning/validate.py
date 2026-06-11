"""Validation checks for the VendorScope engine.

Validators never modify data. Each returns ``Violation`` records describing
where reality departs from the configured expectations, leaving the decision
about what to do with violations to humans or downstream policy. All
functions are pure and source-agnostic: tables, columns, vocabularies, and
rules arrive as parameters.

Copyright © 2026 Wolfgang Sanyer
Licensed under the Polyform Noncommercial License 1.0.0 (see LICENSE).
"""

import re
from collections.abc import Mapping, Sequence

import pandas as pd

from .config import CrossValidationConfig
from .transforms import Violation


def validate_vocabulary(
    df: pd.DataFrame,
    vocabularies: Mapping[str, Sequence[str]],
    *,
    table: str,
) -> list[Violation]:
    """Report values outside each column's controlled vocabulary.

    Blank values pass: the protocol treats blank as "missing", and missing
    is permitted everywhere because imputation is forbidden.
    """
    violations: list[Violation] = []
    for column, allowed in vocabularies.items():
        if column not in df.columns:
            continue
        allowed_set = set(allowed)
        for row_id, value in df[column].items():
            if not isinstance(value, str) or not value:
                continue
            if value not in allowed_set:
                violations.append(
                    Violation(
                        table=table,
                        row_id=row_id,
                        column=column,
                        value=value,
                        rule="vocabulary",
                        message=f"not in allowed set {sorted(allowed_set)}",
                    )
                )
    return violations


def check_format(
    df: pd.DataFrame,
    column: str,
    pattern: str,
    *,
    table: str,
    description: str = "",
) -> list[Violation]:
    """Report non-blank values of ``column`` not matching ``pattern``."""
    if column not in df.columns:
        return []
    compiled = re.compile(pattern)
    return [
        Violation(
            table=table,
            row_id=row_id,
            column=column,
            value=value,
            rule="format",
            message=description or f"does not match {pattern}",
        )
        for row_id, value in df[column].items()
        if isinstance(value, str) and value and not compiled.fullmatch(value)
    ]


def check_referential(
    left: pd.DataFrame,
    left_key: str,
    right_key_values: Sequence[str],
    *,
    left_table: str,
    right_description: str,
) -> list[Violation]:
    """Report non-blank left-key values absent from the right key set.

    This is the generic form "left key must exist in right key set".
    Orphans are reported rather than dropped so the integrity gap stays
    visible and auditable instead of silently shrinking the dataset.
    """
    if left_key not in left.columns:
        return []
    known = set(right_key_values)
    return [
        Violation(
            table=left_table,
            row_id=row_id,
            column=left_key,
            value=value,
            rule="referential",
            message=f"no matching key in {right_description}",
        )
        for row_id, value in left[left_key].items()
        if isinstance(value, str) and value and value not in known
    ]


def run_cross_validation(
    frames: Mapping[str, pd.DataFrame],
    config: CrossValidationConfig,
) -> list[Violation]:
    """Execute all configured cross-table rules against named frames.

    Rules referencing tables absent from ``frames`` are skipped, so partial
    runs (one table re-cleaned alone) remain possible.
    """
    violations: list[Violation] = []

    for rule in config.referential:
        if rule.left_table not in frames or rule.right_table not in frames:
            continue
        right = frames[rule.right_table]
        right_values = (
            right[rule.right_key].tolist() if rule.right_key in right.columns else []
        )
        violations.extend(
            check_referential(
                frames[rule.left_table],
                rule.left_key,
                right_values,
                left_table=rule.left_table,
                right_description=f"{rule.right_table}.{rule.right_key}",
            )
        )

    for fmt in config.formats:
        if fmt.table not in frames:
            continue
        violations.extend(
            check_format(
                frames[fmt.table],
                fmt.column,
                fmt.pattern,
                table=fmt.table,
                description=fmt.description,
            )
        )

    for cond in config.conditional:
        frame = frames.get(cond.table)
        if frame is None or not {
            cond.condition_column,
            cond.flag_column,
            cond.required_column,
        }.issubset(frame.columns):
            continue
        mask = (
            (frame[cond.condition_column] == cond.condition_value)
            & (frame[cond.flag_column] == cond.flag_value)
            & (frame[cond.required_column].astype(str) == "")
        )
        violations.extend(
            Violation(
                table=cond.table,
                row_id=row_id,
                column=cond.required_column,
                value="",
                rule="conditional_requirement",
                message=cond.description
                or (
                    f"required when {cond.condition_column}="
                    f"{cond.condition_value} and {cond.flag_column}="
                    f"{cond.flag_value}"
                ),
            )
            for row_id in frame.index[mask]
        )

    return violations
