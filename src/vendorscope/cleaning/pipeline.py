"""Pipeline composition for the VendorScope engine.

One generic ``clean_table`` serves every dataset: which steps run, and on
which columns, falls out of the ``TableConfig`` it receives. The function is
pure — frames in, frames plus audit records out — so the imperative shell in
``cli.py`` stays trivially thin.

Copyright © 2026 Wolfgang Sanyer
Licensed under the Polyform Noncommercial License 1.0.0 (see LICENSE).
"""

from dataclasses import dataclass, field
from functools import partial

import pandas as pd

from .config import CrossValidationConfig, TableConfig
from .transforms import (
    Correction,
    Violation,
    apply_to_columns,
    clean_whitespace,
    deduplicate,
    hybrid_title_case,
    map_vocabulary,
    normalize_date,
    normalize_email,
    normalize_phone,
    normalize_text_id,
    standardize_list,
)
from .validate import run_cross_validation, validate_vocabulary


@dataclass
class CleanResult:
    """Outcome of cleaning one table: data plus its full audit trail."""

    frame: pd.DataFrame
    corrections: list[Correction] = field(default_factory=list)
    violations: list[Violation] = field(default_factory=list)


def clean_table(df: pd.DataFrame, config: TableConfig) -> CleanResult:
    """Run the documented cleaning protocol over one table.

    Step order follows the protocol: whitespace first (so every later rule
    sees trimmed values), formats next, vocabulary mapping after that, and
    deduplication last (so duplicates are compared in canonical form).
    Validation reports out-of-vocabulary values but never alters them.
    """
    corrections: list[Correction] = []
    violations: list[Violation] = []

    def run(frame: pd.DataFrame, columns: tuple[str, ...], fn, rule: str):
        out, fixed, flagged = apply_to_columns(
            frame, columns, fn, table=config.name, rule=rule
        )
        corrections.extend(fixed)
        violations.extend(flagged)
        return out

    out = run(df, tuple(df.columns), clean_whitespace, "trim")
    out = run(out, config.email_columns, normalize_email, "email")
    out = run(out, config.phone_columns, normalize_phone, "phone")
    out = run(out, config.date_columns, normalize_date, "date")
    out = run(
        out,
        config.business_name_columns,
        partial(
            hybrid_title_case,
            suffixes=config.name_suffixes,
            preserve_upper=config.preserve_upper,
        ),
        "business_name",
    )
    out = run(
        out,
        config.address_columns,
        partial(hybrid_title_case, preserve_upper=config.preserve_upper),
        "address",
    )
    out = run(out, config.text_id_columns, normalize_text_id, "text_id")
    out = run(
        out,
        config.flag_columns,
        partial(map_vocabulary, mapping=config.flag_map),
        "flag",
    )
    for column, mapping in config.mapped_vocab_columns.items():
        out = run(out, (column,), partial(map_vocabulary, mapping=mapping), "vocab_map")
    out = run(
        out,
        config.list_columns,
        partial(standardize_list, delimiters=config.list_delimiters),
        "list_delimiter",
    )

    violations.extend(validate_vocabulary(out, config.vocabularies, table=config.name))

    if config.dedup_keys:
        out, dropped = deduplicate(out, config.dedup_keys, table=config.name)
        corrections.extend(dropped)

    return CleanResult(frame=out, corrections=corrections, violations=violations)


def cross_validate(
    frames: dict[str, pd.DataFrame],
    config: CrossValidationConfig,
) -> list[Violation]:
    """Run configured cross-table rules over cleaned frames.

    Call this after ``clean_table`` so rules compare canonical values
    (e.g. flags already normalized, identifiers already de-artifacted).
    """
    return run_cross_validation(frames, config)


def corrections_frame(corrections: list[Correction]) -> pd.DataFrame:
    """Render correction records as a DataFrame for export."""
    columns = ["table", "row_id", "column", "before", "after", "rule"]
    return pd.DataFrame([vars(c) for c in corrections], columns=columns)


def violations_frame(violations: list[Violation]) -> pd.DataFrame:
    """Render violation records as a DataFrame for export."""
    columns = ["table", "row_id", "column", "value", "rule", "message"]
    return pd.DataFrame([vars(v) for v in violations], columns=columns)
